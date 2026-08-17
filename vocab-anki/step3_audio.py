#!/usr/bin/env python3
"""
step3: edge-tts 批量生成美音 mp3（文件名 = 单词.mp3），支持断点续传 + 并发限流。

用法: py step3_audio.py [--seg high|mid|low|all] [--concurrency 8]
"""
import asyncio
import json
import os
import re
import sys

import edge_tts

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WORDS_JSON = os.path.join(SCRIPT_DIR, "words_15000.json")
MEDIA_DIR = os.path.join(SCRIPT_DIR, "media")
VOICE = "en-US-AriaNeural"

# 文件名非法字符 -> 下划线
ILLEGAL = re.compile(r'[\\/:*?"<>|\s]+')


def safe_name(word: str) -> str:
    return ILLEGAL.sub("_", word).strip("._")


async def gen_one(word: str, sem: asyncio.Semaphore, retries: int = 3):
    path = os.path.join(MEDIA_DIR, safe_name(word) + ".mp3")
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return "skip"
    async with sem:
        for attempt in range(retries):
            try:
                tts = edge_tts.Communicate(word, VOICE)
                await tts.save(path)
                return "ok"
            except Exception as e:
                if attempt == retries - 1:
                    return f"fail:{word}:{e}"
                await asyncio.sleep(1 + attempt * 2)
    return "fail"


async def main():
    seg = "all"
    concurrency = 8
    if "--seg" in sys.argv:
        seg = sys.argv[sys.argv.index("--seg") + 1]
    if "--concurrency" in sys.argv:
        concurrency = int(sys.argv[sys.argv.index("--concurrency") + 1])

    with open(WORDS_JSON, encoding="utf-8") as f:
        data = json.load(f)

    if seg == "all":
        words = data["seg_high"] + data["seg_mid"] + data["seg_low"]
    else:
        words = data[f"seg_{seg}"]

    os.makedirs(MEDIA_DIR, exist_ok=True)
    sem = asyncio.Semaphore(concurrency)

    # 预扫描已有文件，跳过
    todo = [w["word"] for w in words]
    done = sum(1 for w in todo if os.path.exists(os.path.join(MEDIA_DIR, safe_name(w) + ".mp3")))
    print(f"总词数 {len(todo)}，已有 {done}，待生成 {len(todo) - done}")

    ok = skip = 0
    fails = []
    for i in range(0, len(todo), 100):
        batch = todo[i:i + 100]
        results = await asyncio.gather(*(gen_one(w, sem) for w in batch))
        for r in results:
            if r == "ok":
                ok += 1
            elif r == "skip":
                skip += 1
            else:
                fails.append(r)
        print(f"  进度 {min(i + 100, len(todo))}/{len(todo)}  ok={ok} skip={skip} fail={len(fails)}")

    print(f"\n✅ 完成: ok={ok} skip={skip} fail={len(fails)}")
    if fails:
        with open(os.path.join(SCRIPT_DIR, "audio_fail.log"), "w", encoding="utf-8") as f:
            f.write("\n".join(fails))
        print("失败清单已写 audio_fail.log")


if __name__ == "__main__":
    asyncio.run(main())
