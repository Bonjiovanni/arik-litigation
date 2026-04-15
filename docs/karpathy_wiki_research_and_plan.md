# Karpathy Wiki Pattern — Research & Implementation Plan

**Date:** 2026-04-10
**Session:** Claude Code (VS Code)
**Purpose:** Research how others implemented the Karpathy LLM Wiki pattern, then design ingest/query/lint workflows for the litigation evidence wiki.

---

## Part 1: Karpathy's Original Method

Source: https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
Published: April 4, 2026 (~5,000+ stars)

### The Core Idea

Most people's experience with LLMs and documents looks like RAG: you upload a collection of files, the LLM retrieves relevant chunks at query time, and generates an answer. This works, but the LLM is rediscovering knowledge from scratch on every question. There's no accumulation.

The idea here is different. Instead of just retrieving from raw documents at query time, the LLM **incrementally builds and maintains a persistent wiki** — a structured, interlinked collection of markdown files that sits between you and the raw sources. When you add a new source, the LLM doesn't just index it for later retrieval. It reads it, extracts the key information, and integrates it into the existing wiki — updating entity pages, revising topic summaries, noting where new data contradicts old claims. The knowledge is compiled once and then kept current, not re-derived on every query.

The wiki is a persistent, compounding artifact. The cross-references are already there. The contradictions have already been flagged. The synthesis already reflects everything you've read.

You never (or rarely) write the wiki yourself — the LLM writes and maintains all of it. You're in charge of sourcing, exploration, and asking the right questions.

### Three-Layer Architecture

1. **Raw sources** — immutable source documents. The LLM reads but never modifies. Source of truth.
2. **The wiki** — LLM-generated markdown files. Summaries, entity pages, concept pages, index, log. LLM owns this entirely.
3. **The schema** — a document (CLAUDE.md or AGENTS.md) that tells the LLM how the wiki is structured, what conventions to follow, and what workflows to execute.

### Three Operations

**Ingest:** Drop a new source in. LLM reads it, discusses takeaways, writes a summary, updates the index, updates relevant entity and concept pages, appends to the log. Single source may touch 10-15 wiki pages. Karpathy prefers one at a time with human involvement.

**Query:** Ask questions against the wiki. LLM reads index first to find relevant pages, reads them, synthesizes answer with citations. Good answers can be filed back as new pages — explorations compound in the knowledge base.

**Lint:** Periodic health-check. Look for contradictions between pages, stale claims, orphan pages with no inbound links, important concepts lacking their own page, missing cross-references. LLM suggests new questions and sources.

### Special Files

- **index.md** — content-oriented catalog. Updated on every ingest. LLM reads it first to find relevant pages. Works at moderate scale (~100 sources, hundreds of pages).
- **log.md** — append-only chronological record. Format: `## [YYYY-MM-DD] operation | title`. Parseable with grep.

### Karpathy's Own Setup

LLM agent on one side, Obsidian on the other. LLM makes edits, he browses in real time. His research wiki on a single topic: ~100 articles, 400,000 words — he didn't write a single word of it directly.

### Key Quote

"The tedious part of maintaining a knowledge base is not the reading or the thinking — it's the bookkeeping. Humans abandon wikis because the maintenance burden grows faster than the value. LLMs don't get bored, don't forget to update a cross-reference, and can touch 15 files in one pass."

---

## Part 2: Research — How Others Implemented It

Researched 12+ sources on 2026-04-10. Full content fetched and analyzed for each.

### Tier 1: Concrete Implementations (code + docs)

#### MehmetGoekce — Claude Code + Logseq
- **Source:** [GitHub](https://github.com/MehmetGoekce/llm-wiki) + [Substack](https://mehmetgoekce.substack.com/p/i-built-karpathys-llm-wiki-with-claude)
- **Best practical source overall.**
- **L1/L2 cache split:** L1 = ~14 files auto-loaded every session (rules, gotchas, identity, credentials). L2 = ~46 wiki pages queried on-demand. Decision rule: "Would Claude making a mistake without this knowledge be dangerous or embarrassing? If yes → L1."
- **Schema enforcement:** 8 namespaces (Business, Tech, Content, Projects, People, Learning, Reference, Careers). 5 page types with required properties (Entity, Project, Knowledge, Feedback, Hub).
- **5-phase ingest:** (1) Analyze & Extract — classify as business/technical/content/project. (2) Scan Wiki — identify affected pages. (3) Update Pages — append, never overwrite. (4) Quality Gate — validate required properties and cross-refs. (5) Report — summarize changes, commit.
- **Lint rules:** orphan detection, staleness checks (90+ days), credential pattern scanning, minimum cross-references per page.
- **Key lessons:** "Schema feels overengineered initially but becomes essential past 10 pages." Parallel agent sessions caused file conflicts and encoding corruption. Hub pages should emerge organically, not be pre-created. Logseq outliner format superior for LLM-generated content (append without restructuring).
- **After 1 week:** 46 pages with synthesized knowledge, dated metrics, explicit rationale, cross-references, and honest gaps labeled as open questions.

#### ussumant/llm-wiki-compiler — Claude Code Plugin
- **Source:** [GitHub](https://github.com/ussumant/llm-wiki-compiler) + [Full docs](https://saydo-5cd0e3d7.mintlify.app/)
- **Most complete tooling.** Full Mintlify documentation site.
- **6 commands:** `/wiki-init`, `/wiki-compile`, `/wiki-ingest`, `/wiki-search`, `/wiki-lint`, `/wiki-query`
- **Two operating modes:** Knowledge Mode (default — compiles markdown docs) and Codebase Mode (v2.0+ — scans repos for embedded knowledge in READMEs, ADRs, API specs).
- **3 adoption modes:** Staging (reference only) → Recommended (wiki preferred) → Primary (wiki is primary source).
- **7-phase compilation:** Scan sources → Classify topics → Compile articles → Discover concepts → Generate schema → Update INDEX.md → Update log.
- **Interactive ingest (`/wiki-ingest`):** (1) File analysis — 3-5 bullet takeaways. (2) Emphasis guidance — "Anything to emphasize or de-emphasize?" (3) Topic classification — confirms affected topics, approves new ones. (4) Article updates — reads current, integrates new, updates coverage indicators. (5) Final updates + summary.
- **Coverage indicators:** `[coverage: high — 5+ sources]` trust directly. `[coverage: medium — 2-4 sources]` good overview. `[coverage: low — 0-1 sources]` check raw files.
- **Concept articles:** Cross-cutting patterns spanning 3+ topics get auto-synthesized (e.g., "Speed vs Quality Tradeoff" found 6 instances across topics).
- **Lint checks:** Stale articles, orphan pages, missing cross-references, low coverage sections, contradictions, schema drift.
- **Config file:** `.wiki-compiler.json` with sources, output, article_sections (customizable per domain), topic_hints, link_style.
- **Incremental:** First compile reads everything (5-10 min). Subsequent runs only reprocess changed files.
- **Result:** "13+ articles, ~161 KB replacing 383 files, 13 MB — reducing token consumption substantially."

#### kfchou/wiki-skills — Claude Code Plugin
- **Source:** [GitHub](https://github.com/kfchou/wiki-skills)
- **5 skills:** wiki-init, wiki-ingest, wiki-query, wiki-lint, wiki-update.
- **Key pattern:** "Surfaces takeaways before writing" — discusses with user before updating pages.
- **Severity-tiered lint reports:** 🔴 (critical), 🟡 (warning), 🔵 (info).
- **Logs unconditionally** — even if no issues found.

#### Ar9av/obsidian-wiki — Multi-Agent Framework
- **Source:** [GitHub](https://github.com/Ar9av/obsidian-wiki)
- **14 skills** including specialized ones: claude-history-ingest, data-ingest, cross-linker, tag-taxonomy, wiki-export.
- **4-stage ingest pipeline:** Ingest → Extract → Resolve → Schema.
- **Provenance marking:** Claims tagged as `extracted` (verbatim from source), `inferred` (synthesized), or `ambiguous` (uncertain).
- **Delta tracking:** `.manifest.json` tracks which sources have been processed — only new/changed files get ingested.
- **Multi-agent support:** Claude Code, Cursor, Windsurf, Codex, Gemini, GitHub Copilot.
- **Graph export:** JSON, GraphML, Neo4j, HTML formats.
- **QMD semantic search** integration with graceful Grep fallback.

#### Astro-Han/karpathy-llm-wiki — Simple Skill
- **Source:** [GitHub](https://github.com/Astro-Han/karpathy-llm-wiki)
- **Simplest implementation.** Installable Claude Code skill via `npx add-skill`.
- 3 operations (ingest/query/lint), minimal schema, good baseline.
- `raw/` with dated subdirectories, `wiki/` with `pages/`, `index.md`, `log.md`.

### Tier 2: Analysis & Guides

#### antigravity.codes — "The Complete Guide to His Idea File"
- **Source:** [Article](https://antigravity.codes/blog/karpathy-llm-wiki-idea-file)
- **Best article.** Specifies YAML frontmatter format: `title`, `type` (concept|entity|source-summary|comparison), `sources`, `related`, `created`, `updated`, `confidence` (high|medium|low).
- Page types: concept, entity, source-summary, comparison.
- Setup commands and maintenance cadence (weekly lint).
- Implementation workflow: setup → config → first ingest → commit → maintain.

#### antigravity.codes — "LLM Knowledge Bases"
- **Source:** [Article](https://antigravity.codes/blog/karpathy-llm-knowledge-bases)
- Karpathy's 6-step workflow: Data Ingest → LLM Compilation → Scale → Querying → Multi-Format Output → Health Checks.
- **Compiler analogy:** raw/ = source code, LLM = compiler, wiki = executable, health checks = tests, queries = runtime.
- Steph Ango (Obsidian CEO) recommends **separate "messy vaults"** for AI-generated content to prevent contamination of personal vaults.
- Tools: Obsidian Web Clipper, MCP servers (gnosis-mcp, library-mcp).

#### AnalyticsVidhya — "LLM Wiki Revolution"
- **Source:** [Article](https://www.analyticsvidhya.com/blog/2026/04/llm-wiki-by-andrej-karpathy/)
- **Document classification before extraction:** Different doc types need different handling. A 50-page research paper needs section-by-section extraction. Social media posts need only primary insights. Meeting transcripts need decisions + action items + quotations.
- **Query result preservation:** Save well-formed Q&A as new wiki pages tagged "query-result."
- **Starting strategy:** Pick one research area with 5-10 quality sources. Don't try to digitize everything at once.
- Invest heavily in the initial system prompt governing classification and page creation rules, then iterate.

#### rohitg00/LLM Wiki v2
- **Source:** [Gist](https://gist.github.com/rohitg00/2067ab416f7bbe447c1977edaaa681e2)
- Conceptual extension: confidence scoring, memory lifecycle tiers (working → episodic → semantic → procedural), knowledge graph with typed relationships, event-driven automation.
- Too complex for our needs. Validates the pattern but overengineers it.

#### MindStudio Guide
- **Source:** [Article](https://www.mindstudio.ai/blog/andrej-karpathy-llm-wiki-knowledge-base-claude-code)
- Page template: H1 + Summary (one sentence) + Tags (#topic) + Created/Updated (ISO timestamps) + Content + Related Notes.
- `inbox/` folder as staging area for unorganized notes.
- 5 top-level categories: projects/, research/, reference/, meetings/, inbox/.

#### Reddit r/Rag — "Using Karpathy's LLM Wiki for Governed Estate Knowledge"
- **Source:** [Reddit](https://www.reddit.com/r/Rag/comments/1sgvvig/using_karpathys_llm_wiki_for_governed_estate/) (could not fetch — Reddit blocked)
- Title suggests someone applied this pattern to estate/trust governance — directly relevant to our litigation use case. Could not retrieve content.

### Synthesized Lessons (consensus across all sources)

1. **5-phase ingest is the consensus:** Analyze/Extract → Scan wiki → Update pages → Quality gate → Report (MehmetGoekce, ussumant, Ar9av all converge)
2. **Interactive ingest > batch:** Surface takeaways first, let user guide emphasis, THEN write (ussumant, kfchou). For litigation this is critical — user must validate before wiki commits a claim.
3. **Coverage indicators** tell you when to trust the wiki vs check raw sources (ussumant: high/medium/low)
4. **Never overwrite, only append:** Each ingest adds; nothing gets deleted without explicit lint + user approval (MehmetGoekce)
5. **Schema enforcement matters past 10 pages:** Without required sections, pages become inconsistent (MehmetGoekce)
6. **Provenance tracking:** Mark claims as extracted (verbatim) vs synthesized (combined) vs flagged (uncertain) (Ar9av)
7. **Document classification before extraction:** Different source types need different handling (AnalyticsVidhya)
8. **Lint should check 6 things:** dead links, orphan pages, stale content, missing cross-refs, contradictions, schema/format drift (ussumant, all agree)
9. **Quality gate before commit:** Validate required sections, cross-refs, Sources section (MehmetGoekce, ussumant)
10. **File good query answers back as wiki pages:** Tagged "query-result" (AnalyticsVidhya, Karpathy)
11. **Start small, iterate schema:** Don't over-engineer upfront. Let it evolve with use (Karpathy, MehmetGoekce, AnalyticsVidhya)

---

## Part 3: Implementation Plan for Litigation Wiki

### What to Build

Add a `## Litigation Wiki` section to CLAUDE.md with concrete workflows for:

**Ingest (5 steps):**
1. Read & Extract — classify doc type, extract key facts, present 3-5 takeaways, ask user for emphasis guidance
2. Scan Wiki — read index.md, identify affected pages, list new pages to create, present plan to user
3. Update Pages — append timeline entries (never overwrite), create new pages from templates, add cross-references, mark provenance
4. Quality Gate — verify required sections, cross-ref links resolve, Sources cite new source with date
5. Log & Commit — update index.md, append to log.md, git commit

**Query (4 steps):**
1. Read index.md to find relevant pages
2. Read those pages — respond with citations if they answer the question
3. If incomplete, query Supabase (FTS or structured)
4. Synthesize answer — optionally file back as wiki page tagged "query-result"

**Lint (6 checks):**
1. Dead links
2. Orphan pages (not in index)
3. Stale claims (verification date older than recent ingests)
4. Missing cross-references (entities mentioned 3+ times without link)
5. Coverage gaps (people with 20+ emails but no entity page)
6. Format violations (missing required sections)

**Page format rules** — formalize existing entity/topic templates with required sections.

**Core principles** — no extrapolation, raw sources immutable, accuracy over speed, provenance on every claim, append never overwrite, interactive before automatic.

### What NOT to Build

| Feature | Source | Why skip |
|---------|--------|----------|
| L1/L2 cache split | MehmetGoekce | CLAUDE.md + MasterSchema.md already serve as L1 |
| .manifest.json delta tracking | Ar9av | Overkill at 7 pages. Revisit past 30. |
| Confidence scoring / knowledge graph | rohitg00 | Litigation needs binary provenance, not probability |
| Coverage indicators | ussumant | Our wiki is hand-compiled, not bulk-compiled. Every section is high-coverage. |
| Automated hooks/triggers | Multiple | User wants manual trigger. Litigation accuracy requires human in loop. |
| New skills or plugins | Multiple | CLAUDE.md instructions are simpler and match existing pattern |
| YAML frontmatter | antigravity.codes | Existing pages use inline metadata blocks. Changing requires rewriting all 7 pages. |
| Concept/comparison pages | Karpathy, ussumant | Only useful past 50+ pages. |

### Files to Modify

Only `C:\Users\arika\.claude\CLAUDE.md` — add the Litigation Wiki section.

### Verification

1. Test ingest: process a JH LTC document and verify it updates entity + topic pages + index + log
2. Test lint: run against current wiki, verify clean report or real issues
3. Test query: ask "What do we know about Via Benefits reimbursements?" and verify wiki → Supabase → synthesis flow
