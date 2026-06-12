#!/usr/bin/env python3
"""CDK application entry point."""

import os
import aws_cdk as cdk
from dotenv import load_dotenv

from stacks.data_stack import DataStack
from stacks.security_stack import SecurityStack
from stacks.api_stack import ApiStack
from stacks.observability_stack import ObservabilityStack

load_dotenv()
app = cdk.App()

env_name = app.node.try_get_context("env") or "dev"
account = app.node.try_get_context("account")
region = app.node.try_get_context("region") or "us-east-1"

env = cdk.Environment(account=account, region=region)

data_stack = DataStack(app, f"GreyhoundData-{env_name}", env=env, env_name=env_name)
security_stack = SecurityStack(app, f"GreyhoundSecurity-{env_name}", env=env, env_name=env_name)
api_stack = ApiStack(
    app,
    f"GreyhoundApi-{env_name}",
    env=env,
    env_name=env_name,
    table=data_stack.table,
    api_key_secret=security_stack.api_key_secret,
    lambda_role=security_stack.lambda_role,
)
observability_stack = ObservabilityStack(
    app,
    f"GreyhoundObservability-{env_name}",
    env=env,
    env_name=env_name,
    lambda_function=api_stack.lambda_function,
    api=api_stack.api,
)

cdk.Tags.of(app).add("Project", "greyhound-facts-api")
cdk.Tags.of(app).add("Environment", env_name)
cdk.Tags.of(app).add("ManagedBy", "cdk")

app.synth()
