import os
import json
import time
import shutil
import random
import subprocess
import urllib.parse
import requests

FALLBACK_SPECIALTIES = [
    ("Linux Shell Assistant", [
        {"user": "How do I find all .log files larger than 50MB in Linux?", "assistant": "find / -type f -name '*.log' -size +50M 2>/dev/null"},
        {"user": "How do I check which process is using port 8080?", "assistant": "lsof -i :8080 || ss -tulpn | grep 8080"}
    ]),
    ("Python Performance Optimizer", [
        {"user": "How can I speed up membership checks in a huge Python list?", "assistant": "Convert the list to a set first (`lookup = set(items)`) for O(1) average lookup time instead of O(n)."},
        {"user": "How do I read a 10GB file in Python without running out of RAM?", "assistant": "Iterate line-by-line using `with open('file.txt') as f: for line in f:` instead of calling `f.read()`."}
    ]),
    ("Git Recovery Specialist", [
        {"user": "How do I undo my last commit without losing my code changes?", "assistant": "Run `git reset --soft HEAD~1` to move HEAD back one commit while keeping all changes staged."},
        {"user": "How do I recover a deleted branch in Git?", "assistant": "Find its last commit hash with `git reflog` and recreate it using `git checkout -b branch-name <hash>`."}
    ])
]

def run_command(cmd, cwd=None):
    print(f"⚙️ Running: {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd, text=True, capture_output=True)
    if result.returncode != 0:
        print(f"❌ Error: {result.stderr}")
        return False
    return True

def get_valid_examples():
    prompt = (
        "Invent a specific coding assistant specialty (e.g., Regex, SQL, Docker, Bash). "
        "Keep answers under 2 sentences so the JSON is short and never truncated. "
        "Reply ONLY with raw JSON: {\"examples\": [{\"user\": \"q1\", \"assistant\": \"a1\"}, {\"user\": \"q2\", \"assistant\": \"a2\"}]}"
    )
    encoded = urllib.parse.quote(prompt)
    for attempt in range(3):
        try:
            resp = requests.get(f"https://text.pollinations.ai/{encoded}?json=true", timeout=30)
            if resp.status_code == 200:
                clean = resp.text.replace("```json", "").replace("```", "").strip()
                parsed = json.loads(clean)
                items = [
                    {"user": str(x["user"]), "assistant": str(x["assistant"])}
                    for x in parsed.get("examples", [])
                    if "user" in x and "assistant" in x
                ]
                if len(items) >= 2:
                    print("✅ Cloud AI generated valid JSON training data!")
                    return items
        except Exception as e:
            print(f"⚠️ Attempt {attempt + 1} invalid JSON ({e}). Retrying...")
            time.sleep(3)

    print("ℹ️ Using curated fallback specialty dataset so cloud run succeeds cleanly.")
    _, fallback_items = random.choice(FALLBACK_SPECIALTIES)
    return fallback_items

def main():
    timestamp = int(time.time())
    child_name = f"jarvis-cloud-child-{timestamp}"
    work_dir = os.path.abspath(child_name)
    data_dir = os.path.join(work_dir, "data")
    os.makedirs(data_dir, exist_ok=True)

    # 1. Get guaranteed-valid training pairs
    examples = get_valid_examples()
    valid_lines = [
        json.dumps({
            "messages": [
                {"role": "user", "content": item["user"]},
                {"role": "assistant", "content": item["assistant"]}
            ]
        })
        for item in examples
    ]

    with open(os.path.join(data_dir, "train.jsonl"), "w") as f:
        f.write("\n".join(valid_lines) + "\n")

    # 2. Create Modelfile & README
    with open(os.path.join(work_dir, "Modelfile"), "w") as f:
        f.write(f'FROM qwen2.5:7b\nSYSTEM "You are {child_name}, a specialized AI trained on the attached dataset."\n')

    with open(os.path.join(work_dir, "README.md"), "w") as f:
        f.write(f"# {child_name}\n\nAutonomously generated in the cloud while MacBook was powered off.\n")

    # 3. Publish new repo to GitHub
    git_steps = [
        'git config --global user.name "Jarvis Cloud Bot"',
        'git config --global user.email "bot@users.noreply.github.com"',
        "git init",
        "git add .",
        'git commit -m "Autonomous cloud AI release"',
        f"gh repo create {child_name} --public --source=. --remote=origin --push"
    ]
    for step in git_steps:
        if not run_command(step, cwd=work_dir):
            raise RuntimeError(f"Failed at: {step}")

    # 4. Cloud self-cleanup
    shutil.rmtree(work_dir)
    print(f"✅ Published {child_name} and cleaned up cloud storage!")

if __name__ == "__main__":
    main()
