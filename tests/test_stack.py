import aws_cdk as cdk
from aws_cdk.assertions import Match, Template

from infra.stack import KnowledgeBaseAgentStack


def make_template(tmp_path):
    # Any folder works as Lambda code for a synth test.
    (tmp_path / "placeholder.py").write_text("")
    app = cdk.App()
    stack = KnowledgeBaseAgentStack(app, "TestStack", lambda_code_path=str(tmp_path))
    return Template.from_stack(stack)


def test_stack_has_the_main_resources(tmp_path):
    template = make_template(tmp_path)

    template.resource_count_is("AWS::Bedrock::KnowledgeBase", 1)
    template.resource_count_is("AWS::Bedrock::DataSource", 1)
    template.resource_count_is("AWS::S3Vectors::VectorBucket", 1)
    template.resource_count_is("AWS::S3Vectors::Index", 1)
    template.resource_count_is("AWS::ApiGateway::RestApi", 1)


def test_ask_endpoint_needs_an_api_key(tmp_path):
    template = make_template(tmp_path)

    template.has_resource_properties(
        "AWS::ApiGateway::Method",
        {"HttpMethod": "POST", "ApiKeyRequired": True},
    )


def test_api_is_rate_limited(tmp_path):
    template = make_template(tmp_path)

    template.has_resource_properties(
        "AWS::ApiGateway::UsagePlan",
        {"Throttle": {"RateLimit": 2, "BurstLimit": 5}},
    )


def test_docs_bucket_is_private(tmp_path):
    template = make_template(tmp_path)

    template.has_resource_properties(
        "AWS::S3::Bucket",
        {
            "PublicAccessBlockConfiguration": Match.object_like(
                {"BlockPublicAcls": True, "RestrictPublicBuckets": True}
            )
        },
    )
