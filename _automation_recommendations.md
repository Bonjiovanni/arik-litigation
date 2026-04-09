# Claude Code Automation Recommendations
Generated: 2026-04-03
Source: `/claude-code-setup:claude-automation-recommender` analysis

---

## What Was Checked
- `~/.claude/settings.json` — all hooks, MCPs, permissions (full content read)
- `~/.claude/agents/` — all 4 agent definitions (full content read)
- `~/.claude/skills/` — custom skills
- `~/.claude/plugins/marketplaces/` — available plugins and external_plugins
- `.claude/settings.json` in repo — project-level config
- `requirements.txt`, `docs/pipeline_architecture.md`, `_testing_needed.md`
- `claude mcp list` — live MCP connection status

---

## What Already Exists — Do NOT Redundantly Recommend

| Category | Already configured |
|---|---|
| Hook | `PostToolUse Write\|Edit` → fires testing-guru + doc-keeper agents |
| Hook | `FileChanged` → warns when CLAUDE.md / MasterSchema.md / etc. change |
| Hook | `UserPromptSubmit` → injects TDD reminder when coding keywords detected |
| Agents | testing-guru, doc-keeper, hr-agent, orchestrator — all fully defined |
| Skills | legal-style-comparator (custom), fw (plugin), all superpowers skills, commit-commands, feature-dev |
| MCPs | sequential-thinking, microsoft-learn, gmail, gcal, midpage legal — all connected |

---

## Recommendations (in priority order)

---

### 1. ⚡ Hook — Block `tests/` edits from the main session
**Status:** NOT YET DONE  
**Why:** CLAUDE.md says "NEVER edit test files — that is exclusively the Testing Guru's job."
Currently this is only a text rule. Nothing structurally prevents the main orchestrator session
from accidentally writing to `tests/`. A PreToolUse hook makes it impossible.

**Add to `~/.claude/settings.json` inside the existing `"hooks"` block:**
```json
"PreToolUse": [
  {
    "matcher": "Write|Edit",
    "hooks": [
      {
        "type": "command",
        "command": "python3 -c \"import sys,json; d=json.load(sys.stdin); p=d.get('file_path','').replace(chr(92),'/'); sys.exit(2) if '/tests/' in p or p.endswith('/tests') else sys.exit(0)\"",
        "timeout": 5000
      }
    ]
  }
]
```
Exit code 2 = hard block. Main session sees an error and the write never happens.

---

### 2. 🔌 MCP — Install context7
**Status:** NOT YET DONE (plugin is on disk but not enabled)  
**Why:** The `external_plugins/context7/` folder is already in your plugin marketplace,
but context7 is not installed as a live MCP. Your pipeline uses PyMuPDF (version-sensitive),
xlsxwriter, and FastAPI — libraries where stale training data causes hallucinated method
signatures. Especially important for building `fw_ocr.py` (next planned stage).

**Install:**
```bash
claude mcp add context7 -s user
```
(`-s user` = global scope, per your MCP install scope memory rule)

---

### 3. 🔴 MCP Cleanup — Remove dead chroma entry
**Status:** NOT YET DONE (and currently showing errors every session)  
**Why:** `chroma` MCP is configured pointing to `localhost:8000` but shows `✗ Failed to connect`
every session. Per `docs/pipeline_architecture.md`, the Chroma/RAG layer is "planned, not yet built."
The MCP is premature and noisy.

**Remove:**
```bash
claude mcp remove chroma -s user
```
Re-add when the RAG layer is actually deployed.

---

### 4. 🎯 Skill — fw-merge (grp files → merged module)
**Status:** NOT YET DONE  
**Why:** The grp→merged module assembly pattern has happened 4 times (dirmap, walk, classify, triage)
and will happen again for `fw_ocr.py`. Each time it's done ad hoc. A skill wrapping the checklist
makes future merges repeatable and safe.

**Create:** `~/.claude/skills/fw-merge/SKILL.md`

Key checklist items to embed:
1. Read all `fw_X_grpN.py` files for the target stage
2. Verify no duplicate function names across groups
3. Verify COLUMNS list in grp2 matches any existing merged module
4. Write `fw_<stage>.py`: stdlib → third-party → local → constants → functions in grp order
5. Write `_testing_needed.md` entry flagging the merged module for integration tests
6. Announce: "Merged. Testing Guru needs to write `test_fw_<stage>.py`"

Ask Claude or the hr-agent to write the full SKILL.md when ready.

---

### 5. 🤖 Subagent — fw-stage-builder
**Status:** NOT YET DONE  
**Why:** All 4 existing agents (testing-guru, doc-keeper, hr-agent, orchestrator) are infrastructure agents.
There's no domain specialist for the fileWalker pipeline's next major work: `fw_ocr.py`.
An agent with the pipeline architecture baked in (ProcessingStatus chain, grpN pattern, required
columns, TDD sequence) avoids re-explaining the architecture from scratch each time.

**Create:** `~/.claude/agents/fw-stage-builder.md`

Key context to embed in the agent:
- Pipeline stage pattern: grp1 (utilities) → grp2 (sheet/column defs) → grp3 (core logic) → grp4 (history/logging) → grp5 (main + namespace)
- ProcessingStatus chain: `file_listed → classified → triaged → ocr_complete`
- `fw_ocr.py` input: rows where `NeedsOCR = "Y"`
- `fw_ocr.py` output columns: `OCRSnippet`, `NeedsOCR` (update), `ProcessingStatus → ocr_complete`
- Three OCR approaches (per architecture doc): Acrobat Pro, Claude Vision API, hybrid
- Always write tests before implementation (TDD)
- After each grp file: write `_testing_needed.md` entry

Ask the hr-agent to write the full agent definition when ready to start `fw_ocr.py`.

---

## Implementation Order (suggested)
1. **Items 2 + 3** — one-line commands, do immediately (2 min)
2. **Item 1** — settings.json edit, low risk (5 min)
3. **Item 4** — skill file, do before next grp→merge operation
4. **Item 5** — agent file, do before starting `fw_ocr.py` development
