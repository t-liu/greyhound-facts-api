"""Security stack — Secrets Manager secret + Lambda IAM role."""

from __future__ import annotations

import aws_cdk as cdk
import aws_cdk.aws_iam as iam
import aws_cdk.aws_secretsmanager as secretsmanager
from constructs import Construct


class SecurityStack(cdk.Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        env_name: str,
        **kwargs: object,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ── Admin API key in Secrets Manager ──────────────────────────────────
        self.api_key_secret = secretsmanager.Secret(
            self,
            "AdminApiKeySecret",
            secret_name=f"greyhound-facts/{env_name}/admin-api-key",
            description="Admin API key for Greyhound Facts API",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                exclude_punctuation=True,
                password_length=32,
            ),
        )

        # ── Lambda execution role ─────────────────────────────────────────────
        self.lambda_role = iam.Role(
            self,
            "LambdaExecutionRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                )
            ],
        )

        # Allow Lambda to read the API key secret
        self.api_key_secret.grant_read(self.lambda_role)

        cdk.CfnOutput(self, "SecretArn", value=self.api_key_secret.secret_arn)
        cdk.CfnOutput(self, "LambdaRoleArn", value=self.lambda_role.role_arn)
