"""Static contracts for the read-only league CloudFormation foundation."""
import json
import re
import unittest

try:
    from .league_authority_infrastructure import template
except ImportError:
    from league_authority_infrastructure import template


class AuthorityFoundationTests(unittest.TestCase):
    def setUp(self):
        self.doc = template()
        self.resources = self.doc["Resources"]

    def test_table_retention_pitr_and_epoch_keys_do_not_enable_ttl(self):
        table = self.resources["EpochTable"]
        self.assertEqual(table["Type"], "AWS::DynamoDB::Table")
        self.assertEqual(table["DeletionPolicy"], "Retain")
        self.assertEqual(table["UpdateReplacePolicy"], "Retain")
        props = table["Properties"]
        self.assertTrue(props["DeletionProtectionEnabled"])
        self.assertTrue(props["PointInTimeRecoverySpecification"]["PointInTimeRecoveryEnabled"])
        self.assertTrue(props["SSESpecification"]["SSEEnabled"])
        self.assertNotIn("TimeToLiveSpecification", props)
        self.assertNotIn("ReplicaSpecifications", props)
        self.assertEqual(props["KeySchema"], [
            {"AttributeName": "campaign_id", "KeyType": "HASH"},
            {"AttributeName": "record_id", "KeyType": "RANGE"},
        ])

    def test_observer_has_only_table_reads_and_explicit_item_write_deny(self):
        role = self.resources["ObserverRole"]["Properties"]
        self.assertNotIn("ManagedPolicyArns", role)
        self.assertEqual(len(role["Policies"]), 1)
        statements = role["Policies"][0]["PolicyDocument"]["Statement"]
        allowed = {action for statement in statements if statement["Effect"] == "Allow"
                   for action in ([statement["Action"]] if isinstance(statement["Action"], str) else statement["Action"])}
        self.assertEqual(allowed, {"dynamodb:GetItem", "dynamodb:Query", "dynamodb:DescribeTable"})
        item_read = next(s for s in statements if s["Sid"] == "ReadOnlyCampaignItems")
        self.assertEqual(item_read["Resource"], {"Fn::GetAtt": ["EpochTable", "Arn"]})
        self.assertEqual(item_read["Condition"], {
            "ForAllValues:StringEquals": {"dynamodb:LeadingKeys": [{"Ref": "CampaignId"}]},
            "Null": {"dynamodb:LeadingKeys": "false"},
        })
        deny = next(s for s in statements if s["Sid"] == "DenyEpochMutation")
        self.assertEqual(deny["Effect"], "Deny")
        self.assertTrue({"dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:DeleteItem",
                         "dynamodb:BatchWriteItem", "dynamodb:UpdateTable", "dynamodb:DeleteTable",
                         "dynamodb:PutResourcePolicy", "dynamodb:DeleteResourcePolicy"}
                        .issubset(deny["Action"]))
        self.assertEqual(deny["Resource"], {"Fn::GetAtt": ["EpochTable", "Arn"]})

    def test_trust_is_exact_repo_environment_audience_and_current_account_provider(self):
        trust = self.resources["ObserverRole"]["Properties"]["AssumeRolePolicyDocument"]["Statement"]
        self.assertEqual(len(trust), 1)
        self.assertEqual(trust[0]["Action"], "sts:AssumeRoleWithWebIdentity")
        self.assertEqual(trust[0]["Principal"], {"Federated": {"Fn::Sub":
            "arn:${AWS::Partition}:iam::${AWS::AccountId}:oidc-provider/token.actions.githubusercontent.com"}})
        self.assertEqual(trust[0]["Condition"]["StringEquals"], {
            "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
            "token.actions.githubusercontent.com:sub": {"Fn::Sub": "repo:daejunnom/Rove4k:environment:${GitHubEnvironment}"},
        })
        environment = self.doc["Parameters"]["GitHubEnvironment"]
        self.assertNotIn("Default", environment)
        self.assertEqual(environment["AllowedPattern"], "[A-Za-z0-9][A-Za-z0-9_.-]{0,63}")

    def test_no_scheduler_deadline_lambda_ec2_or_writer_is_defined(self):
        self.assertEqual({r["Type"] for r in self.resources.values()},
                         {"AWS::DynamoDB::Table", "AWS::IAM::Role"})
        text = json.dumps(self.doc).lower()
        self.assertNotIn("ec2:runinstances", text)
        self.assertNotIn("ec2:terminateinstances", text)
        self.assertNotIn("harddeadlineutc", text)
        self.assertEqual(self.doc["Metadata"]["AWSToolsMetrics"]["AWSAgentToolkit"], "aws-cloudformation@3")
        self.assertEqual(self.doc["Rules"]["AuthorityHomeRegion"]["Assertions"][0]["Assert"],
                         {"Fn::Equals": [{"Ref": "HomeRegion"}, {"Ref": "AWS::Region"}]})
        pattern = self.doc["Parameters"]["CampaignId"]["AllowedPattern"]
        self.assertIsNotNone(re.fullmatch(pattern, "league-example"))
        self.assertIsNone(re.fullmatch(pattern, "legacy-example"))
        self.assertIsNone(re.fullmatch(pattern, "league-" + "a" * 90))

    def test_factory_returns_independent_document_and_inline_size_is_bounded(self):
        self.resources["EpochTable"]["Properties"]["KeySchema"].clear()
        original = template()
        self.assertEqual(len(original["Resources"]["EpochTable"]["Properties"]["KeySchema"]), 2)
        self.assertLessEqual(len(json.dumps(original).encode("utf-8")), 51200)


if __name__ == "__main__":
    unittest.main()
