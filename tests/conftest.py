import os

# Dummy AWS settings so no test can reach a real account by accident.
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
os.environ.setdefault("KNOWLEDGE_BASE_ID", "TESTKB1234")
