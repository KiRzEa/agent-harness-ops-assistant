from dataclasses import dataclass

from langchain_core.language_models.chat_models import BaseChatModel

from src.core.config import Settings
from src.store.events import EventLog
from src.store.runs import ApprovalRepository
from src.tools.registry import ToolSpec


@dataclass
class GraphDependencies:
    settings: Settings
    chat_model: BaseChatModel
    tools: dict[str, ToolSpec]
    events: EventLog
    approvals: ApprovalRepository
