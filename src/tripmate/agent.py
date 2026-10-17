from dataclasses import dataclass, field
from typing import cast

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.tools import BaseTool
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from tripmate.llm import ScriptedFakeLLM
from tripmate.request import parse_request
from tripmate.telemetry import Telemetry
from tripmate.tools import GUARD_REJECTION, Fields, Guard, make_tools

MAX_STEPS = 8


@dataclass(frozen=True)
class RunResult:
    requested: Fields
    booking: Fields | None
    final_message: str
    trace_id: str
    rejected: list[Fields] = field(default_factory=list)

    @property
    def output(self) -> dict[str, object]:
        booking = {} if self.booking is None else {"booking": self.booking}
        return {**booking, "final_message": self.final_message}


def build_graph(
    llm: BaseChatModel, tools: list[BaseTool]
) -> CompiledStateGraph[MessagesState, None, MessagesState, MessagesState]:
    def agent(state: MessagesState) -> MessagesState:
        messages = state["messages"]
        if sum(isinstance(m, AIMessage) for m in messages) >= MAX_STEPS:
            return {"messages": [AIMessage(content=f"Stopped: step limit of {MAX_STEPS} reached.")]}
        return {"messages": [llm.invoke(messages)]}

    graph = StateGraph(MessagesState)
    graph.add_node("agent", agent)
    graph.add_node("tools", ToolNode(tools, handle_tool_errors=True))
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", tools_condition, ["tools", END])
    graph.add_edge("tools", "agent")
    return graph.compile()


def summarize(requested: Fields, messages: list[BaseMessage], trace_id: str) -> RunResult:
    args = {
        call["id"]: cast(Fields, call["args"])
        for m in messages
        if isinstance(m, AIMessage)
        for call in m.tool_calls
    }
    bookings = [m for m in messages if isinstance(m, ToolMessage) and m.name == "book_flight"]
    booked = [cast(Fields, m.artifact) for m in bookings if m.status == "success"]
    rejected = [args[m.tool_call_id] for m in bookings if GUARD_REJECTION in str(m.content)]
    return RunResult(
        requested=requested,
        booking=booked[-1] if booked else None,
        final_message=str(messages[-1].content),
        trace_id=trace_id,
        rejected=rejected,
    )


def run_agent(
    text: str,
    case: int,
    guard: Guard,
    telemetry: Telemetry,
    *,
    seed: int = 0,
    latency_scale: float = 1.0,
) -> RunResult:
    with telemetry.langfuse.start_as_current_observation(
        name="tripmate", as_type="agent", input={"message": text}
    ) as root:
        try:
            requested = parse_request(text)
        except ValueError as error:
            root.update(level="ERROR", status_message=str(error))
            raise
        root.update(input={"requested": requested, "message": text})
        llm = ScriptedFakeLLM(case=case, seed=seed, latency_scale=latency_scale)
        graph = build_graph(llm, make_tools(requested, guard))
        state = graph.invoke(
            {"messages": [HumanMessage(content=text)]}, config={"callbacks": [telemetry.handler]}
        )
        result = summarize(requested, state["messages"], root.trace_id)
        root.update(output=result.output)
    return result
