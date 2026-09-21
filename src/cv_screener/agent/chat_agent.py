"""Tool-calling chat agent over the candidate dataset.

Manual tool-call loop (rather than a higher-level AgentExecutor) so the
control flow is easy to read and explain: ask the model, if it wants a
tool call it, feed the result back, repeat until it answers in plain text.
"""

from __future__ import annotations

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI

from cv_screener.agent.tools import TOOLS, TOOLS_BY_NAME
from cv_screener.config import CHAT_MODEL, require_api_key

SYSTEM_PROMPT = """You are a recruiting assistant answering questions about a \
dataset of candidate resumes. You do NOT have the resumes memorized. You \
MUST use the provided tools (semantic_search_tool, filter_search_tool, \
get_candidate_profile_tool) to look things up before answering — never \
answer from assumption or memory.

Rules:
- Always search before answering. Call at least one tool for every question \
about candidates.
- Never invent candidates, skills, employers, or facts that didn't come \
from a tool result.
- Always name the specific candidates your answer is based on.
- If a search returns no relevant candidates, say plainly that no one in \
the dataset matches. Do not guess or soften this.
- Prefer filter_search_tool for concrete fields (a specific language, role, \
seniority, years of experience, location, skill, or company) and \
semantic_search_tool for open-ended or fuzzy questions (e.g. "best fit for \
a senior ML role"). You can call more than one tool, and more than once, \
before answering.
- Use get_candidate_profile_tool when asked to summarize or detail one \
named candidate.
- Keep the final answer concise and grounded only in tool results."""

MAX_TOOL_ROUNDS = 6


def build_llm() -> ChatOpenAI:
    require_api_key()
    return ChatOpenAI(model=CHAT_MODEL, temperature=0.2).bind_tools(TOOLS)


def initial_history() -> list[BaseMessage]:
    return [SystemMessage(content=SYSTEM_PROMPT)]


def run_turn(llm: ChatOpenAI, history: list[BaseMessage], user_input: str) -> tuple[str, list[BaseMessage]]:
    """Runs one user turn to completion (including any tool calls) and
    returns (answer_text, updated_history)."""
    messages: list[BaseMessage] = [*history, HumanMessage(content=user_input)]

    for _ in range(MAX_TOOL_ROUNDS):
        ai_msg: AIMessage = llm.invoke(messages)
        messages = [*messages, ai_msg]

        if not ai_msg.tool_calls:
            return ai_msg.content, messages

        for tool_call in ai_msg.tool_calls:
            tool_fn = TOOLS_BY_NAME.get(tool_call["name"])
            if tool_fn is None:
                result = f"Unknown tool: {tool_call['name']}"
            else:
                try:
                    result = tool_fn.invoke(tool_call["args"])
                except Exception as exc:  # keep the loop alive on bad tool args
                    result = f"Tool error: {exc}"
            messages = [
                *messages,
                ToolMessage(content=str(result), tool_call_id=tool_call["id"]),
            ]

    fallback = "I wasn't able to finish looking this up within the tool-call budget."
    return fallback, messages
