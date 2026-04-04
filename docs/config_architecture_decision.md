# Config Architecture Decision
Date: 2026-03-16
Status: DECIDED

## Decision

**Config must NOT live in `filewalker_master.xlsx`.**
Config and data must be in separate workbooks.

## Rationale

`filewalker_master.xlsx` is a **data artifact** — it holds the results of pipeline runs.
It gets overwritten, updated, and re-run. Config mixed into it risks being lost or corrupted
every time the pipeline runs or the schema changes.

Config is **user-curated knowledge** — DocType rules, keywords, triage weights, entity lists.
It must survive pipeline runs, schema migrations, and schema resets.

## Config Workbook Design — DECIDED 2026-03-16

**One config workbook per functional domain/application.** Not one global config book, not one per script.

| Workbook | Owns |
|---|---|
| `fw_config.xlsx` | FileFamily_Config, Keywords_Config, DocType_Rules_Config, Triage_Config, Triage_Bands |
| `lit_config.xlsx` | Extraction field schemas, redaction rules, matter-specific rules |
| `shared_ref.xlsx` | Entity lists, counterparty lists, key people — shared across pipelines |

New domains/applications get their own config workbook when they are built.

## What Goes in Config vs. Data

| Sheet | Belongs in | Notes |
|---|---|---|
| MFI (Master File Inventory) | `filewalker_master.xlsx` | Pipeline output |
| Walk_Coverage | `filewalker_master.xlsx` | Pipeline output |
| Walk_History | `filewalker_master.xlsx` | Pipeline output |
| Classify_History | `filewalker_master.xlsx` | Pipeline output |
| Triage_History | `filewalker_master.xlsx` | Pipeline output |
| FileFamily_Config | config workbook | User-curated |
| Keywords_Config | config workbook | User-curated |
| DocType_Rules_Config | config workbook | User-curated (was lost — must be rebuilt) |
| Triage_Config | config workbook | User-curated |
| Triage_Bands | config workbook | User-curated |

## Migration Required

A migration script must move config sheets OUT of `filewalker_master.xlsx`
and INTO the config workbook. Do NOT delete `filewalker_master.xlsx` during this migration.

Script: `migrate_config_to_fw_config.py` (to be written)

## DocType Rules — LOST, must be rebuilt

The DocType taxonomy was user-dictated in a prior session and stored only in
`filewalker_master.xlsx`. The workbook was deleted during a trial run debug session
(orchestrator error). The taxonomy must be re-dictated by the user and written to disk
**immediately** upon dictation — both to a markdown file and to the config workbook.

Taxonomy source reference: `ltcc_extraction_spec.md` DocType section (user provided in chat 2026-03-16).
