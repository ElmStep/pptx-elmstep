# -*- coding: utf-8 -*-
"""Notion原稿(Markdown) → ElmStepブランドのPPTX。

変換ルール:
    # 見出し1                  → Section スライド
    ## 見出し2 + 箇条書き       → Bullets スライド
    ## 見出し2 + ### が2つ      → TwoCol スライド（### が左右の見出し）

使い方:
    python3 notion_to_deck.py <原稿.md> <出力.pptx> ["表紙タイトル"] ["表紙サブタイトル"]
"""
import re
import sys

import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from elmstep_pptx import Deck, WRAP, _char_width, jp_wrap


def parse(md: str):
    """Markdownをスライド指示のリストに変換する。"""
    # 表・引用・水平線・コードフェンスは原稿のメタ情報なので落とす
    lines = []
    in_table = False
    for ln in md.split("\n"):
        s = ln.strip()
        if s.startswith("|") or s.startswith("<table") or s.startswith("</table"):
            in_table = True
            continue
        if in_table and not s.startswith("|"):
            in_table = False
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
    cover_title = sys.argv[3] if len(sys.argv) > 3 else "ChatGPT実践研修"
    cover_sub = sys.argv[4] if len(sys.argv) > 4 else "株式会社ElmStep"

    slides = parse(open(src, encoding="utf-8").read())

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
