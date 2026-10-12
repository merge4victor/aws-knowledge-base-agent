"""Settings for the agent. All values come from environment variables."""

import os

# Id of the Bedrock knowledge base that holds the company documents.
KNOWLEDGE_BASE_ID = os.environ.get("KNOWLEDGE_BASE_ID", "")

# Bedrock model or inference profile id used to write the answers.
MODEL_ID = os.environ.get("MODEL_ID", "global.anthropic.claude-haiku-4-5-20251001-v1:0")

# How many passages to fetch for each search.
MAX_RESULTS = int(os.environ.get("MAX_RESULTS", "5"))

# Longest question we accept, in characters.
MAX_QUESTION_CHARS = int(os.environ.get("MAX_QUESTION_CHARS", "1000"))

# Upper limit for the length of one model reply.
MAX_ANSWER_TOKENS = int(os.environ.get("MAX_ANSWER_TOKENS", "2000"))
