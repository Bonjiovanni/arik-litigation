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

## 2026-04-09 — Topic pages compiled

**Source:** Same Supabase corpus. Cross-referenced FTS queries across multiple search terms per topic.

**Pages created:**
- `topics/mortgage_delinquency.md` — 71 emails. Timeline from first missed payment through Dec 2025 CPI non-payment. Key fact: HELOC autopay on 21st, due on 15th.
- `topics/trust_property_insurance.md` — 279 emails (broad search, many overlap). Liberty Mutual lapse Jun 2024 → EastRise CPI force-placement → Kinney broker engagement → ongoing Dec 2025.
- `topics/ltc_claims.md` — 22 direct hits + Via Benefits notifications. Active benefits 2022–2024, uncashed checks 2025, potential unaccounted asset.
- `topics/trustee_removal.md` — 100+ emails. 5-phase timeline: informal complaints → attorney engagement → court proceedings → removal push. Court case 25-CV-02133. Documented breaches table.
