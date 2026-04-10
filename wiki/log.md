# Litigation Wiki — Log

Append-only chronological record of ingests, queries, and lint passes.

---

## 2026-04-09 — Wiki initialized

- Created wiki directory structure: `wiki/`, `wiki/entities/`, `wiki/topics/`
- Created `index.md` and `log.md`
- Supabase database loaded: 1,550 emails + 2,154 attachments
- No entity or topic pages compiled yet — pending first ingest cycle

## 2026-04-09 — First entity pages compiled

**Source:** Supabase `emails_master` (1,550 emails) — queried via FTS + structured filters.
**Method:** Subject lines, from/to/cc addresses, date ranges, and body_clean excerpts from key emails.

**Pages created:**
- `entities/jeanne_lavigne.md` — 270 emails involving heronsway@surfglobal.net. Timeline from 2019 personal emails through 2025 eviction proceedings. Key patterns: non-responsiveness, unpaid trust obligations, attorney escalation.
- `entities/eastrise.md` — 48 FTS hits. Mortgage default timeline, HELOC autopay timing issue, CPI insurance, 1098 discrepancy.
- `entities/john_hancock.md` — 9 Hancock + 11 LTC hits. LTC policy for Robert Marks, claims activity 2022–2024, 1099-LTC tax form, potential unaccounted asset.

**Key people identified from email network:**
- Arik Marks (arik.arik@gmail.com) — 512 emails, beneficiary
- Bob Marks (bob_294@surfglobal.net) — 148 emails, settlor/dad
- David Peterson (dpeterson@gravelshea.com) — 70 emails, attorney at Gravel & Shea
- Jeanne (heronsway@surfglobal.net) — 53 from, 270 total, trustee
- Molly Bucci (mbucci@primmer.com) — 43 emails, attorney at Primmer
- Amanda Marks, Matt Marks, Barbara Marks — family members
