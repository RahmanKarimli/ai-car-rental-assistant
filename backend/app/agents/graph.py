import logging
from langgraph.graph import StateGraph,START,END
from app.agents.state import RentalAgentState
from app.agents.nodes import Nodes
from app.core.errors import DomainError
from pydantic import ValidationError
NAMES=["load_context","detect_language","interpret_request","risk_gate","route_intent","clarify","search_inventory","rank_options","retrieve_policy","answer_policy","recommend_extras","prepare_draft","validate_confirmation","commit_action","escalate","compose_response","persist_response","await_confirmation","recover"]

def build_graph(saver):
    graph=StateGraph(RentalAgentState);nodes=Nodes()
    for name in NAMES:
        method=getattr(nodes,name)
        def bind(method,name):
            async def run(state):
                try:return await method(state)
                except DomainError as error:return {"error_code":error.code,"error_node":name,"text":""}
                except (ValueError,ValidationError) as error:
                    fields=[".".join(str(part) for part in item["loc"]) for item in error.errors()] if isinstance(error,ValidationError) else []
                    logging.getLogger("rental").warning("graph_validation_failed:%s fields=%s",name,fields)
                    return {"error_code":"INVALID_INPUT","error_node":name,"text":""}
                except Exception:
                    logging.getLogger("rental").exception("graph_node_failed:%s",name)
                    if name=="persist_response":raise
                    return {"error_code":"STEP_UNAVAILABLE","error_node":name,"text":""}
            return run
        graph.add_node(name,bind(method,name))
    graph.add_edge(START,"load_context")
    def guarded(target):return lambda s:"escalate" if s.get("error_code")=="OUT_OF_STATE_DROPOFF" else "recover" if s.get("error_code") else target
    graph.add_conditional_edges("load_context",lambda s:"compose_response" if s.get("intent")=="HANDOFF" else "risk_gate" if s["event"]["kind"]=="CONFIRM_DRAFT" else "detect_language")
    graph.add_conditional_edges("detect_language",guarded("interpret_request"))
    graph.add_conditional_edges("interpret_request",guarded("risk_gate"))
    graph.add_conditional_edges("risk_gate",lambda s:"recover" if s.get("error_code") else "escalate" if s.get("intent")=="ESCALATE" else "validate_confirmation" if s["event"]["kind"]=="CONFIRM_DRAFT" else "route_intent")
    def route(s):
        intent=s["intent"]
        if intent=="POLICY_QA":return "retrieve_policy"
        if intent=="SEARCH":return "search_inventory"
        if intent=="PREPARE_DRAFT":return "prepare_draft"
        return "clarify"
    graph.add_conditional_edges("route_intent",route)
    graph.add_conditional_edges("search_inventory",guarded("rank_options"))
    graph.add_edge("rank_options","recommend_extras")
    graph.add_conditional_edges("recommend_extras",guarded("compose_response"))
    graph.add_conditional_edges("retrieve_policy",guarded("answer_policy"))
    graph.add_conditional_edges("answer_policy",guarded("compose_response"))
    graph.add_conditional_edges("prepare_draft",guarded("compose_response"))
    graph.add_conditional_edges("validate_confirmation",guarded("commit_action"))
    graph.add_conditional_edges("commit_action",guarded("compose_response"))
    graph.add_edge("clarify","compose_response");graph.add_conditional_edges("escalate",guarded("compose_response"))
    graph.add_edge("recover","compose_response")
    graph.add_conditional_edges("compose_response",lambda s:"recover" if s.get("error_code") and not s.get("text") else "persist_response")
    graph.add_conditional_edges("persist_response",lambda s:"await_confirmation" if s["phase"]=="AWAITING_CONFIRMATION" else END)
    graph.add_edge("await_confirmation",END)
    return graph.compile(checkpointer=saver)
graph=None
