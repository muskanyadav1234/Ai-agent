import json
from typing import TypedDict, Optional

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

# ------------------ LOAD KB ------------------
with open("knowledge_base.json", "r") as f:
    KB = json.load(f)

# ------------------ TOOL ------------------
def mock_lead_capture(name, email, platform):
    print(f"\n✅ Lead captured successfully: {name}, {email}, {platform}\n")

# ------------------ STATE ------------------
class AgentState(TypedDict, total=False):
    message: str
    intent: str
    response: str
    step: Optional[str]
    name: Optional[str]
    email: Optional[str]
    platform: Optional[str]

# ------------------ INTENT NODE ------------------
def intent_node(state):
    msg = state["message"].lower()

    # 🔥 If already in lead flow
    if state.get("step"):
        state["intent"] = "high_intent"
        return state

    # 🔥 GREETING
    if any(x in msg for x in ["hi", "hello", "hey"]):
        state["intent"] = "greeting"
        state["response"] = "Hey 👋 I’m AutoStream Assistant. Ask me about pricing!"
        return state

    # 🔥 FUZZY PRICING MATCH (FIX FOR TYPOS)
    if any(word in msg for word in ["price", "pricing", "plan", "cost", "pric", "rate"]):
        state["intent"] = "pricing"
        return state

    # 🔥 HIGH INTENT
    if any(word in msg for word in ["buy", "pro", "try", "subscribe", "i want", "sign up", "purchase"]):
        state["intent"] = "high_intent"
        return state

    state["intent"] = "general"
    return state
# ------------------ RAG NODE ------------------
def rag_node(state):
    msg = state["message"].lower()

    if "basic" in msg:
        state["response"] = KB["pricing"]["basic"]

    elif "pro" in msg:
        state["response"] = KB["pricing"]["pro"]

    elif "refund" in msg:
        state["response"] = KB["policies"]["refund"]

    elif "support" in msg:
        state["response"] = KB["policies"]["support"]

    else:
        state["response"] = KB["pricing"]["basic"]

    return state

# ------------------ LEAD NODE ------------------
def lead_node(state):

    step = state.get("step")

    if step is None:
        state["step"] = "name"
        state["response"] = "Great 🚀 Please tell me your Name."
        return state

    if step == "name":
        state["name"] = state["message"]
        state["step"] = "email"
        state["response"] = "Nice 👍 Now your Email?"
        return state

    if step == "email":
        state["email"] = state["message"]
        state["step"] = "platform"
        state["response"] = "Which platform? (YouTube / Instagram)"
        return state

    if step == "platform":
        state["platform"] = state["message"]

        mock_lead_capture(
            state.get("name"),
            state.get("email"),
            state.get("platform")
        )

        state["response"] = "🎉 Lead captured successfully!"
        state["step"] = None

        return state

    return state

# ------------------ ROUTER (ONLY ONE) ------------------
def router(state):

    print("ROUTING:", state["intent"])

    if state.get("step"):
        return "lead"

    if state["intent"] == "greeting":
        return END

    if state["intent"] == "pricing":
        return "rag"

    if state["intent"] == "high_intent":
        return "lead"

    return "rag"

# ------------------ BUILD GRAPH ------------------
workflow = StateGraph(AgentState)

workflow.add_node("intent", intent_node)
workflow.add_node("rag", rag_node)
workflow.add_node("lead", lead_node)

workflow.set_entry_point("intent")

workflow.add_conditional_edges(
    "intent",
    router,
    {
        "rag": "rag",
        "lead": "lead",
        END: END
    }
)

workflow.add_edge("rag", END)
workflow.add_edge("lead", END)

memory = MemorySaver()

app = workflow.compile(checkpointer=memory)

# ------------------ CHAT LOOP ------------------
thread = {"configurable": {"thread_id": "user1"}}

while True:
    user_input = input("You: ")

    result = app.invoke(
        {"message": user_input},
        config=thread
    )

    print("Bot:", result.get("response"))