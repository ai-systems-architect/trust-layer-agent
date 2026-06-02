"""
Bedrock LLM client for the Governed Compliance Agent.

Model: Claude Sonnet via AWS Bedrock (model ID from BEDROCK_MODEL_ID env var).
Used in: sufficiency_assessment_node, drafting_node.

Temperature is fixed at 0 for deterministic governance assessments — the LLM
provides structured evaluation, not creative generation. The routing functions
enforce hard boundaries; the LLM determines sufficiency within those bounds.

Prompt caching is enabled by default (use_cache=True in invoke_with_logging).
The system prompt is marked as ephemeral cache. On cache hit, the sufficiency
assessment input tokens are reduced to the user-prompt tokens only. Cache
metrics (cache_read_input_tokens, cache_creation_input_tokens) are captured
in token_usage and logged for Phase 3 evaluation baseline comparison.

The caching path bypasses ChatBedrock to use boto3 invoke_model directly —
this gives full control over the cache_control field in the system block and
the anthropic-beta header injection via botocore event. The non-caching path
uses ChatBedrock with SystemMessage as before.

References:
    DL-031: LangGraph selected; Bedrock as inference provider
    DL-034: Bedrock model selection; read_timeout fix for drafting calls
    DL-037: Token cost baseline; prompt caching reduces per-control cost
    Framework Section 11.3: Probabilistic reasoning within deterministic bounds
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Optional, Tuple

import boto3
from botocore.config import Config
from langchain_aws import ChatBedrock
from langchain_core.messages import HumanMessage, SystemMessage

try:
    from langfuse import observe as _lf_observe, get_client as _lf_get_client
except Exception:  # noqa: BLE001
    def _lf_observe(*_a: Any, **_kw: Any) -> Any:  # type: ignore[misc]
        return _a[0] if _a and callable(_a[0]) else (lambda f: f)

    def _lf_get_client() -> Any:  # type: ignore[misc]
        return None

logger = logging.getLogger(__name__)

BEDROCK_MODEL_ID = os.getenv(
    "BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
)
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

_BEDROCK_CONFIG = Config(
    read_timeout=300,
    connect_timeout=30,
    retries={"max_attempts": 2, "mode": "standard"},
)

# Lazy-initialised boto3 bedrock-runtime client for caching-enabled calls.
# The prompt-caching beta header is registered once via botocore event.
_caching_client: Optional[Any] = None


def _inject_caching_header(request: Any, **_kwargs: Any) -> None:
    """Inject the Anthropic prompt-caching beta header before the request is sent."""
    request.headers["anthropic-beta"] = "prompt-caching-2024-07-31"


def _get_caching_client() -> Any:
    """
    Return a lazy-initialised boto3 bedrock-runtime client with the
    prompt-caching beta header injected via botocore before-send event.

    Module-level singleton — the event is registered once; subsequent
    calls return the same client without re-registering.
    """
    global _caching_client
    if _caching_client is None:
        client = boto3.client(
            "bedrock-runtime",
            region_name=AWS_REGION,
            config=_BEDROCK_CONFIG,
        )
        client.meta.events.register(
            "before-send.bedrock-runtime.InvokeModel",
            _inject_caching_header,
        )
        _caching_client = client
    return _caching_client


def get_llm() -> ChatBedrock:
    """
    Initialise and return a Bedrock LLM client.

    temperature=0 enforces deterministic, structured output for governance
    assessments. max_tokens=8192 accommodates full evidence summaries.

    read_timeout=300 allows up to 5 minutes for large drafting responses
    (evidence summary + 4-control assessment can generate 2000+ output tokens).
    The botocore default of 60 s is too short for the drafting node.

    Note: When use_cache=True (default), invoke_with_logging uses
    _get_caching_client() directly rather than this ChatBedrock client,
    to have full control over the cache_control field in the system block.
    """
    return ChatBedrock(
        model_id=BEDROCK_MODEL_ID,
        region_name=AWS_REGION,
        model_kwargs={
            "temperature": 0,
            "max_tokens": 8192,
        },
        config=_BEDROCK_CONFIG,
    )


def invoke_with_logging(
    llm: ChatBedrock,
    system_prompt: str,
    user_prompt: str,
    run_id: str,
    node_name: str,
    use_cache: bool = True,
) -> Tuple[str, Dict[str, object]]:
    """
    Invoke the LLM and return (response_text, token_usage).

    When use_cache=True (default), delegates to _invoke_cached() — a direct
    boto3 call that passes the system prompt with cache_control: ephemeral and
    injects the anthropic-beta header. Cache hits appear as non-zero
    cache_read_input_tokens in the returned token_usage dict.

    When use_cache=False, falls back to ChatBedrock with SystemMessage.
    cache_read_input_tokens and cache_creation_input_tokens are set to 0.

    Args:
        llm:           Initialized ChatBedrock client (used only when use_cache=False).
        system_prompt: Governance system instructions.
        user_prompt:   Control-specific evidence and query.
        run_id:        Current run ID for log correlation.
        node_name:     Node context label for log and trace output.
        use_cache:     Enable prompt caching for the system prompt (default True).

    Returns:
        Tuple of (response text, token usage dict with cache metrics).
    """
    if use_cache:
        return _invoke_cached(system_prompt, user_prompt, run_id, node_name)

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]
    response = llm.invoke(messages)

    usage_metadata = response.usage_metadata or {}
    input_tokens = usage_metadata.get("input_tokens", 0)
    output_tokens = usage_metadata.get("output_tokens", 0)

    token_usage: Dict[str, object] = {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cache_read_input_tokens": 0,
        "cache_creation_input_tokens": 0,
        "node": node_name,
        "run_id": run_id,
    }

    logger.info(
        "[%s] %s — tokens in: %s out: %s cache_read: 0 cache_write: 0",
        run_id,
        node_name,
        input_tokens,
        output_tokens,
    )

    return response.content, token_usage


@_lf_observe(name="bedrock_invoke", as_type="generation", capture_input=False, capture_output=False)
def _invoke_cached(
    system_prompt: str,
    user_prompt: str,
    run_id: str,
    node_name: str,
) -> Tuple[str, Dict[str, object]]:
    """
    Direct boto3 Bedrock invocation with prompt caching enabled.

    Bypasses ChatBedrock to have full control over the API call structure:
    - cache_control: ephemeral on the system block marks it as cacheable
    - anthropic-beta header injected via botocore event before the request is sent

    On first call, system prompt tokens are written to cache
    (cache_creation_input_tokens). Subsequent calls within the 5-minute TTL
    hit the cache (cache_read_input_tokens), reducing per-control sufficiency
    assessment cost to user-prompt tokens only.
    """
    client = _get_caching_client()

    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 8192,
        "temperature": 0,
        "system": [
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        "messages": [{"role": "user", "content": user_prompt}],
    }

    resp = client.invoke_model(
        modelId=BEDROCK_MODEL_ID,
        body=json.dumps(body),
        contentType="application/json",
        accept="application/json",
    )

    resp_body = json.loads(resp["body"].read())
    text = resp_body["content"][0]["text"]
    usage = resp_body.get("usage", {})

    input_tokens = usage.get("input_tokens", 0)
    output_tokens = usage.get("output_tokens", 0)
    cache_read = usage.get("cache_read_input_tokens", 0)
    cache_write = usage.get("cache_creation_input_tokens", 0)

    token_usage: Dict[str, object] = {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cache_read_input_tokens": cache_read,
        "cache_creation_input_tokens": cache_write,
        "node": node_name,
        "run_id": run_id,
    }

    logger.info(
        "[%s] %s — tokens in: %s out: %s cache_read: %s cache_write: %s",
        run_id,
        node_name,
        input_tokens,
        output_tokens,
        cache_read,
        cache_write,
    )

    # Record generation metadata in the Langfuse span.
    try:
        _lf_get_client().update_current_generation(
            name=node_name,
            model=BEDROCK_MODEL_ID,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            output=text,
            usage_details={
                "input": input_tokens,
                "output": output_tokens,
                "cache_read_input_tokens": cache_read,
                "cache_creation_input_tokens": cache_write,
            },
            metadata={"run_id": run_id},
        )
    except Exception:  # noqa: BLE001
        pass

    return text, token_usage
