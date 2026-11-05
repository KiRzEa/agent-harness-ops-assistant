from langchain_core.messages import HumanMessage

from src.ai_models.chat_model import build_chat_model


def test_chat_model_never_stores_requests_at_openai(settings):
    chat_model = build_chat_model(settings)
    payload = chat_model._get_request_payload([HumanMessage(content="hello")])
    assert chat_model.store is False
    assert payload["store"] is False
