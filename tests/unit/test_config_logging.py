import json

from src.core.config import Settings
from src.core.logging import configure_logging, get_logger


def test_defaults_are_safe_limits():
    settings = Settings(_env_file=None)
    assert settings.max_steps == 8
    assert settings.max_run_seconds == 60
    assert settings.tool_max_retries == 2
    assert settings.failure_mode == "none"


def test_api_key_is_hidden_in_repr():
    settings = Settings(_env_file=None, openai_api_key="sk-very-secret")
    assert "sk-very-secret" not in repr(settings)


def test_logs_redact_sensitive_keys(capsys):
    configure_logging()
    get_logger("test").info("hello", run_id="run-1", api_key="sk-very-secret")
    line = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert line["run_id"] == "run-1"
    assert line["api_key"] == "***"
