"""Render a separate diagnostic-only Lambda writer stack; never deploy it.

The existing observer role is not granted DynamoDB write. This template's
separate GitHub invoker policy allows only a code-hash-pinned Lambda version,
and the Lambda service role has campaign-scoped data permissions on one table. This
does not authenticate caller-supplied event claims, an independent anchor, the
budget, or the clock and never grants EC2/GO/termination. IAM administrators or
someone with PassRole/function modification can evade the code boundary.

S3 code object version, code signing configuration, and exact archive digest
must be supplied by a separately reviewed release process. This source does not
create/upload/sign a package, initialize a HEAD, change AWS, or establish a
deployment approval. The entire stack is diagnostic only; in particular Lambda
asynchronous delivery can retry or duplicate invocations independently of SDK
retry configuration. Never use its response to start or settle a scored game.
"""
import argparse
import hashlib
import json
import re
import sys


def _ref(value):
    return {"Ref": value}


def _sub(value):
    return {"Fn::Sub": value}


def _arn(value):
    return {"Fn::GetAtt": [value, "Arn"]}


def _policy(statements):
    return {"Version": "2012-10-17", "Statement": statements}


def template(*, campaign_id, epoch_table_name, genesis_json):
    # Bind environment values into the rendered template. CloudFormation has no
    # hash intrinsic: caller-supplied digest parameters would permit stale versions.
    if not isinstance(campaign_id, str) or not re.fullmatch(r"league-[A-Za-z0-9_.-]{0,89}", campaign_id):
        raise ValueError("invalid campaign id")
    if not isinstance(epoch_table_name, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{3,255}", epoch_table_name):
        raise ValueError("invalid table name")
    if (not isinstance(genesis_json, str) or not 1 <= len(genesis_json) <= 1024
            or not all(" " <= c <= "~" for c in genesis_json)):
        raise ValueError("invalid genesis JSON environment value")
    environment = {"ROVE_LEAGUE_CAMPAIGN": campaign_id,
                   "ROVE_LEAGUE_EPOCH_TABLE": epoch_table_name,
                   "ROVE_LEAGUE_GENESIS_JSON": genesis_json}
    fingerprint = hashlib.sha256(json.dumps(environment, sort_keys=True, separators=(",", ":"),
                                            ensure_ascii=True).encode("ascii")).hexdigest()
    campaign = campaign_id
    table = _sub("arn:${AWS::Partition}:dynamodb:${AWS::Region}:${AWS::AccountId}:table/" + epoch_table_name)
    data_scope = {"ForAllValues:StringEquals": {"dynamodb:LeadingKeys": [campaign]},
                  "Null": {"dynamodb:LeadingKeys": "false"}}
    function_name = _ref("FunctionName")
    log_streams = _sub("arn:${AWS::Partition}:logs:${AWS::Region}:${AWS::AccountId}:log-group:/aws/lambda/${FunctionName}:*")
    writer_role = {
        "Type": "AWS::IAM::Role",
        "Metadata": {"com.aws.cloudformation.Context": {
            "why": "Limit diagnostic writes to a dedicated Lambda service identity and one league partition.",
            "must": ["No EC2, S3 anchor-signing, GO or termination permissions.",
                     "IAM data permissions cannot require correct conditional expressions.",
                     "Independent control of PassRole, Lambda code and role modification remains necessary."],
        }},
        "Properties": {
            "AssumeRolePolicyDocument": _policy([{"Effect": "Allow", "Principal": {"Service": "lambda.amazonaws.com"},
                                                   "Action": "sts:AssumeRole"}]),
            "Policies": [{"PolicyName": "league-diagnostic-table-and-logs", "PolicyDocument": _policy([
                {"Sid": "CampaignReadAndConditionalCodeWrites", "Effect": "Allow", "Resource": table,
                 "Action": ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:PutItem", "dynamodb:UpdateItem"],
                 "Condition": data_scope},
                {"Sid": "DenyDestructiveTableOperations", "Effect": "Deny", "Resource": table,
                 "Action": ["dynamodb:DeleteItem", "dynamodb:BatchWriteItem", "dynamodb:PartiQLInsert",
                            "dynamodb:PartiQLUpdate", "dynamodb:PartiQLDelete", "dynamodb:UpdateTable",
                            "dynamodb:DeleteTable", "dynamodb:UpdateTimeToLive", "dynamodb:UpdateContinuousBackups",
                            "dynamodb:PutResourcePolicy", "dynamodb:DeleteResourcePolicy"]},
                {"Sid": "WriteThisFunctionLogs", "Effect": "Allow", "Resource": log_streams,
                 "Action": ["logs:CreateLogStream", "logs:PutLogEvents"]},
            ])}],
        },
    }
    trust = {"Effect": "Allow", "Principal": {"Federated": _sub(
        "arn:${AWS::Partition}:iam::${AWS::AccountId}:oidc-provider/token.actions.githubusercontent.com")},
        "Action": "sts:AssumeRoleWithWebIdentity", "Condition": {"StringEquals": {
            "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
            "token.actions.githubusercontent.com:sub": _sub("repo:daejunnom/Rove4k:environment:${GitHubEnvironment}"),
        }}}
    return {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "Rove4k league diagnostic writer - confines conditional history recording to a code-hash-pinned Lambda version without execution authority",
        "Metadata": {"AWSToolsMetrics": {"AWSAgentToolkit": "aws-cloudformation@3"},
                     "com.aws.cloudformation.Context": {"must": [
                         "Diagnostic records never authorize GO, instance launch, termination or recovery.",
                         "No legacy deadline resource or instance termination may be attached.",
                         "Verify independent anchor, IAM writer isolation and observed source provenance separately.",
                         "Verify the trusted signing identity separately; async retries remain possible.",
                         "Code SHA does not pin the managed runtime or its AWS SDK dependencies.",
                     ]}},
        "Parameters": {
            "GitHubEnvironment": {"Type": "String", "AllowedPattern": "[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", "MinLength": 1, "MaxLength": 64},
            "FunctionName": {"Type": "String", "AllowedPattern": "rove4k-league-[a-z0-9-]{1,40}",
                             "MinLength": 15, "MaxLength": 54,
                             "Description": "Unique diagnostic writer name; verify it does not collide with an existing function."},
            "HomeRegion": {"Type": "String", "Default": "ap-southeast-2",
                           "AllowedPattern": "[a-z][a-z0-9]*(?:-[a-z0-9]+)+-[0-9]+", "MaxLength": 63},
            "CodeBucket": {"Type": "String", "AllowedPattern": "[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]", "MinLength": 3, "MaxLength": 63},
            "CodeKey": {"Type": "String", "MinLength": 1, "MaxLength": 1024},
            "CodeObjectVersion": {"Type": "String", "MinLength": 1, "MaxLength": 1024},
            "CodeSha256": {"Type": "String", "AllowedPattern": "[A-Za-z0-9+/]{43}=", "MinLength": 44, "MaxLength": 44},
            "SigningProfileVersionArn": {"Type": "String",
                "AllowedPattern": "arn:[a-z0-9-]+:signer:[a-z0-9-]+:[0-9]{12}:/signing-profiles/[A-Za-z0-9_]{2,64}/[A-Za-z0-9]{10}",
                "Description": "Previously verified trusted AWS Signer profile version ARN."},
        },
        "Rules": {"AuthorityHomeRegion": {"Assertions": [{
            "Assert": {"Fn::Equals": [_ref("HomeRegion"), _ref("AWS::Region")]},
            "AssertDescription": "Deploy the writer in the authority home region.",
        }]}, "VersionedCodeObject": {"Assertions": [{
            "Assert": {"Fn::Not": [{"Fn::Equals": [_ref("CodeObjectVersion"), "null"]}]},
            "AssertDescription": "Use an actual S3 object version, not the null version.",
        }]}},
        "Resources": {
            "WriterRole": writer_role,
            "WriterSigningConfig": {"Type": "AWS::Lambda::CodeSigningConfig",
                "Metadata": {"com.aws.cloudformation.Context": {"why": "Reject untrusted Lambda code deployments using the specified signer version.",
                    "must": ["Verify signer ownership independently; administrators can change this configuration."]}},
                "Properties": {"AllowedPublishers": {"SigningProfileVersionArns": [_ref("SigningProfileVersionArn")]},
                    "CodeSigningPolicies": {"UntrustedArtifactOnDeployment": "Enforce"}}},
            "WriterLogGroup": {"Type": "AWS::Logs::LogGroup", "DeletionPolicy": "Retain", "UpdateReplacePolicy": "Retain",
                "Metadata": {"com.aws.cloudformation.Context": {"why": "Keep bounded diagnostic invocation records for review.",
                    "must": ["Logs are not an independently authenticated history anchor."]}},
                "Properties": {"LogGroupName": _sub("/aws/lambda/${FunctionName}"), "RetentionInDays": 30}},
            "WriterFunction": {"Type": "AWS::Lambda::Function", "DependsOn": ["WriterLogGroup"],
                "Metadata": {"com.aws.cloudformation.Context": {"why": "Validate and conditionally append v2 diagnostic history instead of exposing DynamoDB writes to callers.",
                    "must": ["Keep version/code signature pinned; no GO, launch or recovery authority.",
                             "Reserved concurrency does not prove exclusive table ownership or prevent retries."]}},
                "Properties": {"FunctionName": function_name, "Runtime": "python3.12", "Handler": "league_writer_lambda.handler",
                    "Architectures": ["x86_64"], "Role": _arn("WriterRole"), "Timeout": 60, "MemorySize": 256,
                    "ReservedConcurrentExecutions": 1, "CodeSigningConfigArn": {"Fn::GetAtt": ["WriterSigningConfig", "CodeSigningConfigArn"]},
                    "Code": {"S3Bucket": _ref("CodeBucket"), "S3Key": _ref("CodeKey"), "S3ObjectVersion": _ref("CodeObjectVersion")},
                    "Environment": {"Variables": environment}}},
            "WriterVersion": {"Type": "AWS::Lambda::Version",
                "Metadata": {"com.aws.cloudformation.Context": {"why": "Pin the invoker to a published, SHA-checked writer version.",
                    "must": ["Code SHA proves package bytes, not source provenance or IAM isolation."]}},
                "Properties": {"FunctionName": _ref("WriterFunction"), "CodeSha256": _ref("CodeSha256"),
                               "Description": "env-sha256:" + fingerprint}},
            "InvokerRole": {"Type": "AWS::IAM::Role",
                "Metadata": {"com.aws.cloudformation.Context": {"why": "Allow one protected GitHub environment to invoke only the diagnostic version.",
                    "must": ["Never attach table writer or EC2 permissions to this role.",
                             "Other IAM or resource policies may add permissions beyond this template.",
                             "GitHub environment subject does not identify a workflow file."]}},
                "Properties": {"AssumeRolePolicyDocument": _policy([trust]), "Policies": [{
                    "PolicyName": "invoke-pinned-diagnostic-writer", "PolicyDocument": _policy([
                        {"Effect": "Allow", "Action": "lambda:InvokeFunction", "Resource": _ref("WriterVersion")},
                        {"Effect": "Deny", "Resource": table, "Action": ["dynamodb:PutItem", "dynamodb:UpdateItem",
                            "dynamodb:DeleteItem", "dynamodb:BatchWriteItem", "dynamodb:PartiQLInsert",
                            "dynamodb:PartiQLUpdate", "dynamodb:PartiQLDelete", "dynamodb:PutResourcePolicy",
                            "dynamodb:DeleteResourcePolicy", "dynamodb:UpdateTable", "dynamodb:DeleteTable"]},
                    ])}]}},
        },
        "Outputs": {
            "WriterVersionArn": {"Description": "Published diagnostic writer version; not an execution authority.", "Value": _ref("WriterVersion")},
            "InvokerRoleArn": {"Description": "GitHub role that invokes only the pinned diagnostic writer.", "Value": _arn("InvokerRole")},
        },
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Render a diagnostic writer template from a JSON configuration on stdin")
    parser.parse_args()
    config = json.load(sys.stdin)
    if not isinstance(config, dict) or set(config) != {"campaign_id", "epoch_table_name", "genesis_json"}:
        raise ValueError("configuration must contain exactly campaign_id, epoch_table_name and genesis_json")
    print(json.dumps(template(**config), indent=2, sort_keys=True))
