"""Build the ReAct-style agent used by OSS Compass."""

from __future__ import annotations

from typing import Any

from app._compat import AgentExecutor, ChatOpenAI, create_react_agent
from app.agent.prompts import SYSTEM_PROMPT
from app.agent.tools import (
    contribution_strength_tool,
    gap_analysis_tool,
    next_contributions_tool,
    role_alignment_tool,
    trajectory_tool,
)


def build_agent() -> AgentExecutor:
    """Build an agent executor that calls the Coral tools in order."""
    llm = ChatOpenAI(
        model="anthropic/claude-3-haiku",
        openai_api_base="https://openrouter.ai/api/v1",
        openai_api_key="placeholder",
        temperature=0,
    )
    tools = [
        contribution_strength_tool,
        role_alignment_tool,
        gap_analysis_tool,
        trajectory_tool,
        next_contributions_tool,
    ]
    agent = create_react_agent(llm, tools, SYSTEM_PROMPT)
    return AgentExecutor.from_agent_and_tools(agent, tools, verbose=False)

