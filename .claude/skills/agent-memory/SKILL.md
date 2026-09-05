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

## 2つの接続経路

| | 経路 | 使えるのは | 権限 |
|---|---|---|---|
| MCP | `obsidian-vault` サーバ (user scope, `http://127.0.0.1:27123/mcp`) | メインセッション + tools に許可した subagent | **読み取りのみ**を付与 |
| CLI | `scripts/obsidian_client.py` | Bash が使える場所(= メインセッションのみ) | 読み書き両方 |

subagent は Bash を持たないので CLI は使えない。REST API は Authorization
ヘッダ必須で WebFetch では通らない(クエリパラメータ認証は401)。だから
subagent が vault を読む唯一の道が MCP ツール。書き込み系ツールは subagent に
**渡していない** — vault へ入れるのは人が確認した後だけ、という規律のため。

MCPサーバ/agentのtools変更は**新しいセッションから**有効。

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

## vault に書いてよいのは「結果が良かった」ときだけ

vault は長期記憶で、入れたものは後で**事実として読み返される**。中途半端な結果は
入れた瞬間に他のページと見分けがつかなくなり、間違いが定着する。だから
**既定は「書かない」**。次を全部満たしたときだけ書く:

1. **完走したか** — 全ステージに実体のある出力があるか(空・エラー・途中終了でない)
2. **中身があるか** — 銘柄コード・数値・出典が実際に入っているか。
   「取得不可」「評価不能」だらけなら不合格
3. **出典が辿れるか** — 数字ごとにどこから来たか言えるか(fact-only の前提)
4. **ユーザーが見たか** — 自発的に書かない。結果を要約して見せ、
   「入れますか」と確認してから書く

満たさないときは **ローカルに置いて報告するだけ**。「とりあえず sources/ に
入れておく」はしない — それが一番よくある汚染経路。

CrewAI graph engine には同じ規律をコードで実装済み
(`flow.py: _quality_gate()` — 落ちた理由を列挙して vault を触らない)。

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
