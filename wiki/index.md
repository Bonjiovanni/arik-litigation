# Litigation Wiki — Index

Content catalog for the Marks Family Trust litigation knowledge base.
Maintained by Claude Code. Updated on every ingest.

Last updated: 2026-04-09

## Entities

| Page | Type | Email Count | Description |
|------|------|-------------|-------------|
| [Jeanne Lavigne](entities/jeanne_lavigne.md) | Person (Trustee) | 270 from/to/cc, 406 body mentions | Trustee of Marks Family Trust. Central figure in litigation. |
| [EastRise](entities/eastrise.md) | Financial Institution | 48 FTS hits | Credit union holding mortgage, HELOC, bank accounts. Mortgage in default. |
| [John Hancock](entities/john_hancock.md) | Insurance Company | 9 FTS hits + 11 LTC | LTC insurance provider for Robert Marks. |

## Topics

| Page | Email Count | Description |
|------|-------------|-------------|
| [Mortgage Delinquency](topics/mortgage_delinquency.md) | 71 FTS hits | EastRise mortgage default, HELOC late payments, CPI insurance. |
| [Trust Property Insurance](topics/trust_property_insurance.md) | 279 FTS hits | Liberty Mutual lapse, EastRise CPI, Kinney Insurance engagement. |
| [LTC Claims](topics/ltc_claims.md) | 22 FTS hits + Via Benefits | John Hancock LTC policy, Via Benefits reimbursements, uncashed checks. |
| [Trustee Removal](topics/trustee_removal.md) | 100+ FTS hits | Breach of duty evidence, court case 25-CV-02133, attorney escalation timeline. |

## How This Works

This wiki follows the Karpathy LLM Wiki pattern:
- **Raw sources** (emails, PDFs, attachments) are immutable — never modified
- **Wiki pages** are compiled summaries maintained by Claude Code
- **Ingest**: new source → Claude reads it → updates relevant wiki pages
- **Query**: Claude searches wiki first, cross-references raw sources for verification
- **Lint**: periodic check for contradictions, stale claims, orphan pages

See also: [log.md](log.md) for chronological record of all operations.
