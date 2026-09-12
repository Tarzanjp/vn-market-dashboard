"""Free, no-API-key web search tool backed by DuckDuckGo (via the `ddgs` package).

Replaces the paid SerperDevTool/TavilySearchTool that crewai_tools ships by
default. Quality/stability is lower than a paid search API and DuckDuckGo can
rate-limit bursts of queries — if that becomes a problem in practice, swap
this tool for SerperDevTool/TavilySearchTool (both need an API key in .env).
"""

from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class DuckDuckGoSearchInput(BaseModel):
    query: str = Field(..., description="検索クエリ(日本語・英語どちらも可)")
    max_results: int = Field(5, description="取得する検索結果の件数(既定5件)")


class DuckDuckGoSearchTool(BaseTool):
    name: str = "duckduckgo_search"
    description: str = (
        "DuckDuckGoでWeb検索し、タイトル・URL・要約スニペットのリストを返す。"
        "APIキー不要。株探・Yahoo!ファイナンス・EDINET・各社IRなどの情報を探すのに使う。"
    )
    args_schema: Type[BaseModel] = DuckDuckGoSearchInput

    def _run(self, query: str, max_results: int = 5) -> str:
        from ddgs import DDGS

        try:
            results = list(DDGS().text(query, max_results=max_results, region="jp-jp"))
        except Exception as exc:  # noqa: BLE001 - surface the failure to the agent, don't hide it
            return f"検索エラー: {exc}"

        if not results:
            return "検索結果なし。"

        lines = []
        for i, r in enumerate(results, start=1):
            title = r.get("title", "")
            href = r.get("href", "")
            body = r.get("body", "")
            lines.append(f"{i}. {title}\n   URL: {href}\n   {body}")
        return "\n".join(lines)
