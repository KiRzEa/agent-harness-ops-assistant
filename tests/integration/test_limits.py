from src.tools.failure_injection import FailureInjector
from tests.fakes import ScriptedChatModel, tool_call_message


async def test_endless_tool_calling_stops_at_step_limit(harness_factory):
    chat_model = ScriptedChatModel(
        responses=[tool_call_message("get_service_status", {"service_name": "auth-service"})],
        repeat_last_response=True,
    )
    harness = harness_factory(chat_model)

    run = await harness.service.start_run("Keep checking")

    assert run["status"] == "LIMIT_EXCEEDED"
    assert run["error"]["code"] == "max_steps"
    assert run["step_count"] == harness.settings.max_steps
    types = [e["type"] for e in await harness.service.get_trace(run["run_id"])]
    assert types.count("tool_result") == harness.settings.max_steps
    assert types[-2:] == ["limit_exceeded", "run_finished"]


async def test_slow_tool_hits_the_time_limit(harness_factory, settings):
    short_settings = settings.model_copy(update={"max_run_seconds": 0.5, "tool_timeout_seconds": 5})
    chat_model = ScriptedChatModel(
        responses=[tool_call_message("get_service_status", {"service_name": "auth-service"})],
        repeat_last_response=True,
    )
    injector = FailureInjector("timeout", fail_times=99, slow_seconds=10)
    harness = harness_factory(chat_model, injector=injector, settings_override=short_settings)

    run = await harness.service.start_run("Check auth")

    assert run["status"] == "LIMIT_EXCEEDED"
    assert run["error"]["code"] == "max_run_seconds"


async def test_slow_model_hits_the_time_limit(harness_factory, settings):
    short_settings = settings.model_copy(update={"max_run_seconds": 0.3})
    chat_model = ScriptedChatModel(
        responses=[tool_call_message("get_service_status", {"service_name": "auth-service"})],
        call_delay_seconds=5,
    )
    harness = harness_factory(chat_model, settings_override=short_settings)

    run = await harness.service.start_run("Check auth")

    assert run["status"] == "LIMIT_EXCEEDED"
    assert run["error"]["code"] == "max_run_seconds"


async def test_model_provider_error_fails_the_run_cleanly(harness_factory):
    chat_model = ScriptedChatModel(responses=[RuntimeError("provider unavailable")])
    harness = harness_factory(chat_model)

    run = await harness.service.start_run("Anything")

    assert run["status"] == "FAILED"
    assert run["error"]["code"] == "llm_error"
