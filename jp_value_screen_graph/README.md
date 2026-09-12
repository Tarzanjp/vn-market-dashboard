# jp_value_screen_graph

コードベースのグラフエンジン(CrewAI Flow)による日本株過小評価株スクリーニング。
`../.claude/agents/`(Claude Codeのプロンプト型サブエージェント + orchestrator.md)
と同じ8専門Agent構成・同じステージ設計を、実行コードとして書き直したもの。
どちらも独立して動作する — 一方を変更したときはもう一方も追随させるか、
本README・`.claude/agents/README.md` にどちらが正本かを明記すること。

## 構成 — 実グラフ(依存関係)

```
Stage 0  build_universe                                  候補ユニバース選定
Stage 1  run_benchmark  ‖ run_data_collection             (並列)
Stage 2  run_screener                                     (Stage1の両方完了後)
Stage 3  run_eps_quality ‖ run_balance_sheet ‖ run_catalyst ‖ run_risk   (並列)
Stage 4  run_scoring                                      (Stage3全完了後)
Stage 5  save_report                                      (LLM呼び出しなし、output/に保存)
```

`flow.py` の並列ステージは `async def` + `agent.kickoff_async()` で実装されており、
CrewAIのFlowランタイムが同一トリガーのリスナーを `asyncio.gather` で実行するため、
実際に並行実行される(プロンプト先読みで「並列」と書くだけではない)。

## セットアップ

```bash
crewai install   # または: uv sync
```

`.env` に `ANTHROPIC_API_KEY` を設定(このマシンでは既に環境変数として設定済みなら不要)。
LLM既定は `anthropic/claude-sonnet-5`。`JP_SCREEN_LLM` 環境変数で上書き可能
(例: `anthropic/claude-haiku-4-5-20251001` で安く/速く試す)。

検索は無料の DuckDuckGo(`ddgs` パッケージ、APIキー不要)を使用 —
`tools/duckduckgo_search_tool.py`。品質・安定性はSerper/Tavily等の有料APIより劣るため、
レート制限などで問題が出た場合は差し替えを検討(`agents.py: _tools()`)。

## 実行

```bash
# セクター/銘柄を指定しない場合 — Stage0が横断的に40〜60銘柄を自分でWebSearch選定
uv run kickoff

# 銘柄を指定する場合(Stage0のWebSearchをスキップし、指定銘柄のみで進める)
uv run run_with_trigger '{"tickers": ["7203 トヨタ自動車", "8058 三菱商事"]}'

# セクターだけ指定する場合
uv run run_with_trigger '{"sectors": ["銀行", "商社"]}'

# グラフ構造を画像で確認
uv run plot
```

出力: `output/jp-value-screen-<timestamp>.md`(実行したAgent一覧・最終ランキング・
各ステージの詳細・手法上の限界の開示を含む)。

## APIキー無しで最新データを取る

`ANTHROPIC_API_KEY` が要るのは **LLM に判断させる部分だけ**。「今いくらか」は
判断ではないので、キー無しの公開エンドポイントで取る。

```bash
# JP / VN / US、キー不要・LLM不要。Claude Code からも直接叩ける
uv run python -m jp_value_screen_graph.tools.market_data 6758 7203 --market jp
uv run python -m jp_value_screen_graph.tools.market_data VNM HPG --market vn
uv run python -m jp_value_screen_graph.tools.market_data AAPL --market us --json
```

`tools/market_data.py` は stdlib のみ(crewai が無くても動く)。Yahoo Finance の
公開 chart エンドポイントを叩き、株価・前日比・通貨・取引所・**取得時刻**を返す。
取れなかった銘柄は `FAILED` として返り、値を推測しない。
User-Agent は必須(無いと `Edit: Too Many Requests` が返る)。

engine 内では `market_quote` tool として、値段を要する3つのAgent
(intelligent_data / quantitative_screener / risk_liquidity)に渡している —
モデルに検索させて値段を探させるより速く、正確で、無料。

**判断まで含めてキー無しで回したい場合**は、この engine ではなく
`.claude/skills/jp-value-screen` の **経路A(会話内 subagent orchestrator)**を使う。
そちらは Claude Code のサブスクリプションで動くので `ANTHROPIC_API_KEY` を消費しない。
engine(経路B)は API 従量課金で、残高切れだと HTTP 400 で即座に止まる。

## メモリ連携(Obsidian llm-wiki)

再調査がこのワークフロー最大のコスト。それを消すために vault を引く。

- **読み**: `obsidian_wiki_index`(既知コード一覧、1回だけ) と
  `obsidian_wiki_lookup`(銘柄ページ)を、銘柄を調べる5つのAgentに付与している
  (`agents.py: WIKI_ENABLED`)。lookup の既定は **digest**(frontmatter + 主要指標)
  で全文の約1/6のトークン量 — 根拠や出典が要るときだけ `full=true`。
  read-only。書き込みは llm-wiki 側の `scripts/obsidian_client.py` が唯一の経路。
- **書き**: **品質ゲートを通った run だけ** `llm-wiki/sources/<date>-jp-screen-graph-run.md`
  へステージする(不変・上書きしない。既存なら `-2`, `-3` と採番)。
  ゲート(`flow.py: _quality_gate()`)は既定で拒否し、run が条件を満たしたときだけ
  通す — 全ステージに実体がある / 最終ランキングに銘柄コードがある /
  取得不可・評価不能だらけでない / Agent が9つとも起動した。落ちた場合は理由を
  列挙して vault を一切触らず、ローカル出力だけ残す。
  半端な結果を入れると、後で「事実」として読み返されて間違いが定着するため。
  vault への昇格は llm-wiki 側で `/wiki-ingest` を実行して curate してから
  — bot が `wiki/` に直接書くことはしない(fact-only/出典明記の品質基準を守るため)。
- **crewAI 内蔵 memory は意図的に無効**: embedding provider(既定 OpenAI)が必要で
  追加コストになるため。その役割は vault が担う。
- 上書き用の環境変数: `JP_SCREEN_WIKI_ENV`(API キーを読む .env のパス)、
  `JP_SCREEN_WIKI_SOURCES`(ステージ先ディレクトリ)。
- Obsidian が起動していない場合、tool は「接続できない」と返して Web検索に
  フォールバックし、ステージはスキップされる(実行自体は落ちない)。

## 既知の制約(プロンプト版から継承)

- WebSearch/スクレイピングのみで動作するため、EDINET/JPXの一次データへの網羅アクセスはできない。
  候補銘柄は二次集計サイト(株探・Yahoo!ファイナンス等)からのサンプリングであり、
  「東証全銘柄の系統的フルスクリーニング」ではない。
- 投資助言(「買い」「目標株価」等)は一切出力しない設計(全Agentのbackstoryに明記)。
- DuckDuckGo検索は無料だがレート制限が発生しうる。頻繁に実行する場合はSerper/Tavily等の
  有料APIキー方式への切り替えを検討。

## ファイル

- `src/jp_value_screen_graph/config/agents.yaml` — 8専門Agentのrole/goal/backstory
- `src/jp_value_screen_graph/agents.py` — Agent構築(LLM・ツール設定)
- `src/jp_value_screen_graph/tools/duckduckgo_search_tool.py` — 無料検索ツール
- `src/jp_value_screen_graph/flow.py` — グラフ本体(ステージ・並列化・状態)
- `src/jp_value_screen_graph/main.py` — CLIエントリポイント
