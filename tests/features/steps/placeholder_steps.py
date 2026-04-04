# pyright: reportCallIssue=false
from behave import given  # type: ignore[import-untyped]


@given("a placeholder step")
def step_placeholder(context):
    context.placeholder = True
