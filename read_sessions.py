"""Quick script to extract conversation text from JSONL session files."""
import json, sys, glob, os

sessions = {
    "db2eeec1": "C--Users-arika-OneDrive-CLaude-Cowork",
    "635954d3": "C--Users-arika-OneDrive-CLaude-Cowork",
    "566e72fb": "c--Users-arika-Repo-for-Claude-android",
    "9b59582f": "c--Users-arika-Repo-for-Claude-android",
}

base = r"C:\Users\arika\.claude\projects"

for sid, folder in sessions.items():
    pattern = os.path.join(base, folder, f"{sid}*.jsonl")
    matches = glob.glob(pattern)
    for path in matches:
        print(f"\n===== {sid} =====")
        count = 0
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    obj = json.loads(line.strip())
                    if obj.get("type") in ("user", "assistant") and "message" in obj:
                        content = obj["message"].get("content", "")
                        if isinstance(content, list):
                            texts = [c.get("text", "") for c in content if c.get("type") == "text"]
                            content = " ".join(texts)
                        if isinstance(content, str) and len(content) > 20:
                            skip = any(tag in content for tag in ["<local-command", "<command-name", "<ide_opened"])
                            if skip:
                                continue
                            role = obj["message"].get("role", "")
                            print(f"[{role}] {content[:400]}")
                            print("---")
                            count += 1
                            if count > 25:
                                print("... (truncated)")
                                break
                except Exception:
                    pass
