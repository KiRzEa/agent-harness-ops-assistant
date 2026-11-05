from langgraph.graph import END, START, StateGraph

from src.graph.dependencies import GraphDependencies
from src.graph.nodes import GraphNodes
from src.graph.routing import (
    route_after_inspect,
    route_after_llm,
    route_after_read_tools,
    route_after_repair,
)
from src.graph.state import RunState


def build_graph(dependencies: GraphDependencies, checkpointer):
    nodes = GraphNodes(dependencies)
    graph = StateGraph(RunState)
    graph.add_node("call_llm", nodes.call_llm)
    graph.add_node("inspect_response", nodes.inspect_response)
    graph.add_node("repair", nodes.repair)
    graph.add_node("run_read_tools", nodes.run_read_tools)
    graph.add_node("request_approval", nodes.request_approval)

    graph.add_edge(START, "call_llm")
    graph.add_conditional_edges("call_llm", route_after_llm, ["inspect_response", END])
    graph.add_conditional_edges(
        "inspect_response",
        route_after_inspect,
        ["repair", "run_read_tools", "request_approval", END],
    )
    graph.add_conditional_edges("repair", route_after_repair, ["call_llm", END])
    graph.add_conditional_edges(
        "run_read_tools", route_after_read_tools, ["request_approval", "call_llm"]
    )
    graph.add_edge("request_approval", "call_llm")
    return graph.compile(checkpointer=checkpointer)
