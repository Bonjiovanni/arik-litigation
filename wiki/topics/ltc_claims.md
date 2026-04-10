# LTC Insurance Claims

**Status:** Active claims through 2024; post-death status unclear
**Related entities:** [John Hancock](../entities/john_hancock.md), [Jeanne Lavigne](../entities/jeanne_lavigne.md)
**Key parties:** Via Benefits, Robert Marks (insured)
**Email count:** 9 Hancock + 11 LTC + Via Benefits notifications

---

## Summary

Robert Marks held a Long-Term Care (LTC) insurance policy with John Hancock. The email record shows active benefit payments from at least January 2022 (check deposits) through 2024, with Via Benefits serving as a reimbursement intermediary. Jeanne Lavigne as trustee was responsible for managing claims correspondence — at least one instance (February 2024) shows Hancock requesting additional documentation from her. A 1099-LTC tax form was issued for 2024, and a potential unaccounted Hancock-related asset was flagged in late 2025.

## Via Benefits — Reimbursement Pipeline

Via Benefits (viabenefits.com) appears to be the benefits administrator for Robert Marks' LTC-related expenses. The email corpus contains 12+ automated notifications:

| Date | Event |
|------|-------|
| 2023-09-25 | Bank account info updated, Account info updated |
| 2024-02-25 | Account info updated (×2) |
| 2024-02-27 | **Reimbursement request approved + payment processed** |
| 2024-10-23 | Mobile registered, bank account updated (×2) |
| 2025-03-07 | Reimbursement request received |
| 2025-03-18 | **Reimbursement request approved + payment processed** |
| 2025-03-21 | **Payment failed** — bank account updated same day |
| 2025-03-24 | Support ticket resolved |
| 2025-04-21 | Reminder to deposit checks |
| 2025-05-21 | Second reminder to deposit checks |
| 2025-10-16 | Reminder to deposit checks |
| 2025-11-17 | Second reminder to deposit checks |

**Key observations:**
- Reimbursements were processed as late as March 2025 — 5 months after Robert's death (Oct 2024). These may be for expenses incurred before death.
- A payment failed in March 2025, suggesting bank account changes (possibly related to trust setup).
- Repeated "reminder to deposit checks" notifications (Apr, May, Oct, Nov 2025) suggest uncashed Via Benefits checks.

## Timeline

### 2022: Active Benefits

- **2022-01-24** — "Hancock check deposit confirmation" — Arik deposits a John Hancock LTC benefit check
- **2022-02-17** — Acclaris: "Documents Processed" — related benefits administration
- **2022-03-21** — Untitled email from Arik (context unclear, in LTC search results)

### 2023: Ongoing Claims

- **2023-03-23** — **Jeanne sends "JHC"** — rare proactive communication about John Hancock
- **2023-08-02** — Robert Marks (fido7143@gmail.com) sends: **"2022 LTC long term care 1099 dad robert"** — tax form for prior year
- **2023-09-14** — "ways for you to approach dad?" — Arik email mentioning LTC in context of approaching Robert about care/finances

### 2024: Trustee Action Required

- **2024-02-29** — **"Fyi: received this from Hancock: they need more from you"** — Arik to Jeanne. Hancock requires additional documentation from the trustee. Body: "Not sure if you get notified directly on this yourself or not."
- **2024-08-07** — "You can ignore the Hancock emails" — suggests a resolved issue or duplicate notifications
- **2024-10-28** — **Robert Marks passes.** LTC policy status post-death is unclear from email record.

### 2025: Tax Forms and Unaccounted Assets

- **2025-02-14** — **"More 2024 tax forms (LTC insurance, mortgage, heloc)"** — 1099-LTC from Hancock received for 2024. Combined with mortgage/HELOC 1098s.
- **2025-03-07 through 2025-03-24** — Via Benefits reimbursement cycle: received → approved → payment processed → payment failed → ticket resolved
- **2025-04-21 through 2025-11-17** — Repeated reminders to deposit Via Benefits checks (4 reminders across 7 months)
- **2025-11-21** — "removal leverage — she has created liabilities that ought not to exist" — Hancock referenced in trustee removal context
- **2025-11-26** — "I found another asset she didn't account for" — potential Hancock-related asset missing from trust accounting
- **2025-12-01** — Peterson (Gravel & Shea) responds to the unaccounted asset claim

## Open Questions

1. **Is the LTC policy still active post-death?** — Some LTC policies have death benefits or survivor provisions. No email confirms termination.
2. **What are the uncashed Via Benefits checks?** — 4 deposit reminders over 7 months suggests meaningful uncollected funds.
3. **What documentation did Hancock need from Jeanne in Feb 2024?** — The actual Hancock letter was likely an attachment (not yet extracted from PDF).
4. **What is the unaccounted asset?** — December 2025 emails reference a Hancock-related asset Jeanne didn't include in trust accounting. Amount and nature unknown from email subjects alone.
5. **Via Benefits payment failure (Mar 2025)** — Was this due to Robert's bank account being closed after death? Was it redirected to the trust account?

## Document Pipeline Status

JH LTC documents (downloaded Nov 9, 2025) are in the extraction pipeline:
- Location: `C:\Users\arika\OneDrive\Litigation\08_INCOMING\John Hancock long term care document downloads on 11-9-2025\`
- 8 document types identified (EOB, Claims Correspondence, Provider/Benefit Eligibility, Invoice, Claim Initiation, Direct Deposit, Policy)
- Native digital PDFs — pymupdf extraction path preferred
- Extraction will significantly expand this wiki page with dollar amounts, dates of service, and claim details

## Sources

- Supabase FTS: 9 "Hancock" + 2 "JHC" + 11 "LTC" emails
- Via Benefits automated notifications: 12+ emails
- JH LTC document project: MEMORY.md, doc_data_extraction_spec.md
- All dates and subjects verified against loaded corpus (2026-04-09)
