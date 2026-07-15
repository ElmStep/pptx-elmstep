# -*- coding: utf-8 -*-
"""Notion原稿 → ElmStepブランドのPPTX。

Notion MCP の `notion-fetch` が返した出力を**そのまま**渡せる。
（`<page>` / `<properties>` / `<table>` 等のタグは自動で処理する）

変換ルール:
    # 見出し1                  → Section スライド
    ## 見出し2 + 箇条書き       → Bullets スライド
    ## 見出し2 + ### が2つ      → TwoCol スライド（### が左右の見出し）

使い方:
    python3 notion_to_deck.py <原稿.md> <出力.pptx> ["表紙タイトル"] ["表紙サブタイトル"]

    表紙タイトルを省略すると、Notionページのタイトルを使う。
"""
import json
import re
import sys

import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from elmstep_pptx import Deck, WRAP, _char_width, jp_wrap


# 原稿ページ名によく付く管理用の接尾辞。表紙では邪魔なので落とす。
TITLE_SUFFIXES = ("スライド原稿", "スライド案", "原稿", "台本", "たたき台", "ドラフト", "draft")


def notion_title(raw: str):
    """notion-fetch の <properties> からページタイトルを取り出し、表紙用に整える。

    Notionのページ名は「ChatGPT実践研修（ElmStep版）スライド原稿」のように
    管理用の名前になりがちなので、先頭の絵文字と末尾の管理用ワードを落とす。
    表紙を明示したいときは引数で渡せばこの推定は使われない。
    """
    m = re.search(r"<properties>\s*(\{.*?\})\s*</properties>", raw, re.S)
    if not m:
        return None
    try:
        t = json.loads(m.group(1)).get("title")
    except json.JSONDecodeError:
        return None
    if not t:
        return None

    t = re.sub(r"^[^\w\d（(]+\s*", "", t).strip()  # 先頭の絵文字
    for suf in TITLE_SUFFIXES:
        if t.lower().endswith(suf.lower()):
            t = t[: -len(suf)].strip(" 　_-–—")
            break
    return t or None


def unwrap(raw: str) -> str:
    """notion-fetch の生出力から本文Markdownだけを取り出す。
    そのままのMarkdownを渡された場合は素通しする。"""
    m = re.search(r"<content>\n?(.*?)\n?</content>", raw, re.S)
    if m:
        return m.group(1)
    # <content> が無い＝素のMarkdown。JSONで包まれている場合だけ剥がす
    if raw.lstrip().startswith("{"):
        try:
            return json.loads(raw).get("text", raw)
        except json.JSONDecodeError:
            pass
    return raw


def parse(md: str):
    """Markdownをスライド指示のリストに変換する。"""
    md = unwrap(md)
    # Notionの表ブロックは原稿のメタ情報なので丸ごと落とす
    md = re.sub(r"<table.*?</table>", "", md, flags=re.S)
    # 子ページ参照・データソースタグも落とす
    md = re.sub(r"<page url=.*?</page>", "", md, flags=re.S)
    md = re.sub(r"</?(ancestor-path|properties|page-discussions)[^>]*>", "", md)

    # 引用・水平線・コードフェンス・表の残骸は落とす
    lines = []
    for ln in md.split("\n"):
        s = ln.strip()
        if s.startswith("|") or s.startswith("<t") or s.startswith("</t"):
            continue
        if s.startswith(">") or s == "---" or s.startswith("```"):
            continue
        lines.append(ln)

    slides = []
    cur = None          # 組み立て中の ## ブロック
    skip_h1 = False     # 「書き方のルール」など原稿メタ節を飛ばす

    def flush():
        nonlocal cur
        if cur is None:
            return
        heads = cur["heads"]
        if len(heads) == 2:
            slides.append({"kind": "twocol", "title": cur["title"],
                           "left_head": heads[0]["head"], "left": heads[0]["items"],
                           "right_head": heads[1]["head"], "right": heads[1]["items"]})
        elif cur["items"]:
            slides.append({"kind": "bullets", "title": cur["title"], "items": cur["items"]})
        cur = None

    for ln in lines:
        s = ln.strip()
        if not s:
            continue

        m1 = re.match(r"^#\s+(.+)$", s)
        m2 = re.match(r"^##\s+(.+)$", s)
        m3 = re.match(r"^###\s+(.+)$", s)
        mb = re.match(r"^[-*]\s+(.+)$", s)

        if m1:
            flush()
            title = m1.group(1).strip()
            # 絵文字つきの原稿メタ節（📐書き方のルール 等）はスライドにしない
            skip_h1 = False
            slides.append({"kind": "section", "title": strip_md(title)})
        elif m2:
            flush()
            title = strip_md(m2.group(1).strip())
            if "書き方のルール" in title:
                skip_h1 = True
                continue
            skip_h1 = False
            cur = {"title": title, "items": [], "heads": []}
        elif m3 and cur is not None:
            cur["heads"].append({"head": strip_md(m3.group(1).strip()), "items": []})
        elif mb and not skip_h1:
            item = strip_md(mb.group(1).strip())
            if cur is None:
                continue
            if cur["heads"]:
                cur["heads"][-1]["items"].append(item)
            else:
                cur["items"].append(item)

    flush()
    return slides


def strip_md(t: str) -> str:
    t = re.sub(r"\*\*(.+?)\*\*", r"\1", t)
    t = re.sub(r"`(.+?)`", r"\1", t)
    t = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", t)
    return t.strip()


def check_widths(slides):
    """1ブレット=1行に収まるか検査して、はみ出しを返す。"""
    over = []
    for sl in slides:
        if sl["kind"] == "bullets":
            for it in sl["items"]:
                if jp_wrap(it, WRAP["bullets_body"]).count("\n"):
                    over.append((sl["title"], it, sum(_char_width(c) for c in it), WRAP["bullets_body"]))
        elif sl["kind"] == "twocol":
            for side in ("left", "right"):
                for it in sl[side]:
                    if jp_wrap(it, WRAP["twocol_body"]).count("\n"):
                        over.append((sl["title"], it, sum(_char_width(c) for c in it), WRAP["twocol_body"]))
    return over


def build(slides, out, cover_title, cover_sub):
    d = Deck()  # 冒頭にElmStep会社紹介5枚が自動で入る
    d.cover(cover_title, cover_sub)
    for sl in slides:
        if sl["kind"] == "section":
            d.section(sl["title"])
        elif sl["kind"] == "bullets":
            d.bullets(sl["title"], sl["items"])
        else:
            d.twocol(sl["title"], sl["left"], sl["right"],
                     left_head=sl["left_head"], right_head=sl["right_head"])
    d.cover("Thank you.", "info@elmstep.jp")
    return d.save(out)


if __name__ == "__main__":
    src, out = sys.argv[1], sys.argv[2]
    raw = open(src, encoding="utf-8").read()

    # 表紙タイトルは、指定が無ければNotionページのタイトルを使う
    cover_title = sys.argv[3] if len(sys.argv) > 3 else (notion_title(raw) or "無題")
    cover_sub = sys.argv[4] if len(sys.argv) > 4 else "株式会社ElmStep"
    print(f"表紙: 「{cover_title}」 / {cover_sub}")

    slides = parse(raw)

    kinds = {}
    for s in slides:
        kinds[s["kind"]] = kinds.get(s["kind"], 0) + 1
    print(f"Notion原稿から {len(slides)} 枚を検出: {kinds}")
    for s in slides:
        print(f"  [{s['kind']:7s}] {s['title']}")

    over = check_widths(slides)
    if over:
        print(f"\n⚠️ 1行に収まらないブレット {len(over)} 件（Notion側を短くしてください）:")
        for title, it, w, lim in over:
            print(f"  {title} / w={w:.1f} > {lim}: {it}")
    else:
        print("\n全ブレット 1行に収まる ✓")

    build(slides, out, cover_title, cover_sub)
