---
name: jp-value-screen
description: 日本株の業種相対割安株を発掘・評価する唯一の入口。2つの実行系(会話内のsubagent orchestrator / CrewAI graph engine)のどちらを使うかもここで決める。「割安株を発掘して」「JP株スクリーニングして」「orchestrator」等で発動。VN Market Dashboard本体とは無関係の独立したリサーチツール。
---

# JP Value Screen — 日本株過小評価株スクリーニング

同じ8専門Agent構成(Benchmark / Intelligent Data / Quantitative Screener / EPS
Quality / Balance Sheet Quality / Catalyst & Re-rating / Risk & Liquidity /
Dynamic Scoring)に、実行系が2つある。**どちらを使うかを先に決める** — 両方
動かさない。

| | A: subagent orchestrator | B: CrewAI graph engine |
|---|---|---|
| 実体 | `.claude/agents/*.md` | `jp_value_screen_graph/` |
| 実行 | この会話の中(Agent tool) | 別プロセス(`uv run`) |
| 課金 | このセッションのトークン | `ANTHROPIC_API_KEY` 従量 |
| 並列 | Agent tool 任せ | asyncio で実測並列 |
| vault連携 | 手動(agent-memory skill) | tool として組込み済み |
| 向く場面 | 対話しながら調整したい / 少数銘柄 | 決まった手順を安く回す / 反復実行 |

**`ANTHROPIC_API_KEY` の残高が無いときは A を使う** — A はこのセッション
(サブスク)で動くので API キーを消費しない。B は従量課金で、残高切れなら
HTTP 400 で即死する。

株価・前日比だけが欲しい場合は、どちらの経路も使わずキー無しで取れる:

```bash
cd jp_value_screen_graph && uv run python -m jp_value_screen_graph.tools.market_data \
  6758 7203 --market jp          # --market jp|vn|us、LLM を一切使わない
```

判断に迷う要素(コスト負担先・銘柄数)があれば AskUserQuestion で確認する。

## 共通の前段(どちらでも必須)

1. **スコープ確定** — `$ARGUMENTS` にセクター/銘柄指定があればそれに厳密に従い、
   勝手に広げない。無指定なら AskUserQuestion:
   - 対象範囲: 業種横断サンプル / 特定セクター / 特定銘柄リスト
   - 時価総額・流動性フィルタ: なし(Risk & Liquidity が個別評価) / 中大型のみ
2. **vault 先読み**(この session で実行する。**Agent 側は Bash を持たず vault に
   アクセスできない**ので、ここで引いて渡すのが唯一の経路):

   ```bash
   cd <llm-wiki> && export PYTHONUTF8=1
   python scripts/obsidian_client.py list entities/jp          # 既知コード一覧
   python scripts/obsidian_client.py get entities/jp/<code>.md # 該当分だけ
   ```

   frontmatter の `bias` が埋まっていれば Kiyohara+DCF 分析済み、空なら thin stub。
   分析済みの銘柄は **frontmatter + Key Metrics の表だけ**を抜き出して(全文は
   1銘柄1万字超で逆にトークンを食う)、A なら orchestrator プロンプトに
   `### vault 既知データ` 節として貼る(orchestrator.md の Stage 0.5 が受け取る)。
   B は engine 内の tool が自分で引くのでこの手順は不要。
   Obsidian 未起動で引けなければ、その旨を明記して普通に進める(捏造しない)。

## A: subagent orchestrator

1. `orchestrator` が現セッションで使えるか確認。`.claude/agents/*.md` を直前に
   編集した場合、**その変更は新しいセッションでないと反映されない**。
2. `Agent` tool で `subagent_type: orchestrator` を `run_in_background` 起動。
   プロンプトに必ず入れる: 確定スコープ / 「各専門Agentを実際に個別起動し、
   ロールプレイ代行はしない」/ vault で判明済みの銘柄と数値 / 投資助言禁止。
3. 完了通知を待つ間、結果を先回りして予測・捏造しない。

## B: CrewAI graph engine

```bash
cd jp_value_screen_graph
uv run run_with_trigger '{"tickers": ["7203 トヨタ自動車", "8058 三菱商事"]}'
uv run kickoff          # 銘柄無指定(Stage0 が横断的に選定)
```

- Stage 0→1(並列)→2→3(並列)→4→5。構成は同ディレクトリの README 参照。
- 出力: `output/jp-value-screen-<ts>.md` と、`llm-wiki/sources/` への自動ステージ。
- 実行前に確認: Obsidian が起動しているか(vault tool が使える)、
  `ANTHROPIC_API_KEY` に残高があるか(残高切れは 400 で即死する)。

## 実行後(どちらでも)

- 全文を貼らず要約する。上位候補 / 見送り / 全体所感 / データ品質の限界。
- 【実行モード】が各Agentの個別起動を示しているか確認し、単一Agentの代行だった
  場合は最初にその旨を明示する。
- **結果が良かったときだけ** vault に入れる(既定は入れない)。判定基準は
  `agent-memory` skill の「vault に書いてよいのは結果が良かったときだけ」を使う。
  B は `flow.py: _quality_gate()` が自動判定し、落ちた run は vault を触らず
  ローカル出力だけ残す。合格した run も `sources/` にステージされるだけで、
  `wiki/` への昇格は llm-wiki 側で `/wiki-ingest` を実行してからになる。
  A(会話内)の場合は、結果を要約してユーザーに見せ、OK をもらってから書く。

## 絶対ルール

- 投資助言(「買い」「目標株価」等)は一切出力しない。
- `src/` `automation/` `public/data/` など VN Market Dashboard 本体には触れない。
- 網羅性の限界(東証全銘柄の系統的スクリーニングではない)を必ず開示する。
