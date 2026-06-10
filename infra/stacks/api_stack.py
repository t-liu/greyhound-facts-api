"""API stack — Lambda function + API Gateway + EventBridge warm-up rule."""

from __future__ import annotations

import os
import aws_cdk as cdk
import aws_cdk.aws_apigateway as apigw
import aws_cdk.aws_dynamodb as dynamodb
import aws_cdk.aws_events as events
import aws_cdk.aws_events_targets as targets
import aws_cdk.aws_iam as iam
import aws_cdk.aws_lambda as lambda_
import aws_cdk.aws_secretsmanager as secretsmanager
from constructs import Construct
from aws_cdk.aws_lambda_python_alpha import PythonFunction
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

        # ── Lambda function ───────────────────────────────────────────────────
        self.lambda_function = PythonFunction(
            self,
            "GreyhoundFactsLambda",
            entry=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "app")),
            index="lambda_handler.py",
            handler="handler",
            runtime=lambda_.Runtime.PYTHON_3_12,
            environment={
                "APP_ENV": env_name,
                "LOG_LEVEL": "INFO",
                "DYNAMODB_TABLE_NAME": table.table_name,
                "SECRETS_MANAGER_SECRET_NAME": api_key_secret.secret_name,
            },
            timeout=cdk.Duration.seconds(30),
            memory_size=256,
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
        cdk.CfnOutput(self, "LambdaFunctionName", value=self.lambda_function.function_name)
