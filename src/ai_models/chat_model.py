from langchain_openai import ChatOpenAI

from src.core.config import Settings


def build_chat_model(settings: Settings) -> ChatOpenAI:
    # store=False keeps prompts and responses out of the OpenAI dashboard.
    return ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        store=False,
        timeout=30,
        max_retries=2,
    )
