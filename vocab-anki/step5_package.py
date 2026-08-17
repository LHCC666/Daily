#!/usr/bin/env python3
"""
step5: genanki 打包「六级及以上词汇」牌库（单牌组 + 5 字段笔记类型）。

字段: 单词 / 音标 / 释义 / 例句 / 语音
前 example_count 词配例句（条件渲染），其余仅释义。
"""
import html
import json
import os
import re

import genanki

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WORDS_JSON = os.path.join(SCRIPT_DIR, "words.json")
EXAMPLES_JSON = os.path.join(SCRIPT_DIR, "examples.json")
MEDIA_DIR = os.path.join(SCRIPT_DIR, "media")
OUT_APKG = os.path.join(SCRIPT_DIR, "六级及以上词汇.apkg")

MODEL_ID = 2026081901
DECK_ID = 2026081902
ILLEGAL = re.compile(r'[\\/:*?"<>|\s]+')


def safe_name(word: str) -> str:
    return ILLEGAL.sub("_", word).strip("._")


def load_examples():
    if os.path.exists(EXAMPLES_JSON):
        with open(EXAMPLES_JSON, encoding="utf-8") as f:
            return json.load(f)
    return {}


def build_model():
    return genanki.Model(
        MODEL_ID,
        "英语词汇卡片 (详细释义+例句+音频)",
        fields=[
            {"name": "单词"},
            {"name": "音标"},
            {"name": "释义"},
            {"name": "例句"},
            {"name": "语音"},
        ],
        templates=[
            {
                "name": "词汇卡片",
                "qfmt": (
                    '<div class="word">{{单词}}</div>'
                    '<div class="phonetic">{{音标}}</div>'
                ),
                "afmt": (
                    '{{FrontSide}}<hr id="answer">'
                    '<div class="def">{{释义}}</div>'
                    '{{#例句}}<div class="example">{{例句}}</div>{{/例句}}'
                    '<div class="audio">{{语音}}</div>'
                ),
            }
        ],
        css=(
            ".card{font-family:'Segoe UI',Arial,sans-serif;text-align:center;"
            "color:#333;background:#fafafa;font-size:20px}"
            ".word{font-size:34px;font-weight:700;color:#1a1a1a;margin:20px 0 8px}"
            ".phonetic{font-size:20px;color:#888;margin-bottom:20px}"
            ".def{font-size:18px;line-height:1.6;text-align:left;"
            "margin:10px auto;max-width:600px;white-space:pre-line}"
            ".example{font-size:16px;color:#555;line-height:1.5;text-align:left;"
            "margin:14px auto;max-width:600px;border-top:1px dashed #ddd;padding-top:10px}"
            ".audio{font-size:16px;margin-top:14px}"
        ),
    )


def main():
    with open(WORDS_JSON, encoding="utf-8") as f:
        data = json.load(f)
    examples = load_examples()

    words = data["words"]
    example_count = data.get("example_count", 0)

    model = build_model()
    deck = genanki.Deck(DECK_ID, "六级及以上词汇")

    media_files = []
    example_notes = 0

    for idx, w in enumerate(words):
        word = w["word"]
        phonetic = w.get("phonetic", "") or ""
        translation = (w.get("translation", "") or "").strip()
        fn = safe_name(word) + ".mp3"
        sound = f"[sound:{fn}]"

        example = ""
        if idx < example_count and word in examples:
            example = examples[word]
            example_notes += 1

        note = genanki.Note(
            model=model,
            fields=[word, phonetic, html.escape(translation), html.escape(example), sound],
        )
        deck.add_note(note)

        mp3_path = os.path.join(MEDIA_DIR, fn)
        if os.path.exists(mp3_path):
            media_files.append(mp3_path)

    pkg = genanki.Package(deck)
    pkg.media_files = media_files
    pkg.write_to_file(OUT_APKG)

    print(f"✅ 打包完成: {OUT_APKG}")
    print(f"   总笔记数: {len(words)}")
    print(f"   含例句: {example_notes}")
    print(f"   媒体文件数: {len(media_files)}")
    print(f"   文件大小: {os.path.getsize(OUT_APKG) / 1024 / 1024:.1f} MB")


if __name__ == "__main__":
    main()
