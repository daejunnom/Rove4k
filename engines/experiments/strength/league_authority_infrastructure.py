"""Render a read-only league authority foundation; never call AWS.

This is an isolated CloudFormation stack, not the legacy campaign stack.
The table and observer role do not provision or initialize an epoch HEAD,
grant a writer, establish an independent history anchor, start instances,
approve a GO, terminate hosts, or recover previously started games.

PITR/deletion protection preserve recoverability, not the authenticity or
completeness of the current record. IAM permissions do not prove conditional
write expressions; direct writer access must remain unavailable until the
separate coordinator, independent anchor, recovery, and fencing contracts are
implemented and verified. Deploying this template can incur DynamoDB charges.
"""

import json


def _ref(name):
    return {"Ref": name}


def _sub(value):
    return {"Fn::Sub": value}


def _arn(name):
    return {"Fn::GetAtt": [name, "Arn"]}


def _policy(statements):
    return {"Version": "2012-10-17", "Statement": statements}


def template():
    """Build a parameterized, reviewable CloudFormation document.

    A single home-region stack can later observe hosts in other regions, but
    its DynamoDB table is not a cross-region global table. This factory makes
    no assertion that a GitHub environment, OIDC provider, IAM boundary, or
    upstream execution identity actually exists or has been configured.
    """
    campaign = _ref("CampaignId")
    table_arn = _arn("EpochTable")
    data_scope = {
        "ForAllValues:StringEquals": {"dynamodb:LeadingKeys": [campaign]},
        "Null": {"dynamodb:LeadingKeys": "false"},
    }
    oidc_trust = {
        "Effect": "Allow",
        "Principal": {"Federated": _sub("arn:${AWS::Partition}:iam::${AWS::AccountId}:oidc-provider/token.actions.githubusercontent.com")},
        "Action": "sts:AssumeRoleWithWebIdentity",
        "Condition": {"StringEquals": {
            "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
            "token.actions.githubusercontent.com:sub": _sub("repo:daejunnom/Rove4k:environment:${GitHubEnvironment}"),
        }},
    }
    observer_policy = _policy([
        {"Sid": "ReadOnlyCampaignItems", "Effect": "Allow",
         "Action": ["dynamodb:GetItem", "dynamodb:Query"], "Resource": table_arn,
         "Condition": data_scope},
        {"Sid": "DescribeExactEpochTable", "Effect": "Allow",
         "Action": "dynamodb:DescribeTable", "Resource": table_arn},
        # An explicit deny survives accidental identity-policy additions to
        # this observer role. It does not constrain account administrators or
        # independently granted permissions of other principals.
        {"Sid": "DenyEpochMutation", "Effect": "Deny", "Resource": table_arn,
         "Action": ["dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:DeleteItem",
                    "dynamodb:BatchWriteItem", "dynamodb:PartiQLInsert",
                    "dynamodb:PartiQLUpdate", "dynamodb:PartiQLDelete",
                    "dynamodb:UpdateTable", "dynamodb:DeleteTable",
                    "dynamodb:UpdateTimeToLive", "dynamodb:UpdateContinuousBackups",
                    "dynamodb:PutResourcePolicy", "dynamodb:DeleteResourcePolicy"]},
    ])
    tags = [{"Key": "RoveLeagueCampaign", "Value": campaign},
            {"Key": "RoveLeaguePurpose", "Value": "authority-observer"}]
    return {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "Rove4k league authority foundation - isolates a retained epoch table and a read-only OIDC observer from legacy timed termination",
        "Metadata": {
            "AWSToolsMetrics": {"AWSAgentToolkit": "aws-cloudformation@3"},
            "com.aws.cloudformation.Context": {
                "arch": "Single home-region epoch table and exact GitHub environment observer; no writer or game host.",
                "must": ["No EC2 launch, GO or termination permissions.",
                         "Keep distinct from the legacy deadline stack and its campaign namespace.",
                         "A validated independent history anchor, owner fence and recovery path precede any writer.",
                         "Do not turn the user budget or finish-started-games policy into a time-based kill."],
            },
        },
        "Parameters": {
            "CampaignId": {"Type": "String", "AllowedPattern": "league-[A-Za-z0-9_.-]{0,89}",
                           "MinLength": 7, "MaxLength": 96,
                           "Description": "Exact isolated league campaign partition key."},
            "GitHubEnvironment": {"Type": "String", "AllowedPattern": "[A-Za-z0-9][A-Za-z0-9_.-]{0,63}",
                                  "MinLength": 1, "MaxLength": 64,
                                  "Description": "Existing protected GitHub environment for the read-only observer."},
            "HomeRegion": {"Type": "String", "Default": "ap-southeast-2",
                           "AllowedPattern": "[a-z][a-z0-9]*(?:-[a-z0-9]+)+-[0-9]+",
                           "MaxLength": 63,
                           "Description": "Single authority home region; must equal this stack region."},
        },
        "Rules": {"AuthorityHomeRegion": {"Assertions": [{
            "Assert": {"Fn::Equals": [_ref("HomeRegion"), _ref("AWS::Region")]},
            "AssertDescription": "Deploy the authority table in its declared home region.",
        }]}},
        "Resources": {
            "EpochTable": {
                "Type": "AWS::DynamoDB::Table", "DeletionPolicy": "Retain", "UpdateReplacePolicy": "Retain",
                "Metadata": {"com.aws.cloudformation.Context": {
                    "why": "Preserve a dedicated epoch history and exact campaign partition for a later verified coordinator.",
                    "must": ["Retain on stack removal or replacement; do not enable TTL.",
                             "PITR and deletion protection are not an authenticated independent anchor.",
                             "Do not add replicas or swap to a restored table without a recovery audit."],
                }},
                "Properties": {
                    "BillingMode": "PAY_PER_REQUEST", "DeletionProtectionEnabled": True,
                    "PointInTimeRecoverySpecification": {"PointInTimeRecoveryEnabled": True},
                    "SSESpecification": {"SSEEnabled": True},
                    "AttributeDefinitions": [{"AttributeName": "campaign_id", "AttributeType": "S"},
                                             {"AttributeName": "record_id", "AttributeType": "S"}],
                    "KeySchema": [{"AttributeName": "campaign_id", "KeyType": "HASH"},
                                  {"AttributeName": "record_id", "KeyType": "RANGE"}],
                    "Tags": tags,
                },
            },
            "ObserverRole": {
                "Type": "AWS::IAM::Role",
                "Metadata": {"com.aws.cloudformation.Context": {
                    "why": "Restrict a separate GitHub identity to observing one league partition.",
                    "must": ["Never grant or infer writer, EC2, GO or host termination authority from this role.",
                             "Protect the named GitHub environment and verify the existing OIDC provider separately.",
                             "A GitHub environment subject does not identify a particular workflow file."],
                }},
                "Properties": {"AssumeRolePolicyDocument": _policy([oidc_trust]),
                               "Policies": [{"PolicyName": "observe-league-epoch-only", "PolicyDocument": observer_policy}],
                               "Tags": tags},
            },
        },
        "Outputs": {
            "EpochTableName": {"Description": "Isolated league epoch table name; not an initialized or trusted HEAD.",
                               "Value": _ref("EpochTable")},
            "EpochTableArn": {"Description": "Exact table ARN for subsequent recovery audits.", "Value": table_arn},
            "ObserverRoleArn": {"Description": "Read-only OIDC observer role ARN; not a writer.", "Value": _arn("ObserverRole")},
        },
    }


if __name__ == "__main__":
    print(json.dumps(template(), indent=2, sort_keys=True))
