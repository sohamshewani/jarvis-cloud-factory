import os
import json
import time
import shutil
import subprocess
import urllib.parse
import requests

def run_command(cmd, cwd=None):
    print(f"⚙️ Running: {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd, text=True, capture_output=True)
    if result.returncode != 0:
        print(f"❌ Error: {result.stderr}")
        return False
    return True

def generate_training_data():
    prompt = (
        "Invent a specific AI assistant specialty (e.g., Linux helper, SQL writer, Python debugger, Regex generator). "
        "Reply ONLY with raw JSON containing key 'examples' with 4 pairs of {'user': '...', 'assistant': '...'}. "
        "No markdown, no backticks."
    )
    encoded_prompt = urllib.parse.quote(prompt)
    for attempt in range(3):
        try:
            resp = requests.get(
                f"https://text.pollinations.ai/{encoded_prompt}?json=true",
                timeout=45
            )
            if resp.status_code == 200 and resp.text.strip():
                return resp.text.strip()
        except Exception as e:
            print(f"⚠️ Attempt {attempt + 1} failed: {e}")
            time.sleep(5)
    raise RuntimeError("Cloud AI generator failed after 3 attempts.")

def main():
    timestamp = int(time.time())
    child_name = f"jarvis-cloud-child-{timestamp}"
    work_dir = os.path.abspath(child_name)
    data_dir = os.path.join(work_dir, "data")
    os.makedirs(data_dir, exist_ok=True)

    # 1. Generate training dataset in the cloud
    raw_text = generate_training_data()
    raw_text = raw_text.replace("```json", "").replace("```", "").strip()
    parsed = json.loads(raw_text)

    valid_lines = []
    for item in parsed.get("examples", []):
        if "user" in item and "assistant" in item:
            valid_lines.append(json.dumps({
                "messages": [
                    {"role": "user", "content": str(item["user"])},
                    {"role": "assistant", "content": str(item["assistant"])}
                ]
            }))

    if len(valid_lines) < 2:
        raise RuntimeError("Not enough valid training pairs returned.")

    with open(os.path.join(data_dir, "train.jsonl"), "w") as f:
        f.write("\n".join(valid_lines) + "\n")

    # 2. Create Modelfile & README for the new AI
    with open(os.path.join(work_dir, "Modelfile"), "w") as f:
        f.write(f'FROM qwen2.5:7b\nSYSTEM "You are {child_name}, an AI trained on the attached dataset."\n')

    with open(os.path.join(work_dir, "README.md"), "w") as f:
        f.write(f"# {child_name}\n\nGenerated autonomously in the cloud while MacBook was powered off.\n")

    # 3. Publish new repo to your GitHub account
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
