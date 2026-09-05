"""Builds crewAI Agent instances for the JP value-screen graph.

Role/goal/backstory come from config/agents.yaml (kept in sync by hand with
the original prompt-based agents in ../../.claude/agents/*.md — that
directory is the prior, Claude-Code-subagent implementation of this same
screening system; this package is the code-based graph-engine rewrite of it).
"""

import os
from pathlib import Path

import yaml
from crewai import Agent
from crewai_tools import ScrapeWebsiteTool

from jp_value_screen_graph.tools.duckduckgo_search_tool import DuckDuckGoSearchTool
from jp_value_screen_graph.tools.obsidian_wiki_tool import (
    ObsidianWikiIndexTool,
    ObsidianWikiLookupTool,
)

_CONFIG_PATH = Path(__file__).parent / "config" / "agents.yaml"
_AGENTS_CONFIG = yaml.safe_load(_CONFIG_PATH.read_text(encoding="utf-8"))

# LiteLLM-style model string. Default targets Claude via ANTHROPIC_API_KEY
# (already present in this environment) — override with JP_SCREEN_LLM to use
# a cheaper/faster model (e.g. anthropic/claude-haiku-4-5-20251001) for a
# quick smoke-test run.
DEFAULT_LLM = os.environ.get("JP_SCREEN_LLM", "anthropic/claude-sonnet-5")

MAX_ITER = int(os.environ.get("JP_SCREEN_MAX_ITER", "10"))


def _tools(*, wiki: bool = False):
    # Fresh instances per agent: crewai tools are cheap to construct and this
    # avoids any shared-state surprises between concurrently running agents.
    tools = [DuckDuckGoSearchTool(), ScrapeWebsiteTool()]
    if wiki:
        # Persistent memory layer: the llm-wiki Obsidian vault. Checking it first
        # is what keeps repeat runs cheap — see tools/obsidian_wiki_tool.py.
        tools = [ObsidianWikiIndexTool(), ObsidianWikiLookupTool()] + tools
    return tools


# Agents that research individual tickers benefit from the vault; the ones that
# only reason over data handed to them by earlier stages don't (giving them the
# tool would just invite extra calls).
WIKI_ENABLED = {
    "intelligent_data_agent",
    "eps_quality_analyst",
    "balance_sheet_quality_agent",
    "catalyst_re_rating_agent",
    "risk_liquidity_agent",
}

# crewAI's own memory=True is deliberately left OFF: it is embedding-backed
# (chromadb + an embedding provider, OpenAI by default) which this setup has no
# key for, and it would add per-run cost. The vault above plays that role
# instead — durable, free, and already human-readable.


def build_agent(key: str, *, llm: str | None = None) -> Agent:
    """Construct one of the 8 named specialist agents from agents.yaml."""
    cfg = _AGENTS_CONFIG[key]
    return Agent(
        role=cfg["role"],
        goal=cfg["goal"],
        backstory=cfg["backstory"],
        tools=_tools(wiki=key in WIKI_ENABLED),
        llm=llm or DEFAULT_LLM,
        max_iter=MAX_ITER,
        verbose=True,
    )


def build_universe_scout(*, llm: str | None = None) -> Agent:
    """Stage 0 agent: candidate-universe selection.

    Not one of the 8 named specialists (orchestrator.md has the orchestrator
    itself do this step via WebSearch, not a dedicated sub-agent) — kept out
    of agents.yaml for that reason, defined here instead.
    """
    return Agent(
        role="候補銘柄ユニバース選定",
        goal=(
            "日本株の割安株スクリーニングのために、業種横断的な候補ティッカー"
            "ユニバースを選定する。"
        ),
        backstory=(
            "ユーザーがセクター/銘柄リストを指定した場合はそれに厳密に従い、"
            "範囲を勝手に広げない。指定がなければ、業種横断的に候補ティッカーを"
            "複数の独立したソースから収集する(目安40〜60銘柄)。東証全銘柄"
            "(約3,900社)の網羅スクリーニングではなく『業種横断サンプル調査』"
            "であることを自覚し、最後にその旨を一言明記する。"
        ),
        tools=_tools(),
        llm=llm or DEFAULT_LLM,
        max_iter=MAX_ITER,
        verbose=True,
    )
