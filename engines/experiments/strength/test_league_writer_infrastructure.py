"""Security and packaging contracts for the diagnostic Lambda writer."""
import base64
import hashlib
import io
import json
from pathlib import Path
import re
import tempfile
import unittest
import zipfile

try:
    from . import league_writer_infrastructure as infra
    from . import league_writer_package as package
except ImportError:
    import league_writer_infrastructure as infra
    import league_writer_package as package


class DiagnosticWriterInfrastructureTests(unittest.TestCase):
    def setUp(self):
        self.config = {"campaign_id": "league-test", "epoch_table_name": "league-table",
                       "genesis_json": '{"campaign":"league-test"}'}
        self.doc = infra.template(**self.config)
        self.resources = self.doc["Resources"]

    def test_only_lambda_service_role_can_write_dynamodb_and_it_cannot_delete(self):
        role = self.resources["WriterRole"]["Properties"]
        trust = role["AssumeRolePolicyDocument"]["Statement"]
        self.assertEqual(len(trust), 1)
        self.assertEqual(trust[0]["Principal"], {"Service": "lambda.amazonaws.com"})
        statements = role["Policies"][0]["PolicyDocument"]["Statement"]
        table = next(s for s in statements if s["Sid"] == "CampaignReadAndConditionalCodeWrites")
        self.assertEqual(set(table["Action"]), {"dynamodb:GetItem", "dynamodb:Query", "dynamodb:PutItem", "dynamodb:UpdateItem"})
        self.assertEqual(table["Resource"], {"Fn::Sub": "arn:${AWS::Partition}:dynamodb:${AWS::Region}:${AWS::AccountId}:table/league-table"})
        self.assertEqual(table["Condition"], {"ForAllValues:StringEquals": {"dynamodb:LeadingKeys": ["league-test"]},
                                             "Null": {"dynamodb:LeadingKeys": "false"}})
        deny = next(s for s in statements if s["Sid"] == "DenyDestructiveTableOperations")
        self.assertEqual(deny["Effect"], "Deny")
        self.assertTrue({"dynamodb:DeleteItem", "dynamodb:BatchWriteItem", "dynamodb:PutResourcePolicy",
                         "dynamodb:DeleteResourcePolicy"}.issubset(deny["Action"]))
        for statement in statements:
            if statement["Effect"] == "Allow":
                self.assertFalse(any(str(action).startswith(("ec2:", "s3:", "kms:")) for action in statement["Action"]))

    def test_invoker_is_exact_oidc_environment_and_can_invoke_only_version(self):
        role = self.resources["InvokerRole"]["Properties"]
        trust = role["AssumeRolePolicyDocument"]["Statement"][0]
        self.assertEqual(trust["Action"], "sts:AssumeRoleWithWebIdentity")
        self.assertEqual(trust["Condition"]["StringEquals"], {
            "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
            "token.actions.githubusercontent.com:sub": {"Fn::Sub": "repo:daejunnom/Rove4k:environment:${GitHubEnvironment}"}})
        statements = role["Policies"][0]["PolicyDocument"]["Statement"]
        allows = [s for s in statements if s["Effect"] == "Allow"]
        self.assertEqual(allows, [{"Effect": "Allow", "Action": "lambda:InvokeFunction", "Resource": {"Ref": "WriterVersion"}}])
        deny = next(s for s in statements if s["Effect"] == "Deny")
        self.assertTrue({"dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:DeleteItem"}.issubset(deny["Action"]))

    def test_code_object_version_sha_and_signing_config_are_required(self):
        props = self.resources["WriterFunction"]["Properties"]
        self.assertEqual(props["Handler"], "league_writer_lambda.handler")
        self.assertEqual(props["ReservedConcurrentExecutions"], 1)
        self.assertEqual(props["Code"]["S3ObjectVersion"], {"Ref": "CodeObjectVersion"})
        self.assertEqual(props["CodeSigningConfigArn"], {"Fn::GetAtt": ["WriterSigningConfig", "CodeSigningConfigArn"]})
        signing = self.resources["WriterSigningConfig"]["Properties"]
        self.assertEqual(signing["CodeSigningPolicies"]["UntrustedArtifactOnDeployment"], "Enforce")
        self.assertEqual(signing["AllowedPublishers"]["SigningProfileVersionArns"], [{"Ref": "SigningProfileVersionArn"}])
        self.assertEqual(self.resources["WriterVersion"]["Properties"]["CodeSha256"], {"Ref": "CodeSha256"})
        self.assertEqual(props["Environment"]["Variables"], {"ROVE_LEAGUE_CAMPAIGN": "league-test",
                         "ROVE_LEAGUE_EPOCH_TABLE": "league-table", "ROVE_LEAGUE_GENESIS_JSON": self.config["genesis_json"]})
        self.assertEqual(props["FunctionName"], {"Ref": "FunctionName"})
        self.assertEqual(self.resources["WriterLogGroup"]["Properties"]["LogGroupName"],
                         {"Fn::Sub": "/aws/lambda/${FunctionName}"})
        self.assertIsNotNone(re.fullmatch(self.doc["Parameters"]["FunctionName"]["AllowedPattern"], "rove4k-league-writer"))
        self.assertLessEqual(self.doc["Parameters"]["FunctionName"]["MaxLength"], 64)
        self.assertEqual(self.doc["Rules"]["AuthorityHomeRegion"]["Assertions"][0]["Assert"],
                         {"Fn::Equals": [{"Ref": "HomeRegion"}, {"Ref": "AWS::Region"}]})
        self.assertEqual(self.doc["Rules"]["VersionedCodeObject"]["Assertions"][0]["Assert"],
                         {"Fn::Not": [{"Fn::Equals": [{"Ref": "CodeObjectVersion"}, "null"]}]})
        for name in ("CodeObjectVersion", "CodeSha256", "SigningProfileVersionArn"):
            self.assertNotIn("Default", self.doc["Parameters"][name])

    def test_render_binds_each_environment_value_to_version_replacement(self):
        env = self.resources["WriterFunction"]["Properties"]["Environment"]["Variables"]
        expected = hashlib.sha256(json.dumps(env, sort_keys=True, separators=(",", ":"),
                                             ensure_ascii=True).encode("ascii")).hexdigest()
        version = self.resources["WriterVersion"]["Properties"]
        self.assertEqual(version["Description"], "env-sha256:" + expected)
        self.assertEqual(version["FunctionName"], {"Ref": "WriterFunction"})
        self.assertTrue({"CampaignId", "EpochTableName", "GenesisJson"}.isdisjoint(self.doc["Parameters"]))
        for name, value in (("campaign_id", "league-another"), ("epoch_table_name", "another-table"),
                            ("genesis_json", '{"campaign":"league-test","v":2}')):
            changed = infra.template(**{**self.config, name: value})
            self.assertNotEqual(changed["Resources"]["WriterVersion"]["Properties"]["Description"], version["Description"])
            self.assertNotEqual(changed["Resources"]["WriterFunction"]["Properties"]["Environment"]["Variables"], env)
            self.assertEqual(changed["Resources"]["WriterVersion"]["Properties"]["FunctionName"], {"Ref": "WriterFunction"})

    def test_render_rejects_invalid_bound_environment(self):
        for name, value in (("campaign_id", "x"), ("epoch_table_name", "${Bad}"),
                            ("genesis_json", "x" * 1025), ("genesis_json", "\u2603")):
            with self.subTest(name=name, value=value), self.assertRaises(ValueError):
                infra.template(**{**self.config, name: value})

    def test_no_instance_scheduler_or_anchor_authority_is_provisioned(self):
        self.assertEqual({r["Type"] for r in self.resources.values()},
                         {"AWS::IAM::Role", "AWS::Logs::LogGroup", "AWS::Lambda::Function", "AWS::Lambda::Version", "AWS::Lambda::CodeSigningConfig"})
        text = json.dumps(self.doc).lower()
        self.assertNotIn("ec2:runinstances", text)
        self.assertNotIn("ec2:terminateinstances", text)
        self.assertNotIn("harddeadlineutc", text)
        self.assertEqual(self.doc["Metadata"]["AWSToolsMetrics"]["AWSAgentToolkit"], "aws-cloudformation@3")
        self.assertLessEqual(len(json.dumps(self.doc).encode()), 51200)

    def test_package_is_reproducible_contains_only_two_sources_and_matches_digest(self):
        root = Path(package.__file__).resolve().parent
        first, second = package.package(root), package.package(root)
        self.assertEqual(first, second)
        self.assertEqual(first["unsigned_sha256_base64"], base64.b64encode(hashlib.sha256(first["bytes"]).digest()).decode("ascii"))
        with zipfile.ZipFile(io.BytesIO(first["bytes"])) as archive:
            self.assertEqual(archive.namelist(), list(package.SOURCE_FILES))
            for name in package.SOURCE_FILES:
                self.assertEqual(hashlib.sha256(archive.read(name)).hexdigest(), first["source_sha256"][name])
                self.assertEqual(archive.getinfo(name).date_time, (1980, 1, 1, 0, 0, 0))

    def test_package_never_includes_unknown_neighbor_files(self):
        source = Path(package.__file__).resolve().parent
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in package.SOURCE_FILES:
                (root / name).write_bytes((source / name).read_bytes())
            (root / "not-a-source.txt").write_text("should not be packed", encoding="utf-8")
            result = package.package(root)
            with zipfile.ZipFile(io.BytesIO(result["bytes"])) as archive:
                self.assertEqual(archive.namelist(), list(package.SOURCE_FILES))


if __name__ == "__main__":
    unittest.main()
