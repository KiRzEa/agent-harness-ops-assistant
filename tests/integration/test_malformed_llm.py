from langchain_core.messages import AIMessage

from tests.fakes import ScriptedChatModel, text_message, tool_call_message


def invalid_json_tool_call() -> AIMessage:
    return AIMessage(
        content="",
        invalid_tool_calls=[
            {
                "name": "get_service_status",
                "args": '{"service_name": ',
                "id": "call_bad",
                "error": "bad json",
                "type": "invalid_tool_call",
            }
        ],
    )


async def repair_events(harness, run_id):
    return [e for e in await harness.service.get_trace(run_id) if e["type"] == "repair"]


async def test_invalid_json_arguments_are_repaired(harness_factory):
    chat_model = ScriptedChatModel(responses=[invalid_json_tool_call(), text_message("Recovered.")])
    harness = harness_factory(chat_model)

    run = await harness.service.start_run("Check auth")

    assert run["status"] == "COMPLETED"
    assert len(await repair_events(harness, run["run_id"])) == 1
    assert "could not be used" in chat_model.received_messages[1][-1].content


async def test_unknown_tool_is_not_executed_and_is_repaired(harness_factory):
    chat_model = ScriptedChatModel(
        responses=[tool_call_message("delete_database", {}, "call_bad"), text_message("Sorry.")]
    )
    harness = harness_factory(chat_model)

    run = await harness.service.start_run("Do something")

    assert run["status"] == "COMPLETED"
    types = [e["type"] for e in await harness.service.get_trace(run["run_id"])]
    assert "tool_call" not in types and "validation_error" in types


async def test_arguments_that_fail_validation_are_repaired(harness_factory):
    chat_model = ScriptedChatModel(
        responses=[
            tool_call_message("get_service_status", {"name": "auth-service"}, "call_bad"),
            tool_call_message("get_service_status", {"service_name": "auth-service"}, "call_ok"),
            text_message("Healthy."),
        ]
    )
    harness = harness_factory(chat_model)

    run = await harness.service.start_run("Check auth")

    assert run["status"] == "COMPLETED"
    assert len(await repair_events(harness, run["run_id"])) == 1


async def test_empty_response_is_repaired(harness_factory):
    chat_model = ScriptedChatModel(responses=[AIMessage(content=""), text_message("Here you go.")])
    harness = harness_factory(chat_model)

    run = await harness.service.start_run("Say something")

    assert run["status"] == "COMPLETED"
    assert len(await repair_events(harness, run["run_id"])) == 1


async def test_run_fails_when_repairs_are_used_up(harness_factory):
    chat_model = ScriptedChatModel(responses=[AIMessage(content="")], repeat_last_response=True)
    harness = harness_factory(chat_model)

    run = await harness.service.start_run("Say something")

    assert run["status"] == "FAILED"
    assert run["error"]["code"] == "malformed_llm_response"
    assert len(await repair_events(harness, run["run_id"])) == harness.settings.max_repairs + 1
