"""Read-only lookup into the llm-wiki Obsidian vault (the durable JP-stock brain).

Why this exists: without it every screening run re-researches every ticker from
scratch via web search — the most expensive part of a run. The vault already
holds 170+ ticker entity pages (many with a full Kiyohara+DCF analysis), so an
agent that checks here first pays one local HTTP GET instead of several
searches + scrapes + a large LLM context.

Talks to the same Obsidian Local REST API that llm-wiki/scripts/obsidian_client.py
uses (that file stays the write path — this tool never writes). Requires
Obsidian running with the wiki/ vault open and the "Local REST API" plugin on;
when it isn't reachable the tool says so plainly and the agent falls back to web
research rather than inventing anything.
"""

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

# The llm-wiki repo keeps the API key in its own .env; read it from there so the
# key lives in exactly one place instead of being copied into this project.
WIKI_ENV = Path(
    os.environ.get(
        "JP_SCREEN_WIKI_ENV",
        r"C:\Users\shimo\OneDrive\ドキュメント\Private\HocTap\AI\llm-wiki\.env",
    )
)


def _load_wiki_env() -> None:
    if not WIKI_ENV.exists():
        return
    for line in WIKI_ENV.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


_load_wiki_env()


def _request(route: str) -> str:
    api_key = os.environ.get("OBSIDIAN_API_KEY", "")
    if not api_key:
        raise RuntimeError("OBSIDIAN_API_KEY chưa được set (xem llm-wiki/.env)")
    base = "{}://{}:{}".format(
        os.environ.get("OBSIDIAN_SCHEME", "http"),
        os.environ.get("OBSIDIAN_HOST", "127.0.0.1"),
        os.environ.get("OBSIDIAN_PORT", "27123"),
    )
    req = urllib.request.Request(
        base + route,
        headers={"Authorization": f"Bearer {api_key}", "Accept": "text/markdown"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode("utf-8")


def _is_thin_stub(body: str) -> bool:
    """A stub page carries identity only — bias/net_cash_ratio still blank because
    the full Kiyohara+DCF pipeline hasn't run on it yet (see the vault's
    templates/entity-stock.md). The agent must still web-research those."""
    lines = body.replace("\r\n", "\n").split("\n")
    if not lines or lines[0].strip() != "---":
        return True
    for line in lines[1:]:
        if line.strip() == "---":
            break
        key, _, value = line.partition(":")
        if key.strip() == "bias":
            return not value.strip()
    return True


def _digest(body: str) -> str:
    """Frontmatter + the Key Metrics table only.

    A fully-analysed entity page runs ~10KB of Japanese markdown; feeding twenty
    of those into an agent costs more than the web search this tool is supposed
    to replace. The frontmatter already carries every number the screening
    stages actually consume (per/pbr/roe/net_cash_ratio/bias/position_size), so
    that plus the metrics table is the useful part. `full=True` fetches the rest
    when an agent genuinely needs the narrative or the source list.
    """
    text = body.replace("\r\n", "\n")
    out = []
    lines = text.split("\n")
    if lines and lines[0].strip() == "---":
        end = next((i for i, l in enumerate(lines[1:], 1) if l.strip() == "---"), 0)
        out.extend(lines[: end + 1])
    for marker in ("### Key Metrics Summary", "## 【統合投資判断】"):
        idx = text.find(marker)
        if idx == -1:
            continue
        chunk = text[idx : idx + 900]
        out.append("")
        out.append(chunk.rsplit("\n", 1)[0])
    return "\n".join(out)


class WikiLookupInput(BaseModel):
    ticker: str = Field(..., description="Mã cổ phiếu JPX 4 ký tự, vd 6758, 146A")
    full: bool = Field(
        False,
        description=(
            "既定 false = frontmatter と主要指標のみの digest（安い）。"
            "分析の根拠や出典まで読む必要があるときだけ true にする（高い）。"
        ),
    )


class ObsidianWikiLookupTool(BaseTool):
    name: str = "obsidian_wiki_lookup"
    description: str = (
        "既存リサーチの再利用: llm-wiki Obsidian vault に、その銘柄の entity ページが"
        "既にあるかを調べ、あればページ全文（財務データ・Kiyohara+DCF分析・出典）を返す。"
        "Web検索より先に必ずこれを試すこと — ヒットすれば再調査は不要。"
        "ヒットしなかった場合のみ Web検索にフォールバックする。"
    )
    args_schema: Type[BaseModel] = WikiLookupInput

    def _run(self, ticker: str, full: bool = False) -> str:
        ticker = ticker.strip().upper()
        try:
            body = _request("/vault/" + urllib.parse.quote(f"entities/jp/{ticker}.md"))
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return (
                    f"{ticker}: vault にページなし（未リサーチ）。"
                    "Web検索で新規に調べること。"
                )
            return f"{ticker}: vault 取得エラー HTTP {exc.code} — Web検索にフォールバックせよ。"
        except Exception as exc:  # noqa: BLE001 - agent phải biết để fallback, không giấu lỗi
            return f"{ticker}: vault に接続できない ({exc}) — Web検索にフォールバックせよ。"

        if _is_thin_stub(body):
            return (
                f"{ticker}: vault にページあり（thin stub — 識別情報のみ、財務データなし。"
                "数値は Web検索で補うこと）"
            )
        if full:
            return (
                f"{ticker}: vault にページあり（分析済み・全文）— 下記をそのまま使い、再調査しないこと\n\n"
                + body
            )
        return (
            f"{ticker}: vault にページあり（分析済み・digest）— 下記の数値をそのまま使い、"
            "再調査しないこと。根拠/出典が要るときだけ full=true で再取得。\n\n"
            + _digest(body)
        )


class WikiListInput(BaseModel):
    pass


class ObsidianWikiIndexTool(BaseTool):
    name: str = "obsidian_wiki_index"
    description: str = (
        "llm-wiki vault に entity ページが存在する JPX 銘柄コードの一覧を返す。"
        "候補ユニバースを決めた直後に1回だけ呼び、どの銘柄が既知でどれが新規かを"
        "把握するのに使う（銘柄ごとに個別に呼ばないこと）。"
    )
    args_schema: Type[BaseModel] = WikiListInput

    def _run(self) -> str:
        # JP only: the vault splits stock entities per market
        # (entities/jp|vn|us/), and this screener is JP-scoped.
        try:
            raw = _request("/vault/entities/jp/")
        except Exception as exc:  # noqa: BLE001
            return f"vault に接続できない ({exc}) — 全銘柄を Web検索で調べること。"
        files = json.loads(raw).get("files", [])
        codes = sorted(f[:-3] for f in files if f.endswith(".md"))
        return f"vault 既知の {len(codes)} 銘柄: " + ", ".join(codes)
