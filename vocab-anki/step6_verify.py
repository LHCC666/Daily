#!/usr/bin/env python3
"""
step6: 解包 .apkg 验证（笔记数/字段/音频/例句完整性）。
复用之前解包「所有牌组.apkg」的经验：collection.anki21b 是 zstd 压缩的 SQLite。
"""
import io
import json
import os
import sqlite3
import zipfile

import zstandard

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
APKG = os.path.join(SCRIPT_DIR, "六级及以上词汇.apkg")


def read_collection(z: zipfile.ZipFile) -> sqlite3.Connection:
    # genanki 生成 collection.anki2（普通 SQLite）；新版 Anki 用 anki21b（zstd 压缩）
    name = "collection.anki21b" if "collection.anki21b" in z.namelist() else "collection.anki2"
    raw = z.read(name)
    if name.endswith("anki21b"):
        dctx = zstandard.ZstdDecompressor()
        raw = dctx.stream_reader(io.BytesIO(raw)).read()
    tmp = os.path.join(SCRIPT_DIR, "_verify_tmp.db")
    with open(tmp, "wb") as f:
        f.write(raw)
    con = sqlite3.connect(tmp)
    con.create_collation(
        "unicase", lambda a, b: (a.lower() > b.lower()) - (a.lower() < b.lower())
    )
    return con


def main():
    with zipfile.ZipFile(APKG) as z:
        names = z.namelist()
        con = read_collection(z)

        # 笔记总数
        total = con.execute("SELECT count(*) FROM notes").fetchone()[0]
        # 按牌组统计（decks 存在 col.decks JSON 里）
        decks = json.loads(con.execute("SELECT decks FROM col").fetchone()[0])
        deck_rows = []
        for did, cnt in con.execute("SELECT did, count(*) FROM cards GROUP BY did"):
            name = decks.get(str(did), {}).get("name", str(did))
            deck_rows.append((name, cnt))

        print(f"📦 笔记总数: {total}")
        for name, cnt in deck_rows:
            print(f"   {name}: {cnt}")

        # 字段完整性：flds 用 \x1f 分隔（5 字段）
        missing = {"音标": 0, "释义": 0, "例句": 0, "语音": 0}
        example_count = 0
        for (flds,) in con.execute("SELECT flds FROM notes"):
            parts = flds.split("\x1f")
            word, phonetic, trans, example, sound = parts[0], parts[1], parts[2], parts[3], parts[4]
            if not phonetic:
                missing["音标"] += 1
            if not trans:
                missing["释义"] += 1
            if not sound:
                missing["语音"] += 1
            if example:
                example_count += 1
        print(f"   缺失音标: {missing['音标']}  缺失释义: {missing['释义']}  缺失语音: {missing['语音']}")
        print(f"   含例句笔记: {example_count}")

        # 媒体文件
        media_count = sum(1 for n in names if n.isdigit())
        print(f"🎵 媒体文件数: {media_count}")

        # 抽样：第一张卡片的完整内容
        row = con.execute("SELECT flds FROM notes LIMIT 1").fetchone()
        if row:
            parts = row[0].split("\x1f")
            print("\n--- 样例卡片 ---")
            for i, name in enumerate(["单词", "音标", "释义", "例句", "语音"]):
                print(f"  {name}: {parts[i][:80]}")

        con.close()
        os.remove(os.path.join(SCRIPT_DIR, "_verify_tmp.db"))
        print(f"\n✅ 验证完成")


if __name__ == "__main__":
    main()
