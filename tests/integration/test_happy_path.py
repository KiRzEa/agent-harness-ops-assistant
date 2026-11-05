from tests.fakes import ScriptedChatModel, many_tool_calls_message, text_message, tool_call_message


async def test_run_uses_two_tools_then_answers(harness_factory):
    chat_model = ScriptedChatModel(
        responses=[
            tool_call_message(
                "get_service_status", {"service_name": "payments-api"}, "call_status"
            ),
            tool_call_message(
                "search_knowledge_base", {"query": "payments degraded runbook"}, "call_kb"
            ),
            text_message("payments-api is degraded; follow the failover runbook."),
        ]
    )
    harness = harness_factory(chat_model)

    run = await harness.service.start_run("Is payments healthy and what should I do?")

    assert run["status"] == "COMPLETED"
    assert run["final_answer"].startswith("payments-api is degraded")
    assert run["step_count"] == 3
    trace = await harness.service.get_trace(run["run_id"])
    event_types = [event["type"] for event in trace]
    assert event_types.count("tool_call") == 2
    assert event_types.count("tool_result") == 2
    assert event_types[0] == "run_started" and event_types[-1] == "run_finished"
    assert [event["seq"] for event in trace] == list(range(1, len(trace) + 1))


async def test_tool_result_is_sent_back_to_the_model(harness_factory):
    chat_model = ScriptedChatModel(
        responses=[
            tool_call_message("get_service_status", {"service_name": "search-service"}),
            text_message("search-service is down."),
        ]
    )
    harness = harness_factory(chat_model)

    await harness.service.start_run("Check search")

    second_call_messages = chat_model.received_messages[1]
    assert "down" in second_call_messages[-1].content


async def test_parallel_read_calls_in_one_turn(harness_factory):
    chat_model = ScriptedChatModel(
        responses=[
            many_tool_calls_message(
                [
                    ("get_service_status", {"service_name": "auth-service"}, "call_a"),
                    ("get_service_status", {"service_name": "checkout-service"}, "call_b"),
                ]
            ),
            text_message("Both healthy."),
        ]
    )
    harness = harness_factory(chat_model)

    run = await harness.service.start_run("Check auth and checkout")

    assert run["status"] == "COMPLETED"
    trace = await harness.service.get_trace(run["run_id"])
    assert [event["type"] for event in trace].count("tool_result") == 2
