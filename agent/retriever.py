"""Search the Bedrock knowledge base and return plain passages."""

from functools import lru_cache

import boto3

from agent import config


@lru_cache(maxsize=1)
def _default_client():
    return boto3.client("bedrock-agent-runtime")


def source_name(result):
    """Return the file name a passage came from, or 'unknown'."""
    uri = result.get("location", {}).get("s3Location", {}).get("uri", "")
    return uri.rsplit("/", 1)[-1] or "unknown"


def search_knowledge_base(query, client=None, max_results=None):
    """Return the passages that best match the query.

    Each passage is a dict with the keys text, source and score.
    """
    client = client or _default_client()
    response = client.retrieve(
        knowledgeBaseId=config.KNOWLEDGE_BASE_ID,
        retrievalQuery={"text": query},
        retrievalConfiguration={
            "vectorSearchConfiguration": {
                "numberOfResults": max_results or config.MAX_RESULTS
            }
        },
    )

    passages = []
    for result in response.get("retrievalResults", []):
        text = result.get("content", {}).get("text", "").strip()
        if not text:
            continue
        passages.append(
            {
                "text": text,
                "source": source_name(result),
                "score": result.get("score", 0.0),
            }
        )
    return passages
