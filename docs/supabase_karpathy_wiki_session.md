# Session Transcript: Supabase Migration & Karpathy LLM Wiki
**Date:** 2026-04-09  
**Project:** Marks Family Trust Litigation — Evidence Pipeline  
**Topics:** Google Cloud alternatives to SQLite, Supabase setup, Karpathy LLM Wiki pattern

---

## Context

This session was a continuation of the litigation evidence pipeline project. The existing architecture uses a local SQLite database (`litigation_corpus.db`) with 1,550 emails and 2,154 attachments loaded, accessed via DB Browser for SQLite (DB4S). The core problem being solved: the laptop has to be on to query the database, and the user wants to query from any device without the laptop running.

---

## Part 1 — Google Cloud Alternatives to SQLite

**Question:** Does Google offer any cloud services equivalent to SQLite?

**Summary of options reviewed:**

| Option | Notes |
|--------|-------|
| Firestore | NoSQL — wrong fit for relational schema |
| Cloud SQL (PostgreSQL) | Best Google option, ~$7-10/month minimum, never scales to zero |
| Cloud Run + Cloud Storage | Run actual SQLite in cloud, both have free tiers |
| AlloyDB | PostgreSQL-compatible, overkill for this scale |
| BigQuery | Analytics warehouse, wrong fit |
| Turso | Third-party cloud-native SQLite, free tier generous, FTS5 native |
| Supabase | PostgreSQL + built-in web GUI + MCP integration, generous free tier |

**SQLite design explained:** The database is just a file. No server process. Application reads/writes directly. Contrast with traditional databases that require a running server process and network connections.

---

## Part 2 — Use Case Definition

**Primary use case:** Query the evidence database from any device without the laptop being on.

**Secondary problem identified:** DB Browser for SQLite (DB4S) — the Windows GUI tool installed — is local only and doesn't solve the "laptop must be on" problem. It's just a visual interface for the local SQLite file.

**Additional pain point:** Slow startup when loading the DB locally — likely caused by Python importing heavy libraries, FTS index not optimized, or OneDrive sync layer adding latency on reads.

**Decision:** Migrate to cloud database. Read/write required (pipeline will continue updating the DB as more attachments are extracted).

---

## Part 3 — Supabase Selected

**Why Supabase over alternatives:**

- Free tier covers the corpus size indefinitely (500MB limit, current data well under that)
- Built-in web GUI (Table Editor + SQL Editor) accessible from any browser on any device
- Official MCP server — Claude Code can query the database directly during pipeline work
- PostgreSQL — proper relational DB, better long term than SQLite for growing corpus
- FTS via `tsvector`/`tsquery` — equivalent capability to SQLite FTS5
- Migration is low-friction since only one source file was loaded to start

**Free tier key limits:**
- 500MB database storage
- 5GB egress
- 2 active projects
- Projects pause after 7 days of inactivity (data retained, manual resume required)
- No automated backups on free tier

**Recommendation:** Start on free tier. If pausing is unacceptable in practice, Pro is $25/month and eliminates it.

**Supabase pricing page:** https://supabase.com/pricing

---

## Part 4 — Karpathy LLM Wiki Pattern

**Source materials reviewed:**
- GitHub Gist: https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f (published April 4, 2026, 5,000+ stars)
- X/Twitter posts
- YouTube video (reviewed via Gemini — content TBD)

**Core idea:** Instead of RAG (rediscovering knowledge from scratch on every query), the LLM incrementally builds and maintains a persistent wiki — a structured, interlinked collection of markdown files. Knowledge is compiled once and kept current, not re-derived on every query.

**Three layers:**
1. **Raw sources** — immutable source documents, LLM reads but never modifies
2. **The wiki** — LLM-generated and maintained markdown files (summaries, entity pages, concept pages, index, log)
3. **The schema** — CLAUDE.md or equivalent that tells the LLM how the wiki is structured and what workflows to follow

**Key operations:**
- **Ingest** — drop new source, LLM reads it, updates 10-15 wiki pages
- **Query** — LLM searches wiki pages, synthesizes answer with citations, can file good answers back as new pages
- **Lint** — periodic health check: contradictions, stale claims, orphan pages, missing cross-references

**Two special files:**
- `index.md` — content-oriented catalog of everything in the wiki
- `log.md` — append-only chronological record of ingests, queries, lint passes

**Optional tooling:** `qmd` — local search engine for markdown files with hybrid BM25/vector search and MCP server. For small wikis the index file is sufficient.

**Obsidian vs alternatives:** Obsidian is recommended for its graph view and plugins, but any markdown editor works — VS Code, Typora, plain text editor. The wiki is just a directory of `.md` files. For this project, VS Code is the right answer since Claude Code already uses it and writes files there directly.

**Karpathy's own setup:** LLM agent open on one side, Obsidian open on the other. LLM makes edits, he browses results in real time. His research wiki on a single topic: ~100 articles, 400,000 words.

---

## Part 5 — How Karpathy Wiki Fits the Litigation Pipeline

**Mapping to existing project:**

| Karpathy Layer | Litigation Project Equivalent | Status |
|---|---|---|
| Raw sources | Aid4Mail exports, PDFs in OneDrive — immutable | ✅ Already exists |
| The wiki | Compiled entity/topic pages | ❌ Gap — doesn't exist yet |
| The schema | CLAUDE.md + MasterSchema.md | ✅ Already exists |

**What this adds:** A persistent synthesis layer on top of the RAG architecture. Instead of asking Gemini to re-synthesize from 1,550 emails every time, compiled wiki pages (e.g., `jeanne_lavigne.md`, `eastrise_mortgage.md`) get richer with every document ingested.

**Wiki directory location decision:** Subfolder within existing repo (`C:\Users\arika\Repo-for-Claude-android\wiki\`) — keeps everything Claude Code touches in one place, GitHub connection means new chats see it automatically, directory boundary provides clean separation from pipeline code.

**Suggested structure:**
```
wiki/
    entities/
        jeanne_lavigne.md
        eastrise.md
        john_hancock.md
    topics/
        mortgage_delinquency.md
        ltc_claims.md
    index.md
    log.md
```

**Integration with Gemini cache:** Wiki files become a third input to the Gemini context cache alongside email corpus and extracted attachment text. Wiki files are small (20-30 pages ≈ 50-100K tokens) — fits easily within the 2M token cache budget. Gemini reads compiled wiki pages first, cross-references raw emails only when needed for verification.

---

## Part 6 — Full Stack Architecture

```
Raw sources (OneDrive, immutable)
        ↓
Supabase — structured metadata + FTS (read/write, any device, web GUI)
        ↓
Wiki — compiled synthesis (Claude Code maintains, markdown files in repo)
        ↓
Gemini cache — semantic search over raw corpus + wiki
        ↓
User, querying from any device
```

**Each layer's job:**

| Layer | Query type | Example |
|---|---|---|
| Supabase | Structured, exact, metadata | "All emails from Jeanne in December 2024" |
| SQLite FTS → PostgreSQL FTS | Keyword/literal | "EastRise", "past due", exact phrases |
| Wiki | Compiled synthesis | "What do we know about Jeanne as of today?" |
| Gemini cache | Semantic/conceptual | "Pattern of LTC payment delays" |

---

## Part 7 — Supabase Setup (Completed This Session)

### Project Details
- **Organization:** Bonjiovanni's Litigators
- **Project name:** Bonjiovanni's Project
- **API URL:** `https://htsjppuoylxepasyghgr.supabase.co`
- **Database engine:** Standard PostgreSQL (OrioleDB alpha was rejected — not production ready)
- **RLS:** Not enabled (sole user, service role key bypasses RLS anyway)

### Credentials
Saved to: `C:\Users\arika\OneDrive\Litigation\Pipeline\.env`

```
SUPABASE_URL=https://htsjppuoylxepasyghgr.supabase.co
SUPABASE_PUBLISHABLE_KEY=<publishable key>
SUPABASE_SECRET_KEY=<secret key>
DB_PASSWORD=<database password>
```

Using new-format keys (Publishable/Secret) rather than legacy JWT-based anon/service_role keys.

### Schema Created

Tables created successfully via SQL Editor:

| Table | Purpose |
|---|---|
| `emails_master` | 1,550 emails from V11.xlsx Merge1 sheet |
| `attachments` | 2,154 attachments from manifest |
| `entity_master` | Shared entity registry |
| `entity_candidates` | Entity resolution candidates |
| `extraction_log` | Per-attachment extraction tracking |
| `_column_map` | Original→mapped column name registry |

All tables showing **UNRESTRICTED** (no RLS) — correct for this use case.

**Key schema decisions vs SQLite:**

| SQLite | PostgreSQL/Supabase |
|---|---|
| FTS5 virtual tables | `TSVECTOR` generated column + GIN index |
| `INTEGER AUTOINCREMENT` | `BIGSERIAL` |
| Single local file | Cloud, always on, any device |
| `PRAGMA foreign_keys = ON` | Foreign keys on by default |
| ~80 extra V11 columns as explicit columns | Stored in `extended JSONB` column |

**FTS query syntax change:**
```sql
-- SQLite FTS5
SELECT * FROM _fts_emails WHERE _fts_emails MATCH 'EastRise';

-- PostgreSQL
SELECT * FROM emails_master WHERE fts_vector @@ to_tsquery('english', 'EastRise');
```

---

## Remaining Steps

- [ ] Install Supabase MCP in `claude_desktop_config.json`
- [ ] Update `corpus_sqlite_loader.py` to use Supabase Python client instead of sqlite3
- [ ] Re-run loader against V11.xlsx + attachment manifest to populate Supabase tables
- [ ] Verify FTS queries work in Supabase SQL Editor
- [ ] Set up wiki directory in repo (`wiki/` subfolder)
- [ ] Define wiki schema/conventions in CLAUDE.md
- [ ] Build first wiki pages (Jeanne Lavigne, EastRise, John Hancock)
- [ ] Integrate wiki into Gemini cache rebuild workflow
- [ ] Update MasterSchema.md to reflect Supabase as the new DB layer

---

## Key References

- Supabase pricing: https://supabase.com/pricing
- Karpathy LLM Wiki gist: https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
- Prior SQLite setup decisions: `docs/sqlite_setup_decisions.md` in repo
- MasterSchema.md: `C:\Users\arika\OneDrive\Litigation\09-Data Schemas\MasterSchema.md`
- `.env` file: `C:\Users\arika\OneDrive\Litigation\Pipeline\.env`

---

*Session transcript — April 9, 2026. To be committed to repo and used to update MasterSchema.md.*
