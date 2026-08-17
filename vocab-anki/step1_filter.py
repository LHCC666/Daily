#!/usr/bin/env python3
"""
step1: 从 ECDICT 全量词表按 COCA 词频(frq)过滤排序，取前 15000 词，分 3 段输出。

字段(ecdict.csv): word,phonetic,definition,translation,pos,collins,oxford,tag,bnc,frq,exchange,detail,audio
  - frq: COCA 词频排名，数字越小越常用；0/空 = 未收录词频
"""
import csv
import json
import os
import re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(SCRIPT_DIR, "ecdict.csv")
OUT = os.path.join(SCRIPT_DIR, "words_15000.json")

TOTAL = 15000
SEG = 5000

# 纯词性标记行（清洗后只剩 "art." / "n." 等无释义的），丢弃
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


def load_and_filter():
    rows = []          # (frq, word, phonetic, translation)
    phrase_count = 0   # 含空格的短语数
    no_phonetic = 0
    no_def = 0
    total = 0

    with open(SRC, encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        for row in reader:
            total += 1
            if len(row) < 10:
                continue
            word = row[0].strip()
            phonetic = (row[1] or "").strip()
            translation = (row[3] or "").strip()
            frq_s = (row[9] or "").strip()

            if not word or not frq_s:
                continue
            try:
                frq = int(frq_s)
            except ValueError:
                continue
            if frq <= 0:
                continue

            # 短语（含空格）不纳入单词牌库
            if " " in word:
                phrase_count += 1
                continue

            if not phonetic:
                no_phonetic += 1

            # 过滤清洗后释义为空的词（派生词/纯网络标签），由后续有释义的词补足
            cleaned = clean_translation(translation)
            if not cleaned:
                no_def += 1
                continue

            rows.append((frq, word, phonetic, cleaned))

    rows.sort(key=lambda x: x[0])
    top = rows[:TOTAL]

    print(f"总行数: {total}")
    print(f"有词频(frq>0)单词: {len(rows)}")
    print(f"  其中短语(已排除): {phrase_count}")
    print(f"  其中无音标: {no_phonetic}")
    print(f"  其中释义为空(已过滤): {no_def}")

    # frq 分布（前 15000 的 frq 范围）
    print(f"前 {TOTAL} 词 frq 范围: {top[0][0]} ~ {top[-1][0]}")
    # 词性分布抽样
    return top


def build_payload(top):
    words = [
        {"word": w, "phonetic": p, "translation": t}
        for (_f, w, p, t) in top
    ]
    # 三段
    data = {
        "total": len(words),
        "seg_high": words[0:SEG],          # 1-5000  高频(配例句)
        "seg_mid": words[SEG:SEG * 2],     # 5001-10000
        "seg_low": words[SEG * 2:],        # 10001-15000
    }
    return data


def main():
    top = load_and_filter()
    data = build_payload(top)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"✅ 已写入 {OUT}")
    print(f"   high={len(data['seg_high'])} mid={len(data['seg_mid'])} low={len(data['seg_low'])}")
    # 抽样打印前 10 词
    print("\n--- 前 10 高频词样例 ---")
    for w in data["seg_high"][:10]:
        print(f"  {w['word']}\t{w['phonetic']}\t{w['translation'][:40]}")


if __name__ == "__main__":
    main()
