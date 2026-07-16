# pptx-elmstep

ElmStepブランドのPowerPoint資料を生成する **Claude Code スキル**です。

スライドマスターと4つのレイアウト（Cover / Section / Bullets / TwoCol）を `.pptx` の中に組み込んだ状態で出力するので、納品先がPowerPointで開いても「新しいスライド」から4レイアウトをそのまま選べます。

## デザイン

- ペーパー背景 `#F7F5F0` + 7pt のグラデ枠（左 深緑 `#123B2B` → 右 ゴールド `#B99855`）
- 右上に「ElmStep.」ワードマーク（マスター継承）
- 箇条書きタイトル下に50%幅のグラデ下線
- フォント: Noto Sans JP（macOSはヒラギノfallback）
- [BudouX](https://github.com/google/budoux) で日本語を文節境界に折り返し、1〜2文字の孤立行（寡婦）を自動回避

| 用途 | カラー |
|---|---|
| 背景（ペーパー） | `#F7F5F0` |
| テキスト（インク） | `#1C2A23` |
| アクセント（深緑） | `#123B2B` |
| サブアクセント（ゴールド） | `#B99855` |
| サブテキスト | `#5C6B62` |

## インストール

```bash
git clone https://github.com/ElmStep/pptx-elmstep.git
mkdir -p ~/.claude/skills
cp -r pptx-elmstep/pptx_elmstep ~/.claude/skills/
pip3 install python-pptx budoux --break-system-packages
```

Claude Code を再起動すると、「パワポ作って」「プレゼン資料つくって」などで自動的に発動します。

## 使い方

```python
from elmstep_pptx import Deck

d = Deck()  # 冒頭にElmStep会社紹介5枚が自動で入る（不要なら Deck(include_intro=False)）

d.cover("生成AI活用研修", "株式会社ElmStep")

d.twocol("本日のアジェンダ",
    ["1. 生成AIの基礎", "2. 業務への落とし込み"],
    ["3. ハンズオン", "4. 定着と自動化"],
    left_head="前半", right_head="後半")

d.section("Day 1 — 基礎を理解する")

d.bullets("研修のねらい", [
    "現場の業務に直結する形で使えるようにする",
    "研修で終わらせず、定着まで伴走する",
])

d.cover("Thank you.", "info@elmstep.jp")

d.save("output.pptx")
```

```bash
python3 build.py
```


## Notion原稿から生成する

原稿をNotionで管理し、スライドは何度でも作り直す運用ができます。Notionページの本文Markdownを `.md` に保存して渡すだけです。

```bash
python3 pptx_elmstep/notion_to_deck.py 原稿.md 出力.pptx "表紙タイトル" "株式会社ElmStep"
```

| Notionの書き方 | 生成されるスライド |
|---|---|
| `# 見出し1` | Section（章の区切り） |
| `## 見出し2` ＋ 箇条書き | Bullets（箇条書き1枚） |
| `## 見出し2` の下に `### 見出し3` が2つ | TwoCol（左右の対比1枚） |

Notion MCP の `notion-fetch` が返した出力を、**加工せずそのまま** `.md` に保存して渡せます（`<page>` や `<table>` のタグが付いたままでOK）。手でMarkdownに書き起こす必要はありません。

引用・表・水平線は原稿のメタ情報として自動で無視するので、Notionページの冒頭に記法ガイドを置いたままにできます。生成前に全ブレットが1行に収まるかを検査し、はみ出すものを警告します。

表紙タイトルを省略すると、Notionのページ名から先頭の絵文字と末尾の管理用ワード（`スライド原稿`／`原稿`／`台本`／`ドラフト` 等）を落として使います。

## API

| メソッド | 用途 |
|---|---|
| `Deck(template=None, include_intro=True)` | デッキを作る。`include_intro=False` で会社紹介5枚なし |
| `d.cover(title, subtitle="")` | 表紙 |
| `d.section(title)` | セクション区切り |
| `d.bullets(title, items)` | 箇条書き |
| `d.twocol(title, left, right, left_head=, right_head=)` | 2列（対比・before/after用） |
| `d.save(path)` | `.pptx` として保存 |

`elmstep_pptx.BRAND` にブランドカラーのHEX辞書があります。図形やグラフを自分で足すときに参照してください。

詳細は [`pptx_elmstep/SKILL.md`](pptx_elmstep/SKILL.md) を参照。

## 同梱ファイル

| ファイル | 中身 |
|---|---|
| `pptx_elmstep/SKILL.md` | スキル定義（Claude Codeが読む） |
| `pptx_elmstep/elmstep.pptx` | 空テンプレート |
| `pptx_elmstep/elmstep_intro.pptx` | 会社紹介5枚入りテンプレート |
| `pptx_elmstep/elmstep_pptx.py` | `Deck` ヘルパー |
| `pptx_elmstep/notion_to_deck.py` | Notion原稿(Markdown)→デッキ コンバータ |
| `sample-materials/` | 研修デモ用の名刺20枚・領収書20枚（**MIT対象外**） |

## サンプル素材（名刺・領収書）

[`sample-materials/`](sample-materials/) に、AI研修のハンズオンで使うスキャン練習用の画像を置いています。すべて架空の会社・人物・取引で、実在の個人情報は含まれません。

| フォルダ | 中身 | 枚数 |
|---|---|---|
| [`sample-materials/cards/`](sample-materials/cards/) | 名刺の写真 | 20枚 |
| [`sample-materials/receipts/`](sample-materials/receipts/) | 領収書の写真 | 20枚 |

**この素材はMIT Licenseの対象外です。** 著作権は [takpfive](https://github.com/takpfive/claude-code-course-materials-2026-04) 氏に帰属し、株式会社ElmStepが許諾を得て再掲しているものです。再利用には著作権者の許諾が必要です。詳細は [`sample-materials/README.md`](sample-materials/README.md) を参照してください。

## 依存

- Python 3
- [python-pptx](https://python-pptx.readthedocs.io/)
- [budoux](https://github.com/google/budoux)

## ライセンス

**MIT License** — ただし対象は `pptx_elmstep/` 配下のコードとテンプレートのみです。詳細は [LICENSE](LICENSE) を参照。

`sample-materials/` 配下の画像は**MITの対象外**です（著作権は takpfive 氏、ElmStepは許諾を得て再掲）。

ブランドカラー・ワードマーク・会社紹介スライドの内容は株式会社ElmStepに帰属します。フォークして自社ブランドで使う場合は `elmstep.pptx` のマスター色とワードマーク、`elmstep_intro.pptx` の内容を差し替えてください。

---

株式会社ElmStep — 生成AI研修とAI業務システム開発
[info@elmstep.jp](mailto:info@elmstep.jp)
