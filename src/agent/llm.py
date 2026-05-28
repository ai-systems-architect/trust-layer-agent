"""
Bedrock LLM client for the Governed Compliance Agent.

Model: Claude Sonnet via AWS Bedrock (model ID from BEDROCK_MODEL_ID env var).
Used in: sufficiency_assessment_node, drafting_node.

Temperature is fixed at 0 for deterministic governance assessments — the LLM
provides structured evaluation, not creative generation. The routing functions
enforce hard boundaries; the LLM determines sufficiency within those bounds.

References:
    DL-030: LangGraph selected; Bedrock as inference provider
    Framework Section 11.3: Probabilistic reasoning within deterministic bounds
"""

from __future__ import annotations

import logging
import os
from typing import Dict, Tuple

from botocore.config import Config
from langchain_aws import ChatBedrock
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)

BEDROCK_MODEL_ID = os.getenv(
    "BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
)
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")


def get_llm() -> ChatBedrock:
    """
    Initialise and return a Bedrock LLM client.

    temperature=0 enforces deterministic, structured output for governance
    assessments. max_tokens=4096 accommodates full evidence summaries.

    read_timeout=300 allows up to 5 minutes for large drafting responses
    (evidence summary + 4-control assessment can generate 2000+ output tokens).
    The botocore default of 60 s is too short for the drafting node.
    """
    bedrock_config = Config(
        read_timeout=300,
        connect_timeout=30,
        retries={"max_attempts": 2, "mode": "standard"},
    )
    return ChatBedrock(
        model_id=BEDROCK_MODEL_ID,
        region_name=AWS_REGION,
        model_kwargs={
            "temperature": 0,
            "max_tokens": 4096,
        },
        config=bedrock_config,
    )


def invoke_with_logging(
    llm: ChatBedrock,
    system_prompt: str,
    user_prompt: str,
    run_id: str,
    node_name: str,
) -> Tuple[str, Dict[str, object]]:
    """
    Invoke the LLM and return (response_text, token_usage).

    Logs token usage for Langfuse instrumentation. usage_metadata may be
    None for some Bedrock model configurations; defaults to 0 safely.

    Args:
        llm:           Initialized ChatBedrock client.
        system_prompt: Governance system instructions.
        user_prompt:   Control-specific evidence and query.
        run_id:        Current run ID for log correlation.
        node_name:     Node context label for log and trace output.

    Returns:
        Tuple of (response text, token usage dict).
    """
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    response = llm.invoke(messages)

    usage_metadata = response.usage_metadata or {}
    token_usage: Dict[str, object] = {
        "input_tokens": usage_metadata.get("input_tokens", 0),
        "output_tokens": usage_metadata.get("output_tokens", 0),
        "node": node_name,
        "run_id": run_id,
    }

    logger.info(
        "[%s] %s — tokens in: %s out: %s",
        run_id,
        node_name,
        token_usage["input_tokens"],
        token_usage["output_tokens"],
    )

    return response.content, token_usage
