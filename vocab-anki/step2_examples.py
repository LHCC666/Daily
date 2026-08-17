#!/usr/bin/env python3
"""
step2: 用 DeepSeek API 批量生成前 5000 高频词的例句（英文 + 中文翻译）。

用法: 先设置环境变量 DEEPSEEK_API_KEY（或写 api_key.txt）
      py step2_examples.py [--batch 50]
"""
import json
import os
import sys
import time

import requests

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WORDS_JSON = os.path.join(SCRIPT_DIR, "words_15000.json")
OUT_JSON = os.path.join(SCRIPT_DIR, "examples_5000.json")

API_URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-chat"


def get_api_key():
    key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not key:
        keyfile = os.path.join(SCRIPT_DIR, "api_key.txt")
        if os.path.exists(keyfile):
            with open(keyfile, encoding="utf-8") as f:
                key = f.read().strip()
    if not key:
        print("❌ 未找到 DeepSeek API key。请设置环境变量 DEEPSEEK_API_KEY 或写入 api_key.txt")
        sys.exit(1)
    return key


def load_existing():
    if os.path.exists(OUT_JSON):
        with open(OUT_JSON, encoding="utf-8") as f:
            return json.load(f)
    return {}


def build_prompt(words):
    """words: [(word, translation前40字), ...] 让模型生成准确例句"""
    lines = []
    for w, t in words:
        lines.append(f"- {w}（{t}）")
    wordlist = "\n".join(lines)
    return (
        "你是英语例句生成器。为下列每个单词生成一个简短、自然、地道的英语例句（8-15词），"
        "并给出准确的中文翻译。例句要能清晰体现该单词的常见义项。\n\n"
        "只输出一个 JSON 对象，键是单词，值是\"英文例句｜中文翻译\"格式的字符串。"
        "不要输出任何 JSON 以外的文字。\n\n"
        f"{wordlist}"
    )


def call_deepseek(api_key, prompt, retries=3):
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.6,
        "max_tokens": 4096,
        "response_format": {"type": "json_object"},
    }
    for attempt in range(retries):
        try:
            resp = requests.post(API_URL, headers=headers, json=payload, timeout=120)
            if resp.status_code == 200:
                content = resp.json()["choices"][0]["message"]["content"]
                return json.loads(content)
            else:
                print(f"    HTTP {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            print(f"    异常: {e}")
        time.sleep(2 + attempt * 3)
    return None


def main():
    batch_size = 50
    if "--batch" in sys.argv:
        batch_size = int(sys.argv[sys.argv.index("--batch") + 1])

    api_key = get_api_key()
    with open(WORDS_JSON, encoding="utf-8") as f:
        data = json.load(f)

    words = data["seg_high"]  # 前 5000
    examples = load_existing()
    todo = [w for w in words if w["word"] not in examples]
    print(f"总词数 {len(words)}，已有 {len(examples)}，待生成 {len(todo)}")

    for i in range(0, len(todo), batch_size):
        batch = todo[i:i + batch_size]
        items = [(w["word"], (w["translation"] or "")[:40].replace("\n", " ")) for w in batch]
        prompt = build_prompt(items)

        result = call_deepseek(api_key, prompt)
        if result:
            got = 0
            for w in batch:
                word = w["word"]
                if word in result and result[word]:
                    examples[word] = result[word]
                    got += 1
            print(f"  进度 {min(i + batch_size, len(todo))}/{len(todo)}  本批成功 {got}/{len(batch)}")
        else:
            print(f"  进度 {min(i + batch_size, len(todo))}/{len(todo)}  本批失败")

        # 每批后保存（断点续传）
        with open(OUT_JSON, "w", encoding="utf-8") as f:
            json.dump(examples, f, ensure_ascii=False, indent=1)
        time.sleep(1)

    missing = len(todo) - sum(1 for w in todo if w["word"] in examples)
    print(f"\n✅ 完成: 共 {len(examples)} 条例句，缺失 {missing}")
    if missing:
        print("缺失的词可再次运行本脚本补生成（断点续传）")


if __name__ == "__main__":
    main()
