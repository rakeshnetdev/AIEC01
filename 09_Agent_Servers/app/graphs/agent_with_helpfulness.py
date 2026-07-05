from __future__ import annotations

import os
from typing import Annotated, Sequence, TypedDict
from pydantic import BaseModel, Field

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import START, END, StateGraph
from langgraph.graph.message import add_messages

from app.graphs.simple_agent import graph as inner_agent
from app.models import get_chat_model

# ---------------------------------------------------------
# State Definition
# ---------------------------------------------------------

class AgentWithHelpfulnessState(TypedDict):
    """
    State representing the context of our helpfulness loop.
    
    - messages: Accumulated conversation history.
    - attempts: The counter for agent attempts.
    - is_helpful: Evaluation verdict from the judge model.
    - feedback: Constructive feedback from the judge if unhelpful.
    """
    messages: Annotated[Sequence[BaseMessage], add_messages]
    attempts: int
    is_helpful: bool
    feedback: str | None


# ---------------------------------------------------------
# Pydantic Schemas for Structured Output
# ---------------------------------------------------------

class HelpfulnessAssessment(BaseModel):
    """
    Pydantic schema representing the output structure of the judge LLM evaluation.
    """
    is_helpful: bool = Field(
        description="True if the response is helpful, accurate, directly answers the user's query, and satisfies all constraints. False otherwise."
    )
    reason: str = Field(
        description="Constructive feedback explaining why the response is helpful or why it is not, pointing out exactly what needs to be improved."
    )


# Safe loop limit: maximum number of attempts the agent can make
MAX_ATTEMPTS = 3


# ---------------------------------------------------------
# Graph Nodes
# ---------------------------------------------------------

def agent_node(state: AgentWithHelpfulnessState) -> dict:
    """
    Agent node: Invokes the inner simple_agent graph using the current conversation history.
    It passes the history (which contains any previous feedback) to the inner agent.
    To prevent duplicating messages in the outer state reducer (add_messages), 
    we only return the newly generated messages.
    """
    input_messages = state["messages"]
    
    # Invoke the pre-configured simple_agent graph
    result = inner_agent.invoke({"messages": input_messages})
    
    # Slice to return only the new messages generated in this step
    new_messages = result["messages"][len(input_messages):]
    
    return {"messages": new_messages}


def judge_node(state: AgentWithHelpfulnessState) -> dict:
    """
    Judge node: Evaluates the helpfulness of the last agent response using a separate LLM call.
    If the response is not helpful, it adds system feedback for the next iteration.
    """
    messages = state["messages"]
    attempts = state.get("attempts", 0) + 1
    
    # Get the chat model for quality control (temperature=0 for deterministic evaluation)
    judge_llm = get_chat_model(temperature=0)
    structured_judge = judge_llm.with_structured_output(HelpfulnessAssessment)
    
    # Instruction prompt for the judge model
    system_prompt = (
        "You are an expert quality control judge for a cat health assistant.\n"
        "Your task is to evaluate the assistant's latest response to the user's query.\n\n"
        "Critically evaluate if the response is:\n"
        "1. Accurate, complete, and helpful.\n"
        "2. Directly and fully answers the user's query.\n"
        "3. Follows all instructions, rules, and negative constraints in the prompt (e.g., word count limits, negative constraints).\n\n"
        "If the response is helpful and meets all criteria, set is_helpful to True.\n"
        "If the response is unhelpful or fails constraints, set is_helpful to False and provide detailed, constructive feedback in the reason field."
    )
    
    # Prepare messages context for the judge model
    judge_messages = [SystemMessage(content=system_prompt)] + list(messages)
    assessment = structured_judge.invoke(judge_messages)
    
    # If the response was judged helpful, or we've hit our loop limit, stop the loop.
    if assessment.is_helpful or attempts >= MAX_ATTEMPTS:
        return {
            "attempts": attempts,
            "is_helpful": True,
            "feedback": None
        }
    else:
        # Create constructive feedback as a HumanMessage to prompt the agent
        feedback_message = HumanMessage(
            content=(
                f"[System Feedback] Your previous response was evaluated as unhelpful.\n"
                f"Reason: {assessment.reason}\n"
                f"Please try again, address this feedback fully, and generate a new response."
            )
        )
        return {
            "attempts": attempts,
            "is_helpful": False,
            "feedback": assessment.reason,
            "messages": [feedback_message]  # Append the feedback message to the chat history
        }


# ---------------------------------------------------------
# Routing Logic
# ---------------------------------------------------------

def route_after_judge(state: AgentWithHelpfulnessState) -> str:
    """
    Conditional routing edge to determine whether the graph should loop back or finish.
    """
    if state.get("is_helpful", True) or state.get("attempts", 0) >= MAX_ATTEMPTS:
        return "end"
    return "agent"


# ---------------------------------------------------------
# Graph Construction
# ---------------------------------------------------------

# Instantiate StateGraph with our state schema
workflow = StateGraph(AgentWithHelpfulnessState)

# Add nodes
workflow.add_node("agent", agent_node)
workflow.add_node("judge", judge_node)

# Set starting point
workflow.add_edge(START, "agent")

# Connect nodes
workflow.add_edge("agent", "judge")

# Add conditional edges
workflow.add_conditional_edges(
    "judge",
    route_after_judge,
    {
        "agent": "agent",
        "end": END
    }
)

# Compile workflow into a runnable graph
graph = workflow.compile()
