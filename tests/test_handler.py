import base64
import json

from agent import handler as handler_module
from agent.handler import handler


def make_event(body, encoded=False):
    return {"body": body, "isBase64Encoded": encoded}


def read_body(response):
    return json.loads(response["body"])


def test_returns_answer(monkeypatch):
    monkeypatch.setattr(
        handler_module,
        "answer_question",
        lambda question: {"answer": f"Echo: {question}", "sources": ["a.md"]},
    )

    response = handler(make_event(json.dumps({"question": " What is leave? "})), None)

    assert response["statusCode"] == 200
    assert read_body(response) == {"answer": "Echo: What is leave?", "sources": ["a.md"]}


def test_accepts_base64_body(monkeypatch):
    monkeypatch.setattr(
        handler_module,
        "answer_question",
        lambda question: {"answer": question, "sources": []},
    )
    body = base64.b64encode(json.dumps({"question": "Hello"}).encode()).decode()

    response = handler(make_event(body, encoded=True), None)

    assert read_body(response)["answer"] == "Hello"


def test_rejects_invalid_json():
    response = handler(make_event("not json"), None)
    assert response["statusCode"] == 400
    assert "valid JSON" in read_body(response)["error"]


def test_rejects_missing_body():
    response = handler({}, None)
    assert response["statusCode"] == 400


def test_rejects_empty_question():
    response = handler(make_event(json.dumps({"question": "   "})), None)
    assert response["statusCode"] == 400


def test_rejects_question_that_is_not_text():
    response = handler(make_event(json.dumps({"question": 42})), None)
    assert response["statusCode"] == 400


def test_rejects_long_question():
    response = handler(make_event(json.dumps({"question": "a" * 1001})), None)
    assert response["statusCode"] == 400
    assert "too long" in read_body(response)["error"]


def test_hides_internal_errors(monkeypatch):
    def fail(question):
        raise RuntimeError("secret detail")

    monkeypatch.setattr(handler_module, "answer_question", fail)

    response = handler(make_event(json.dumps({"question": "Hi"})), None)

    assert response["statusCode"] == 502
    assert "secret detail" not in response["body"]
