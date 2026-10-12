from agent import kb_agent


def test_format_passages_numbers_each_passage():
    text = kb_agent.format_passages(
        [
            {"text": "First.", "source": "a.md", "score": 0.9},
            {"text": "Second.", "source": "b.md", "score": 0.8},
        ]
    )
    assert text == "[1] source: a.md\nFirst.\n\n[2] source: b.md\nSecond."


def test_format_passages_when_nothing_found():
    assert kb_agent.format_passages([]) == "No matching passages were found."


def test_search_tool_records_each_source_once(monkeypatch):
    passages = [
        {"text": "One.", "source": "a.md", "score": 0.9},
        {"text": "Two.", "source": "a.md", "score": 0.8},
        {"text": "Three.", "source": "b.md", "score": 0.7},
    ]
    monkeypatch.setattr(kb_agent, "search_knowledge_base", lambda query: passages)
    found_sources = []

    search = kb_agent.make_search_tool(found_sources)
    output = search(query="leave")

    assert found_sources == ["a.md", "b.md"]
    assert "[3] source: b.md" in output


def test_answer_question_returns_answer_and_sources(monkeypatch):
    class FakeAgent:
        def __init__(self, tools, **kwargs):
            self.search = tools[0]

        def __call__(self, question):
            self.search(query=question)
            return "  You get 20 days.  "

    monkeypatch.setattr(kb_agent, "Agent", FakeAgent)
    monkeypatch.setattr(kb_agent, "_model", lambda: None)
    monkeypatch.setattr(
        kb_agent,
        "search_knowledge_base",
        lambda query: [{"text": "20 days.", "source": "leave_policy.md", "score": 1}],
    )

    result = kb_agent.answer_question("How much leave do I get?")

    assert result == {"answer": "You get 20 days.", "sources": ["leave_policy.md"]}
