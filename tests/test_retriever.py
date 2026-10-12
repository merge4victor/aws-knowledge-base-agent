from agent.retriever import search_knowledge_base, source_name


class FakeClient:
    def __init__(self, results):
        self.results = results
        self.calls = []

    def retrieve(self, **kwargs):
        self.calls.append(kwargs)
        return {"retrievalResults": self.results}


def make_result(text, uri, score=0.5):
    return {
        "content": {"text": text},
        "location": {"s3Location": {"uri": uri}},
        "score": score,
    }


def test_source_name_is_the_file_name():
    result = make_result("x", "s3://docs-bucket/leave_policy.md")
    assert source_name(result) == "leave_policy.md"


def test_source_name_without_location():
    assert source_name({"content": {"text": "x"}}) == "unknown"


def test_search_returns_passages():
    client = FakeClient(
        [make_result("  Staff get 20 days.  ", "s3://docs/leave_policy.md", 0.9)]
    )

    passages = search_knowledge_base("annual leave", client=client)

    assert passages == [
        {"text": "Staff get 20 days.", "source": "leave_policy.md", "score": 0.9}
    ]


def test_search_sends_query_and_limit():
    client = FakeClient([])

    search_knowledge_base("expenses", client=client, max_results=3)

    call = client.calls[0]
    assert call["knowledgeBaseId"] == "TESTKB1234"
    assert call["retrievalQuery"] == {"text": "expenses"}
    config = call["retrievalConfiguration"]["vectorSearchConfiguration"]
    assert config["numberOfResults"] == 3


def test_search_skips_empty_passages():
    client = FakeClient([make_result("   ", "s3://docs/empty.md")])
    assert search_knowledge_base("anything", client=client) == []
