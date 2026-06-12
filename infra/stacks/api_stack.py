"""API stack — Lambda function + API Gateway + EventBridge warm-up rule."""

from __future__ import annotations

import os
import aws_cdk as cdk
import aws_cdk.aws_apigateway as apigw
import aws_cdk.aws_certificatemanager as acm
import aws_cdk.aws_dynamodb as dynamodb
import aws_cdk.aws_events as events
import aws_cdk.aws_events_targets as targets
import aws_cdk.aws_iam as iam
import aws_cdk.aws_lambda as lambda_
import aws_cdk.aws_route53 as route53
import aws_cdk.aws_route53_targets as r53_targets
import aws_cdk.aws_secretsmanager as secretsmanager
from constructs import Construct
from aws_cdk.aws_lambda_python_alpha import PythonFunction, BundlingOptions
from aws_cdk import aws_lambda as lambda_


class ApiStack(cdk.Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        env_name: str,
        table: dynamodb.Table,
        api_key_secret: secretsmanager.Secret,
        lambda_role: iam.Role,
        **kwargs: object,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Grant DynamoDB permissions to the Lambda role
        table.grant_read_write_data(lambda_role)

        hosted_zone_name = os.environ.get("AWS_HOSTED_ZONE_NAME")        
        hosted_zone = route53.HostedZone.from_lookup(
            self, 
            "ProjectHostedZone", 
            domain_name=hosted_zone_name
        )

        if env_name == "prod":
            subdomain_record = "greyhound-facts"
        else:
            subdomain_record = f"{env_name}.greyhound-facts"

        custom_domain_name = f"{subdomain_record}.{hosted_zone_name}"

        certificate = acm.Certificate(
            self,
            "ApiCertificate",
            domain_name=custom_domain_name,
            validation=acm.CertificateValidation.from_dns(hosted_zone),
        )

        # ── Lambda function ───────────────────────────────────────────────────
        self.lambda_function = PythonFunction(
            self,
            "GreyhoundFactsLambda",
            entry=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "app")),
            index="lambda_handler.py",
            handler="handler",
            runtime=lambda_.Runtime.PYTHON_3_13,
            role=lambda_role,
            environment={
                "APP_ENV": env_name,
                "LOG_LEVEL": "INFO",
                "DYNAMODB_TABLE_NAME": table.table_name,
                "SECRETS_MANAGER_SECRET_NAME": api_key_secret.secret_name,
            },
            timeout=cdk.Duration.seconds(30),
            memory_size=256,
            bundling=BundlingOptions(
                asset_excludes=[
                    "__pycache__",
                    "*.pyc",
                    "*.pyo",
                    ".pytest_cache",
                    ".venv",
                    ".git",
                ]
            )
        )

        # ── Explicit Custom Domain Definition ─────────────────────────────
        custom_domain = apigw.DomainName(
            self,
            "GreyhoundApiCustomDomain",
            domain_name=custom_domain_name,
            certificate=certificate,
            security_policy=apigw.SecurityPolicy.TLS_1_2,
            endpoint_type=apigw.EndpointType.REGIONAL,
        )        

        # ── API Gateway ───────────────────────────────────────────────────────
        self.api = apigw.LambdaRestApi(
            self,
            "GreyhoundFactsApi",
            rest_api_name=f"greyhound-facts-api-{env_name}",
            handler=self.lambda_function,
            proxy=True,
            deploy_options=apigw.StageOptions(
                stage_name=env_name,
                throttling_rate_limit=100,
                throttling_burst_limit=200,
                logging_level=apigw.MethodLoggingLevel.INFO,
                data_trace_enabled=False,
                metrics_enabled=True,
            ),
        )

        # Bind the API Gateway to your Custom Domain
        apigw.BasePathMapping(
            self,
            "GreyhoundApiMapping",
            domain_name=custom_domain,
            rest_api=self.api,
        )

        # ── Route 53 Alias Record ─────────────────────────────────────────────
        route53.ARecord(
            self,
            "ApiGatewayAliasRecord",
            zone=hosted_zone,
            record_name=subdomain_record,
            # Pass the explicit custom_domain construct here
            target=route53.RecordTarget.from_alias(
                r53_targets.ApiGatewayDomain(custom_domain)
            ),
        )

        # ── EventBridge warm-up rule (business hours, every 5 min) ───────────
        warm_up_rule = events.Rule(
            self,
            "WarmUpRule",
            rule_name=f"greyhound-facts-warmup-{env_name}",
            description="Keep the Lambda warm during business hours",
            # Mon–Fri 8am–6pm UTC
            schedule=events.Schedule.cron(
                minute="*/5",
                hour="8-18",
                week_day="MON-FRI",
            ),
        )
        warm_up_rule.add_target(
            targets.LambdaFunction(
                self.lambda_function,
                event=events.RuleTargetInput.from_object({"source": "warmup"}),
            )
        )

        cdk.CfnOutput(self, "ApiUrl", value=self.api.url)
        cdk.CfnOutput(self, "CustomDomainUrl", value=f"https://{custom_domain_name}/")
        cdk.CfnOutput(self, "LambdaFunctionName", value=self.lambda_function.function_name)
