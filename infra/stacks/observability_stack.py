"""Observability stack — CloudWatch log groups, alarms, and dashboard."""

from __future__ import annotations

import aws_cdk as cdk
import aws_cdk.aws_apigateway as apigw
import aws_cdk.aws_cloudwatch as cloudwatch
import aws_cdk.aws_lambda as lambda_
import aws_cdk.aws_logs as logs
from constructs import Construct


class ObservabilityStack(cdk.Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        env_name: str,
        lambda_function: lambda_.Function,
        api: apigw.LambdaRestApi,
        **kwargs: object,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ── CloudWatch log group ──────────────────────────────────────────────
        logs.LogGroup(
            self,
            "LambdaLogGroup",
            log_group_name=f"/aws/lambda/{lambda_function.function_name}",
            retention=logs.RetentionDays.ONE_MONTH if env_name != "prod" else logs.RetentionDays.THREE_MONTHS,
            removal_policy=cdk.RemovalPolicy.DESTROY,
        )

        # ── Lambda error alarm ────────────────────────────────────────────────
        lambda_errors_alarm = cloudwatch.Alarm(
            self,
            "LambdaErrorsAlarm",
            alarm_name=f"greyhound-facts-lambda-errors-{env_name}",
            metric=lambda_function.metric_errors(
                period=cdk.Duration.minutes(5),
                statistic="Sum",
            ),
            threshold=5,
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
            alarm_description="Lambda function errors in the last 5 minutes",
        )

        # ── Lambda duration alarm ─────────────────────────────────────────────
        cloudwatch.Alarm(
            self,
            "LambdaDurationAlarm",
            alarm_name=f"greyhound-facts-lambda-duration-{env_name}",
            metric=lambda_function.metric_duration(
                period=cdk.Duration.minutes(5),
                statistic="p95",
            ),
            threshold=5000,  # 5 seconds p95
            evaluation_periods=3,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
            alarm_description="Lambda p95 duration > 5s over 15 minutes",
        )

        # ── API Gateway 5xx alarm ─────────────────────────────────────────────
        cloudwatch.Alarm(
            self,
            "Api5xxAlarm",
            alarm_name=f"greyhound-facts-api-5xx-{env_name}",
            metric=cloudwatch.Metric(
                namespace="AWS/ApiGateway",
                metric_name="5XXError",
                dimensions_map={
                    "ApiName": api.rest_api_name,
                    "Stage": env_name,
                },
                period=cdk.Duration.minutes(5),
                statistic="Sum",
            ),
            threshold=10,
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
            alarm_description="API Gateway 5xx errors in the last 5 minutes",
        )

        # ── Dashboard ─────────────────────────────────────────────────────────
        cloudwatch.Dashboard(
            self,
            "Dashboard",
            dashboard_name=f"greyhound-facts-api-{env_name}",
            widgets=[
                [
                    cloudwatch.GraphWidget(
                        title="Lambda Invocations & Errors",
                        left=[
                            lambda_function.metric_invocations(period=cdk.Duration.minutes(5)),
                            lambda_function.metric_errors(period=cdk.Duration.minutes(5)),
                        ],
                    ),
                    cloudwatch.GraphWidget(
                        title="Lambda Duration (p50 / p95)",
                        left=[
                            lambda_function.metric_duration(
                                period=cdk.Duration.minutes(5), statistic="p50"
                            ),
                            lambda_function.metric_duration(
                                period=cdk.Duration.minutes(5), statistic="p95"
                            ),
                        ],
                    ),
                ],
                [
                    cloudwatch.GraphWidget(
                        title="API Gateway Requests & 5xx",
                        left=[
                            cloudwatch.Metric(
                                namespace="AWS/ApiGateway",
                                metric_name="Count",
                                dimensions_map={"ApiName": api.rest_api_name, "Stage": env_name},
                                period=cdk.Duration.minutes(5),
                                statistic="Sum",
                            ),
                            cloudwatch.Metric(
                                namespace="AWS/ApiGateway",
                                metric_name="5XXError",
                                dimensions_map={"ApiName": api.rest_api_name, "Stage": env_name},
                                period=cdk.Duration.minutes(5),
                                statistic="Sum",
                            ),
                        ],
                    ),
                ],
            ],
        )
