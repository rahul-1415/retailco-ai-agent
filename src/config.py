import os
import boto3

_openai_key: str | None = None


def get_openai_key() -> str:
    global _openai_key
    if _openai_key:
        return _openai_key
    # Locally: OPENAI_API_KEY set directly in environment
    # On AWS: not set, so fetch from SSM using the parameter name
    if key := os.environ.get("OPENAI_API_KEY"):
        _openai_key = key
        return _openai_key
    param_name = os.environ["SSM_PARAM_NAME"]
    ssm = boto3.client("ssm")
    _openai_key = ssm.get_parameter(Name=param_name, WithDecryption=True)["Parameter"]["Value"]
    return _openai_key
