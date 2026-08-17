#!/usr/bin/env python3
"""
step1: 从 ECDICT 筛选「六级及以上」词汇（tag 含 cet6/ky/toefl/ielts/gre），
按 COCA 词频(frq)排序，清洗释义，输出单份词表 + 例句范围标记。

输出 words.json: {"words": [...], "example_count": 5000}
"""
import csv
import json
import os
import re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(SCRIPT_DIR, "ecdict.csv")
OUT = os.path.join(SCRIPT_DIR, "words.json")

# 六级及以上的词级标签
HIGH_TAGS = {"cet6", "ky", "toefl", "ielts", "gre"}
# 中小学基础词标签（中考/高考），即使带 ielts/toefl 标签也排除
LOW_TAGS = {"zk", "gk"}
# 前 N 词配例句
EXAMPLE_COUNT = 5000

POS_ONLY = re.compile(r"^[a-z]+\.$")


def clean_translation(t: str) -> str:
    """清洗释义：去掉 [计]/[化]/[网络] 等专业标签及其后续内容，归一化换行。"""
    if not t:
        return ""
    # ECDICT CSV 里换行是字面 \n / \r\n 转义（反斜杠+n），先转成真实换行
    t = t.replace("\\r\\n", "\n").replace("\\r", "\n").replace("\\n", "\n")
    t = t.replace("\r\n", "\n").replace("\r", "\n")
    lines = []
    for line in t.split("\n"):
        line = line.strip()
        if not line:
            continue
        # [ 和 【 在 translation 中只会是专业标签起始符，截断其后内容
        for ch in ("[", "【"):
            if ch in line:
                line = line[: line.index(ch)].strip()
        if not line or POS_ONLY.match(line):
            continue
        lines.append(line)
    return "\n".join(lines)


def main():
    rows = []          # (frq, word, phonetic, translation)
    no_def = 0
    no_phonetic = 0
    phrase = 0

    with open(SRC, encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            if len(row) < 10:
                continue
            word = row[0].strip()
            phonetic = (row[1] or "").strip()
            translation = (row[3] or "").strip()
            tag = (row[7] or "").strip()
            frq_s = (row[9] or "").strip()

            # 只要六级及以上标签，且排除中小学基础词（中考/高考）
            tags = set(tag.split()) if tag else set()
            if not (tags & HIGH_TAGS) or (tags & LOW_TAGS):
                continue
            # 需有 COCA 词频
            try:
                frq = int(frq_s)
            except ValueError:
                continue
            if frq <= 0:
                continue
            # 短语（含空格）不纳入
            if " " in word:
                phrase += 1
                continue

            if not phonetic:
                no_phonetic += 1

            cleaned = clean_translation(translation)
            if not cleaned:
                no_def += 1
                continue

            rows.append((frq, word, phonetic, cleaned))

    rows.sort(key=lambda x: x[0])
    words = [{"word": w, "phonetic": p, "translation": t} for (_f, w, p, t) in rows]

    data = {"words": words, "example_count": EXAMPLE_COUNT}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)

    print(f"✅ 六级及以上词汇: {len(words)} 词")
    print(f"   无音标: {no_phonetic}  释义为空(已过滤): {no_def}  短语(已排除): {phrase}")
    print(f"   前 {EXAMPLE_COUNT} 词配例句")
    if words:
        print(f"   frq 范围: {words[0]['word']}(frq{rows[0][0]}) ~ {words[-1]['word']}(frq{rows[-1][0]})")
    print("\n--- 前 10 词样例 ---")
    for w in words[:10]:
        print(f"  {w['word']}\t{w['phonetic']}\t{w['translation'][:40]}")


if __name__ == "__main__":
    main()
