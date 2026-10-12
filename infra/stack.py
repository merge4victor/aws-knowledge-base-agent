"""All AWS resources for the knowledge base agent."""

import aws_cdk as cdk
from aws_cdk import aws_apigateway as apigw
from aws_cdk import aws_bedrock as bedrock
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_logs as logs
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_s3vectors as s3vectors
from constructs import Construct

EMBEDDING_MODEL_ID = "amazon.titan-embed-text-v2:0"
EMBEDDING_DIMENSIONS = 1024
DEFAULT_MODEL_ID = "global.anthropic.claude-haiku-4-5-20251001-v1:0"


class KnowledgeBaseAgentStack(cdk.Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        lambda_code_path: str = "build/lambda",
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Override with: cdk deploy -c model_id=<model or inference profile id>
        model_id = self.node.try_get_context("model_id") or DEFAULT_MODEL_ID
        embedding_model_arn = (
            f"arn:aws:bedrock:{self.region}::foundation-model/{EMBEDDING_MODEL_ID}"
        )

        # Bucket that holds the source documents.
        docs_bucket = s3.Bucket(
            self,
            "DocsBucket",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            removal_policy=cdk.RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        # Vector store for the document embeddings.
        vector_bucket = s3vectors.CfnVectorBucket(self, "VectorBucket")
        vector_index = s3vectors.CfnIndex(
            self,
            "VectorIndex",
            vector_bucket_arn=vector_bucket.attr_vector_bucket_arn,
            data_type="float32",
            dimension=EMBEDDING_DIMENSIONS,
            distance_metric="cosine",
            # Bedrock stores the passage text in these keys. They are too large
            # to be used as filters, so they must be marked as non filterable.
            metadata_configuration=s3vectors.CfnIndex.MetadataConfigurationProperty(
                non_filterable_metadata_keys=[
                    "AMAZON_BEDROCK_TEXT",
                    "AMAZON_BEDROCK_METADATA",
                ]
            ),
        )

        # Role that Bedrock uses to read documents and write vectors.
        kb_role = iam.Role(
            self,
            "KnowledgeBaseRole",
            assumed_by=iam.ServicePrincipal(
                "bedrock.amazonaws.com",
                conditions={"StringEquals": {"aws:SourceAccount": self.account}},
            ),
        )
        docs_bucket.grant_read(kb_role)
        kb_role.add_to_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel"],
                resources=[embedding_model_arn],
            )
        )
        kb_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "s3vectors:GetIndex",
                    "s3vectors:PutVectors",
                    "s3vectors:GetVectors",
                    "s3vectors:DeleteVectors",
                    "s3vectors:QueryVectors",
                ],
                resources=[vector_index.attr_index_arn],
            )
        )

        knowledge_base = bedrock.CfnKnowledgeBase(
            self,
            "KnowledgeBase",
            name=f"{construct_id}-docs",
            role_arn=kb_role.role_arn,
            knowledge_base_configuration=bedrock.CfnKnowledgeBase.KnowledgeBaseConfigurationProperty(
                type="VECTOR",
                vector_knowledge_base_configuration=bedrock.CfnKnowledgeBase.VectorKnowledgeBaseConfigurationProperty(
                    embedding_model_arn=embedding_model_arn,
                ),
            ),
            storage_configuration=bedrock.CfnKnowledgeBase.StorageConfigurationProperty(
                type="S3_VECTORS",
                s3_vectors_configuration=bedrock.CfnKnowledgeBase.S3VectorsConfigurationProperty(
                    vector_bucket_arn=vector_bucket.attr_vector_bucket_arn,
                    index_arn=vector_index.attr_index_arn,
                ),
            ),
        )
        # The role policy must exist before Bedrock checks its access.
        knowledge_base.node.add_dependency(kb_role)

        data_source = bedrock.CfnDataSource(
            self,
            "DocsDataSource",
            name="company-docs",
            knowledge_base_id=knowledge_base.attr_knowledge_base_id,
            data_deletion_policy="RETAIN",
            data_source_configuration=bedrock.CfnDataSource.DataSourceConfigurationProperty(
                type="S3",
                s3_configuration=bedrock.CfnDataSource.S3DataSourceConfigurationProperty(
                    bucket_arn=docs_bucket.bucket_arn,
                ),
            ),
        )

        # Lambda function that runs the agent.
        agent_function = lambda_.Function(
            self,
            "AgentFunction",
            runtime=lambda_.Runtime.PYTHON_3_13,
            architecture=lambda_.Architecture.X86_64,
            handler="agent.handler.handler",
            code=lambda_.Code.from_asset(lambda_code_path),
            memory_size=512,
            # API Gateway gives up after 29 seconds, so there is no point in more.
            timeout=cdk.Duration.seconds(29),
            log_group=logs.LogGroup(
                self,
                "AgentLogs",
                retention=logs.RetentionDays.ONE_MONTH,
                removal_policy=cdk.RemovalPolicy.DESTROY,
            ),
            environment={
                "KNOWLEDGE_BASE_ID": knowledge_base.attr_knowledge_base_id,
                "MODEL_ID": model_id,
            },
        )
        agent_function.add_to_role_policy(
            iam.PolicyStatement(
                actions=["bedrock:Retrieve"],
                resources=[knowledge_base.attr_knowledge_base_arn],
            )
        )
        # An inference profile can route to any region, so the model
        # permission cannot be pinned to one region.
        agent_function.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream",
                ],
                resources=[
                    "arn:aws:bedrock:*::foundation-model/*",
                    f"arn:aws:bedrock:*:{self.account}:inference-profile/*",
                ],
            )
        )

        # Public API. Callers need an API key and are rate limited.
        api = apigw.RestApi(
            self,
            "Api",
            rest_api_name=f"{construct_id}-api",
            deploy_options=apigw.StageOptions(stage_name="prod"),
        )
        api.root.add_resource("ask").add_method(
            "POST",
            apigw.LambdaIntegration(agent_function),
            api_key_required=True,
        )
        api_key = api.add_api_key("ApiKey")
        usage_plan = api.add_usage_plan(
            "UsagePlan",
            throttle=apigw.ThrottleSettings(rate_limit=2, burst_limit=5),
            quota=apigw.QuotaSettings(limit=500, period=apigw.Period.DAY),
        )
        usage_plan.add_api_key(api_key)
        usage_plan.add_api_stage(stage=api.deployment_stage)

        cdk.CfnOutput(self, "AskUrl", value=f"{api.url}ask")
        cdk.CfnOutput(self, "ApiKeyId", value=api_key.key_id)
        cdk.CfnOutput(self, "DocsBucketName", value=docs_bucket.bucket_name)
        cdk.CfnOutput(
            self, "KnowledgeBaseId", value=knowledge_base.attr_knowledge_base_id
        )
        cdk.CfnOutput(self, "DataSourceId", value=data_source.attr_data_source_id)
