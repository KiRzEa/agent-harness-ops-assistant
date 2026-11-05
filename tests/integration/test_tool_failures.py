from src.tools.failure_injection import FailureInjector
from tests.fakes import ScriptedChatModel, text_message, tool_call_message

STATUS_CALL = ("get_service_status", {"service_name": "auth-service"}, "call_status")


def status_then_answer():
    return ScriptedChatModel(
        responses=[tool_call_message(*STATUS_CALL), text_message("Final answer.")]
    )


async def event_types(harness, run_id):
    return [event["type"] for event in await harness.service.get_trace(run_id)]


async def test_transient_failure_is_retried_then_succeeds(harness_factory):
    harness = harness_factory(
        status_then_answer(), injector=FailureInjector("transient", fail_times=1)
    )

    run = await harness.service.start_run("Check auth")

    assert run["status"] == "COMPLETED"
    types = await event_types(harness, run["run_id"])
    assert types.count("tool_retry") == 1
    assert types.count("tool_result") == 1
    result_event = next(
        e for e in await harness.service.get_trace(run["run_id"]) if e["type"] == "tool_result"
    )
    assert result_event["payload"]["attempts"] == 2


async def test_transient_failure_that_never_clears_is_reported_to_the_model(harness_factory):
    chat_model = status_then_answer()
    harness = harness_factory(chat_model, injector=FailureInjector("transient", fail_times=99))

    run = await harness.service.start_run("Check auth")

    assert run["status"] == "COMPLETED"
    types = await event_types(harness, run["run_id"])
    assert types.count("tool_retry") == 2
    assert types.count("tool_error") == 1
    assert "transient_error" in chat_model.received_messages[1][-1].content


async def test_permanent_failure_is_not_retried(harness_factory):
    chat_model = status_then_answer()
    harness = harness_factory(chat_model, injector=FailureInjector("permanent"))

    run = await harness.service.start_run("Check auth")

    assert run["status"] == "COMPLETED"
    types = await event_types(harness, run["run_id"])
    assert "tool_retry" not in types and types.count("tool_error") == 1


async def test_unknown_service_error_lets_the_model_adapt(harness_factory):
    chat_model = ScriptedChatModel(
        responses=[
            tool_call_message("get_service_status", {"service_name": "billing"}, "call_status"),
            text_message("I could not find that service."),
        ]
    )
    harness = harness_factory(chat_model)

    run = await harness.service.start_run("Check billing")

    assert run["final_answer"] == "I could not find that service."
    assert "service_not_found" in chat_model.received_messages[1][-1].content


async def test_slow_tool_times_out_then_retry_succeeds(harness_factory):
    injector = FailureInjector("timeout", fail_times=1, slow_seconds=5)
    harness = harness_factory(status_then_answer(), injector=injector)

    run = await harness.service.start_run("Check auth")

    assert run["status"] == "COMPLETED"
    retry_events = [
        e for e in await harness.service.get_trace(run["run_id"]) if e["type"] == "tool_retry"
    ]
    assert retry_events[0]["payload"]["error"] == "timeout"


async def test_tool_that_always_times_out_is_surfaced_as_error(harness_factory):
    chat_model = status_then_answer()
    injector = FailureInjector("timeout", fail_times=99, slow_seconds=5)
    harness = harness_factory(chat_model, injector=injector)

    run = await harness.service.start_run("Check auth")

    assert run["status"] == "COMPLETED"
    assert "timeout" in chat_model.received_messages[1][-1].content


async def test_output_that_breaks_the_schema_is_treated_as_a_permanent_error(harness_factory):
    chat_model = status_then_answer()
    harness = harness_factory(chat_model, injector=FailureInjector("invalid_output"))

    run = await harness.service.start_run("Check auth")

    assert run["status"] == "COMPLETED"
    assert "invalid_output" in chat_model.received_messages[1][-1].content
    assert "tool_retry" not in await event_types(harness, run["run_id"])
