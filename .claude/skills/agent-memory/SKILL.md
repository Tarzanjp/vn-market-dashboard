---
name: agent-memory
description: 3層メモリ(Claude Code memory / Obsidian llm-wiki vault / CrewAI graph engine)の使い分けと、vault への読み書き手順。JP株の事実・過去の分析を「調べる前に思い出す」ため、また調べた結果を次回に残すために使う。「前に調べたっけ」「これ覚えておいて」「vault/Obsidian に入れて」等で発動。
---

# Agent Memory — 3層構造

調べ直すのが一番高い。**書く前に思い出す、調べる前に vault を見る。**

| 層 | 実体 | 入れるもの | 入れないもの |
|---|---|---|---|
| 1. Claude memory | `~/.claude/projects/<proj>/memory/` | 進め方・好み・決定・**どこに何があるかの指針** | 銘柄の数値、分析結果 |
| 2. Obsidian vault | `llm-wiki/wiki/` (vault ID `41e39fe10c79563c`) | 株の事実: `entities/jp|vn|us/`(JP 176件)・summaries・concepts・MOC | 進行中の作業メモ |
| 3. CrewAI runtime | `jp_value_screen_graph/` | 実行時に vault を引く tool | 恒久データ(層2へ) |

層1は「どこを見ればいいか」だけを持つ。中身は層2にある。この分離を崩さない
(memory に数値を書くと必ず腐る)。

## vault の読み書き(このリポジトリから)

vault は別リポジトリ `…/Private/HocTap/AI/llm-wiki/` にある。

```bash
cd <llm-wiki>            # PYTHONUTF8=1 必須(Windows cp932 で日本語が落ちる)
python scripts/obsidian_client.py get entities/jp/6758.md   # 市場別: jp|vn|us
python scripts/obsidian_client.py list entities/jp
python scripts/obsidian_client.py search "Net Cash Ratio"
echo "..." | python scripts/obsidian_client.py put summaries/<name>.md
echo "..." | python scripts/obsidian_client.py append log.md
```

- **書き込みは必ずこの CLI 経由**(Write/Edit で `wiki/*` を直接触らない)。起動中の
  Obsidian に即反映させるため。読むだけなら Read でもよい。
- `patch-heading` はこの vault では HTTP 400 (`invalid-target`) で失敗する既知の問題。
  get → 文字列結合 → put で回避する。
- Obsidian が起動していないと CLI は接続エラーになる。その時は「vault 未接続」と
  正直に伝える — 記憶を捏造しない。

## どこに書くかの判断

```
事実/分析(銘柄)                    → vault: entities/<jp|vn|us>/<TICKER>.md
事実/分析(業種・概念)              → vault: concepts/ summaries/
生の入力(貼り付けリスト・run出力) → llm-wiki/sources/ (不変。ここが唯一の入口)
進め方・好み・決定・場所の指針     → Claude memory
今回の作業の途中経過               → どこにも残さない(タスク管理で足りる)
```

vault の構造・命名・テンプレ・ingest 手順は `llm-wiki/CLAUDE.md` と
`llm-wiki/.claude/commands/wiki-*.md` が正本。**そちらに従う**(このファイルは
別リポジトリから vault に触るときの入口の説明であって、規約の再定義ではない)。

## 調べる前に

JP株の質問が来たら、Web検索の前に:

1. `list entities/<market>` で該当コードのページが既にあるか見る
2. あれば `get entities/<market>/<code>.md` — frontmatter の `bias` が埋まっていれば
   Kiyohara+DCF 分析済み、空なら thin stub(識別情報のみ)
3. 無い/stub のときだけ Web で調べ、結果は `sources/` に置いて
   `/wiki-ingest`(llm-wiki 側で実行)で vault に昇格させる

CrewAI graph engine 側も同じ規律を tool として実装済み
(`obsidian_wiki_index` / `obsidian_wiki_lookup`、既定は digest 取得で全文の約1/6)。
