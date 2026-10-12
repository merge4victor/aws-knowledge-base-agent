"""AWS Lambda entry point for POST /ask."""

import base64
import json
import logging

from agent import config
from agent.kb_agent import answer_question

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def _response(status, body):
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def _read_question(event):
    """Return the question from the request, or raise ValueError."""
    raw = event.get("body") or ""
    if event.get("isBase64Encoded"):
        raw = base64.b64decode(raw).decode("utf-8")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        raise ValueError("Request body must be valid JSON.") from None

    question = data.get("question") if isinstance(data, dict) else None
    if not isinstance(question, str) or not question.strip():
        raise ValueError("Field 'question' is required and must be text.")

    question = question.strip()
    if len(question) > config.MAX_QUESTION_CHARS:
        raise ValueError(
            f"Question is too long. Limit is {config.MAX_QUESTION_CHARS} characters."
        )
    return question


def handler(event, context):
    try:
        question = _read_question(event)
    except ValueError as error:
        return _response(400, {"error": str(error)})

    try:
        result = answer_question(question)
    except Exception:
        # Log the details for us, but do not leak them to the caller.
        logger.exception("Failed to answer question")
        return _response(502, {"error": "The agent could not answer right now."})

    logger.info("Answered question using sources: %s", result["sources"])
    return _response(200, result)
