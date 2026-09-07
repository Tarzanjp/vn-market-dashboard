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
| vault連携 | MCP tool(読み取りのみ、orchestrator+調査5Agentに付与) | engine内 tool として組込み済み |
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

## 経路C: キーレスの数値パイプライン（LLM を使わない・最も安く確実）

**「ファンダメンタルが良くて割安な銘柄を出す」だけなら、A/B のどちらも要らない。**
`jp_value_screen_graph/tools/` の3本で完結し、APIキーもLLMも消費しない。
A/B は「なぜそうなったか」を言語で調べる段階で使う。

```bash
cd jp_value_screen_graph

# 1) 候補コードを検証・数値化(決算短信PDFを直接読む)
uv run python -m jp_value_screen_graph.tools.jp_fundamentals     1762 5367 7244 9347 ... --json --out screened.json

# 2) 4つのハードフィルタ + 「株価が織り込む成長率」で並べ替え
uv run python -m jp_value_screen_graph.tools.rank screened.json          # 通過分のみ
uv run python -m jp_value_screen_graph.tools.rank screened.json --all    # 落選理由つき全件

# 3) 上位数銘柄だけ通期決算短信を取り、注記まで読む
uv run python -c "from jp_value_screen_graph.tools.jp_fundamentals import     find_annual_tanshin as f; print(f('7244'))"
```

### この順番でなければならない理由

**1と3は別物。** 1が読む四半期決算短信には貸借対照表しかなく、**注記(セグメント
情報・CF計算書・特別損益)が無い**。「なぜ利益率が落ちたか」「なぜ営業CFが減ったか」は
3でしか分からない。40銘柄すべてに3をやるのは無駄なので、2で数銘柄に絞る。

### 何を「良い」と見るか — 比率そのものではなく中身

**Net Cash Ratio の大きさで並べてはいけない。** 実測で順位が大きく入れ替わった:
1762は比率1位(0.59)だが正味現金は時価総額の**0.01倍**、1848は比率+0.22だが実態は
**時価総額の61%に相当する純有利子負債**。比率は事業負債も引くうえ、分子の流動資産が
現金とは限らない。`rank` が並べるのは比率ではない。

| 見る順 | 指標 | なぜ |
|---|---|---|
| 1 | **正味現金/時価総額** | 現金−借入−リース。比率の符号が実態と逆になる罠を消す |
| 2 | **現金/流動資産** | 分子が本当に現金か。1762は15.6%、9347は53.1% |
| 3 | **FCF黒字年数(3期)** | 1期でもマイナスなら DCF の基準値を事実として置けない |
| 4 | **営業利益率の推移** | 増収でも利益が伸びない罠。分析した9銘柄中8銘柄が低下していた |
| 5 | **織込g(株価が織り込む永久成長率)** | 割安さの主指標。低いほど「うまく行かねばならない量」が少ない |

**織込g が主指標である理由:** 内在価値を出すには誰も知らない成長率を置く必要があるが、
逆に解けば「今の株価が何%の成長を前提にしているか」という**仮定の要らない数字**が出る。
7244 は△0.1%、5803 は+6.5%。前者は横ばいで足り、後者は永久に6.5%成長が要る。

### 出た結果を信じる前に

`rank` の出力は**結論ではなく候補**。上位銘柄には必ず次を当てる:

1. **通期決算短信で注記を読む**(手順3)。7244 は投資CF△10,762のうち設備投資は4,578だけで、
   残りは短期貸付金。**報告FCFが3分の1に歪んでいた。**
2. **skill `financial-data-verification`** — 単位・科目・連結/個別・突合
3. **skill `financial-analyst-review`** — FCFのlevered/unlevered、PER履歴のlook-ahead、
   g と設備投資の整合、自己株式

**現状の限界(重要):** このパイプラインは**検証器であって発見器ではない**。
候補コードは人間が与える必要がある(四季報、Kabutanのランキング、既存の
[[stocks-jpx]] MOC など)。市場全体をスキャンする機能は無い。
新しい一括取得ソースを足すのは ToS の判断が要るので、**先に確認すること**。

## 共通の前段(どちらでも必須)

1. **スコープ確定** — `$ARGUMENTS` にセクター/銘柄指定があればそれに厳密に従い、
   勝手に広げない。無指定なら AskUserQuestion:
   - 対象範囲: 業種横断サンプル / 特定セクター / 特定銘柄リスト
   - 時価総額・流動性フィルタ: なし(Risk & Liquidity が個別評価) / 中大型のみ
2. **vault 先読み** — A は orchestrator 自身が MCP ツール
   (`vault_list`/`vault_read`/`search_simple`、読み取り専用)で引くので、
   ここで代行する必要はない。B は engine 内の tool が引く。
   この session から直接確認したいときだけ以下を使う:

   ```bash
   cd <llm-wiki> && export PYTHONUTF8=1
   python scripts/obsidian_client.py list entities/jp          # 既知コード一覧
   python scripts/obsidian_client.py get entities/jp/<code>.md # 該当分だけ
   ```

   frontmatter の `bias` が埋まっていれば Kiyohara+DCF 分析済み、空なら thin stub。
   Obsidian 未起動なら MCP も CLI も繋がらない。その場合は「vault 参照なし」と
   明記して普通に進める(捏造しない)。

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
