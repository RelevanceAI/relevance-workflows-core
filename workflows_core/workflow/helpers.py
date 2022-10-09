"""
Base64 decoding for workflows
"""
import argparse
import os
import base64
import json

from typing import Any, Mapping


def decode_workflow_token(token: str) -> Mapping[str, Any]:
    """
    It takes a token, decodes it, and returns the decoded token

    Parameters
    ----------
    token
        The token that was generated by the workflow.

    Returns
    -------
        A dictionary of the workflow configuration.

    """
    config = json.loads(base64.b64decode(token + "==="))
    # Set workflow ID for tracking
    os.environ["WORKFLOW_ID"] = config.get("job_id", "")
    return config


def read_token_from_script():
    """
    Reads in a token from script and returns a config as a
    dictionary object.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("token", help="The token used for the workflow config.")
    args = parser.parse_args()
    token = args.workflow_token
    config = decode_workflow_token(token)
    return config
