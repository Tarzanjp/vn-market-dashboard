"""JP value-screen graph engine.

Code-based rewrite of .claude/agents/orchestrator.md's staged multi-agent
design as an actual dependency graph (crewAI Flow), instead of a single LLM
role-playing as an "orchestrator" that calls Claude Code subagents:

    Stage 0  build_universe                     (candidate ticker universe)
    Stage 1  run_benchmark  || run_data_collection      (parallel)
    Stage 2  run_screener                         (needs both Stage 1 results)
    Stage 3  run_eps_quality || run_balance_sheet || run_catalyst || run_risk (parallel)
    Stage 4  run_scoring                          (needs all four Stage 3 results)
    Stage 5  save_report                          (plain Python, no LLM call)

Parallel branches are genuinely concurrent: each listener method is async and
calls Agent.kickoff_async(), and crewAI's Flow runtime schedules same-trigger
listeners with asyncio.gather (see crewai/flow/runtime/__init__.py).

Known limitation carried over from the prompt-based version (see
.claude/agents/README.md): only WebSearch/scrape access, no EDINET/JPX bulk
data — this is a cross-sector *sample* survey, not a full TSE screen. No
investment advice ("buy", target prices, etc.) is produced anywhere in this
pipeline.
"""

import os
from datetime import datetime
from pathlib import Path

from crewai.flow.flow import Flow, and_, listen, start
from pydantic import BaseModel, Field

from jp_value_screen_graph.agents import build_agent, build_universe_scout

OUTPUT_DIR = Path("output")

# Closing the memory loop: a run's findings are dropped into llm-wiki's sources/
# inbox (raw + immutable by that repo's own convention) so `/wiki-ingest` can
# promote them into the curated vault later. Writing straight into wiki/ would
# bypass the curation rules that make the vault trustworthy, so this never does.
WIKI_SOURCES_DIR = Path(
    os.environ.get(
        "JP_SCREEN_WIKI_SOURCES",
        r"C:\Users\shimo\OneDrive\ドキュメント\Private\HocTap\AI\llm-wiki\sources",
    )
)


class ScreeningState(BaseModel):
    # --- inputs (settable via kickoff(inputs={...}) or trigger payload) ---
    sectors: list[str] = Field(default_factory=list)
    tickers: list[str] = Field(default_factory=list)
    shortlist_size: int = 20

    # --- stage outputs ---
    universe_notes: str = ""
    benchmark_report: str = ""
    data_report: str = ""
    screener_shortlist: str = ""
    eps_report: str = ""
    balance_sheet_report: str = ""
    catalyst_report: str = ""
    risk_report: str = ""
    final_ranking: str = ""

    # --- run bookkeeping (ground truth for the "実行モード" disclosure —
    # tracked in code, not self-reported by an LLM) ---
    agent_call_log: list[str] = Field(default_factory=list)
    report_path: str = ""
    wiki_source_path: str = ""


class JPValueScreenFlow(Flow[ScreeningState]):

    # ---------------- Stage 0 ----------------
    @start()
    async def build_universe(self, crewai_trigger_payload: dict | None = None):
        if crewai_trigger_payload:
            self.state.sectors = crewai_trigger_payload.get("sectors", self.state.sectors)
            self.state.tickers = crewai_trigger_payload.get("tickers", self.state.tickers)

        if self.state.tickers:
            self.state.universe_notes = (
                "ユーザー指定の候補銘柄(WebSearchによる追加選定は行わない): "
                + ", ".join(self.state.tickers)
            )
            print(f"[Stage0] user-specified universe: {self.state.tickers}")
            return

        scout = build_universe_scout()
        sector_hint = (
            f"対象セクター指定: {', '.join(self.state.sectors)}"
            if self.state.sectors
            else "セクター指定なし — 業種横断的に選定してよい"
        )
        prompt = (
            f"{sector_hint}\n\n"
            "日本株の割安株スクリーニング候補として、業種横断的な候補ティッカー"
            "ユニバースを選定せよ(指定がなければ目安40〜60銘柄、複数の独立した"
            "ソースから)。出力は「銘柄コード・銘柄名・業種」の一覧のみでよい。"
        )
        result = await scout.kickoff_async(prompt)
        self.state.universe_notes = result.raw
        self.state.agent_call_log.append("Universe Scout x1")
        print("[Stage0] universe built")

    # ---------------- Stage 1 (parallel) ----------------
    @listen(build_universe)
    async def run_benchmark(self):
        agent = build_agent("benchmark_agent")
        prompt = (
            f"候補ユニバース:\n{self.state.universe_notes}\n\n"
            "上記銘柄が属する業種すべてについて、業種別PER・PBR中央値と"
            "正常レンジをまとめて1回で調査せよ。"
        )
        result = await agent.kickoff_async(prompt)
        self.state.benchmark_report = result.raw
        self.state.agent_call_log.append("Benchmark Agent x1")
        print("[Stage1] benchmark done")

    @listen(build_universe)
    async def run_data_collection(self):
        agent = build_agent("intelligent_data_agent")
        prompt = (
            f"候補ユニバース:\n{self.state.universe_notes}\n\n"
            "まず obsidian_wiki_index を1回呼び、既にリサーチ済みの銘柄を把握せよ。"
            "既知の銘柄は obsidian_wiki_lookup の内容を再利用し、Web検索を繰り返さない"
            "(これがコスト削減の要)。vault に無い銘柄だけ Web検索で調べる。\n"
            "上記の全銘柄について、必須項目のデータを収集し、データ品質スコアを"
            "付けてまとめて1回で報告せよ(銘柄ごとに個別に依頼されたわけではない、"
            "全銘柄分を一括で出力すること)。出典が vault か Web かを各銘柄に明記せよ。"
        )
        result = await agent.kickoff_async(prompt)
        self.state.data_report = result.raw
        self.state.agent_call_log.append("Intelligent Data Agent x1")
        print("[Stage1] data collection done")

    # ---------------- Stage 2 ----------------
    @listen(and_(run_benchmark, run_data_collection))
    async def run_screener(self):
        agent = build_agent("quantitative_screener")
        prompt = (
            f"### 業種ベンチマーク\n{self.state.benchmark_report}\n\n"
            f"### 個別銘柄データ\n{self.state.data_report}\n\n"
            f"上記データを使い、一次候補ショートリスト(目安{self.state.shortlist_size}"
            "銘柄前後)を厳格に抽出せよ。"
        )
        result = await agent.kickoff_async(prompt)
        self.state.screener_shortlist = result.raw
        self.state.agent_call_log.append("Quantitative Screener x1")
        print("[Stage2] screener done")

    # ---------------- Stage 3 (parallel) ----------------
    @listen(run_screener)
    async def run_eps_quality(self):
        agent = build_agent("eps_quality_analyst")
        result = await agent.kickoff_async(self._stage3_prompt())
        self.state.eps_report = result.raw
        self.state.agent_call_log.append("EPS Quality Analyst x1")
        print("[Stage3] eps quality done")

    @listen(run_screener)
    async def run_balance_sheet(self):
        agent = build_agent("balance_sheet_quality_agent")
        result = await agent.kickoff_async(self._stage3_prompt())
        self.state.balance_sheet_report = result.raw
        self.state.agent_call_log.append("Balance Sheet Quality Agent x1")
        print("[Stage3] balance sheet done")

    @listen(run_screener)
    async def run_catalyst(self):
        agent = build_agent("catalyst_re_rating_agent")
        result = await agent.kickoff_async(self._stage3_prompt())
        self.state.catalyst_report = result.raw
        self.state.agent_call_log.append("Catalyst & Re-rating Agent x1")
        print("[Stage3] catalyst done")

    @listen(run_screener)
    async def run_risk(self):
        agent = build_agent("risk_liquidity_agent")
        result = await agent.kickoff_async(self._stage3_prompt())
        self.state.risk_report = result.raw
        self.state.agent_call_log.append("Risk & Liquidity Agent x1")
        print("[Stage3] risk done")

    def _stage3_prompt(self) -> str:
        return (
            f"### 一次候補ショートリスト\n{self.state.screener_shortlist}\n\n"
            f"### 個別銘柄データ(参考)\n{self.state.data_report}\n\n"
            "上記ショートリストの全銘柄について、あなたの専門分野の評価を"
            "まとめて1回で行え。"
        )

    # ---------------- Stage 4 ----------------
    @listen(and_(run_eps_quality, run_balance_sheet, run_catalyst, run_risk))
    async def run_scoring(self):
        agent = build_agent("dynamic_scoring_agent")
        prompt = (
            f"### 一次候補ショートリスト\n{self.state.screener_shortlist}\n\n"
            f"### EPS質評価\n{self.state.eps_report}\n\n"
            f"### 財務質評価\n{self.state.balance_sheet_report}\n\n"
            f"### 触媒評価\n{self.state.catalyst_report}\n\n"
            f"### リスク評価\n{self.state.risk_report}\n\n"
            "上記全評価を統合し、動的スコアリングによる優先順位付き最終リストを"
            "作成せよ。除外/要注意とした銘柄がある場合はその理由も明記せよ。"
        )
        result = await agent.kickoff_async(prompt)
        self.state.final_ranking = result.raw
        self.state.agent_call_log.append("Dynamic Scoring Agent x1")
        print("[Stage4] scoring done")

    # ---------------- Stage 5 — assemble & save (no LLM call) ----------------
    @listen(run_scoring)
    def save_report(self):
        OUTPUT_DIR.mkdir(exist_ok=True)
        ts = datetime.now().isoformat(timespec="seconds")
        report = f"""# 日本株過小評価株スクリーニング レポート

生成日時: {ts}

## 実行モード(実際に起動したAgent)
{chr(10).join(f"- {c}" for c in self.state.agent_call_log)}

## 最終候補リスト(Dynamic Scoring Agent)
{self.state.final_ranking}

## 手法上の限界(必読)
- WebSearch/スクレイピングのみに依拠しており、EDINET/JPXの一次データへの
  網羅アクセスはできない。候補銘柄は二次集計サイトからのサンプリングであり、
  東証全銘柄の系統的フルスクリーニングではない。
- 本レポートはデータと評価根拠の提示のみを目的とし、投資助言
  (「買い」「目標株価」等)ではない。

---
## 付録:各ステージの詳細出力

### Stage 0 — 候補ユニバース
{self.state.universe_notes}

### Stage 1 — 業種ベンチマーク
{self.state.benchmark_report}

### Stage 1 — 個別銘柄データ
{self.state.data_report}

### Stage 2 — 一次スクリーニング
{self.state.screener_shortlist}

### Stage 3 — EPS質評価
{self.state.eps_report}

### Stage 3 — 財務質評価
{self.state.balance_sheet_report}

### Stage 3 — 触媒評価
{self.state.catalyst_report}

### Stage 3 — リスク評価
{self.state.risk_report}
"""
        path = OUTPUT_DIR / f"jp-value-screen-{datetime.now():%Y%m%d-%H%M%S}.md"
        path.write_text(report, encoding="utf-8")
        self.state.report_path = str(path)
        print(f"[Stage5] report saved to {path}")
        self._stage_into_wiki_sources(report)

    def _stage_into_wiki_sources(self, report: str) -> None:
        """Drop the run into llm-wiki/sources/ so `/wiki-ingest` can promote it.

        Best-effort: if that repo isn't on this machine, the run still succeeds —
        the local report is the primary output, this is the memory loop's inbox.
        """
        if not WIKI_SOURCES_DIR.is_dir():
            print(f"[Stage5] wiki sources dir not found ({WIKI_SOURCES_DIR}) — skipped staging")
            return
        stem = f"{datetime.now():%Y-%m-%d}-jp-screen-graph-run"
        dest = WIKI_SOURCES_DIR / f"{stem}.md"
        n = 2
        while dest.exists():  # sources/ is immutable by convention — never overwrite
            dest = WIKI_SOURCES_DIR / f"{stem}-{n}.md"
            n += 1
        front = (
            "---\n"
            f"title: JP value screen — CrewAI graph engine run\n"
            f"fetched: {datetime.now():%Y-%m-%d}\n"
            "type: agent-run\n"
            "tool: jp_value_screen_graph (CrewAI Flow)\n"
            "---\n\n"
            "自動生成（CrewAI graph engine）。vault へ取り込むには `/wiki-ingest` を実行し、"
            "fact-only / 出典明記のルールに沿って curate すること — この生ファイルは"
            "そのままでは wiki/ の品質基準を満たさない。\n\n"
        )
        dest.write_text(front + report, encoding="utf-8")
        self.state.wiki_source_path = str(dest)
        print(f"[Stage5] staged for wiki ingest: {dest}")


def kickoff(sectors: list[str] | None = None, tickers: list[str] | None = None, shortlist_size: int = 20):
    flow = JPValueScreenFlow()
    inputs = {"shortlist_size": shortlist_size}
    if sectors:
        inputs["sectors"] = sectors
    if tickers:
        inputs["tickers"] = tickers
    flow.kickoff(inputs=inputs)
    return flow.state


def plot():
    JPValueScreenFlow().plot("jp_value_screen_graph")
