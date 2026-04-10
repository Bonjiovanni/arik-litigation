# John Hancock

**Type:** Insurance company
**Product:** Long-Term Care (LTC) insurance policy for Robert Marks
**Also known as:** Hancock, JHC

---

## Summary

John Hancock is the long-term care insurance provider for Robert Marks (the Trust settlor/dad). The email corpus contains 9 emails mentioning "Hancock" by name, 2 mentioning "JHC", and 11 mentioning "LTC". The record shows an active LTC policy with claims activity dating back to at least 2022, ongoing claims correspondence requiring Jeanne's action in 2024, and 1099-LTC tax forms issued for 2024.

## Key Facts from Email Record

- **Policy type:** Long-Term Care (LTC) insurance
- **Insured:** Robert Marks
- **Claims activity:** Active as of at least 2022 (check deposits) through 2024 (claims correspondence)
- **Tax reporting:** 1099-LTC issued for 2024 (received February 2025)

## Timeline

### 2022: Active Claims

- **2022-01-24** — "Hancock check deposit confirmation" — Arik deposits a John Hancock check. This confirms LTC benefit payments were being received.

### 2023: Jeanne Engages

- **2023-03-23** — Jeanne sends "JHC" to Arik — one of her rare proactive emails. Subject is just "JHC" with no additional context in the subject line. This is one of the few times Jeanne initiates communication about a specific financial matter.
- **2023-03-23** — Arik responds: "Arik here- i think this might be helpful to you, lmk" — forwarding Hancock-related information to Jeanne.

### 2024: Claims Require Trustee Action

- **2024-02-29** — "Fyi: received this from Hancock: they need more from you" — Arik forwards a John Hancock communication to Jeanne. Hancock needs additional documentation or information from the trustee. Body: "Not sure if you get notified directly on this yourself or not."
- **2024-08-07** — "You can ignore the Hancock emails." — Arik tells Jeanne to disregard certain Hancock emails. Context unclear from subject alone — may indicate a resolved issue or duplicate notifications.

### 2025: Tax Reporting and Continued Reference

- **2025-02-14** — "More 2024 tax forms (LTC insurance, mortgage, heloc) and likely error" — 1099-LTC from Hancock received for 2024 LTC insurance. Arik compiles this with mortgage and HELOC tax forms.
- **2025-11-21** — "RE: removal leverage- she has created liabilities that ought not to exist" — Hancock referenced in context of Jeanne's mismanagement and potential leverage for trustee removal.
- **2025-11-24** — Reply continues on removal leverage topic.
- **2025-12-01** — "RE: I found another asset she didn't account for" — Hancock referenced as a potential unaccounted asset.

## Document Types in Pipeline

The JH LTC document project (tracked in MEMORY.md and doc_data_extraction_spec.md) has identified these document types from John Hancock source files:

1. **EOB** (Explanation of Benefits)
2. **Claims Correspondence** (letters)
3. **Provider Eligibility Determination** (letters, sometimes with sub-letters)
4. **Benefit Eligibility Determination** (letters, sometimes with sub-letters)
5. **Invoice**
6. **Document_Claim_Initiation** (fillable form, DocuSign)
7. **Document_Direct_Deposit** (form)
8. **Policy**

Source files location: `C:\Users\arika\OneDrive\Litigation\08_INCOMING\John Hancock long term care document downloads on 11-9-2025\`

## Open Questions

1. **What was the LTC benefit amount?** — Check deposit confirmed in 2022, but dollar amounts not visible in email subjects/bodies queried.
2. **What did Hancock need from Jeanne in Feb 2024?** — The "they need more from you" email body is brief; the actual Hancock letter was likely an attachment (not yet extracted).
3. **Is the LTC policy still active?** — Robert Marks passed (cremation info email 2024-10-28). The policy status post-death is not clear from email subjects alone.
4. **What is the "asset she didn't account for"?** — December 2025 email suggests a Hancock-related asset may be missing from Jeanne's trust accounting.

## Related Entities

- [Jeanne Lavigne](jeanne_lavigne.md) — trustee, responsible for managing LTC claims
- [EastRise](eastrise.md) — separate financial institution (mortgage/HELOC, not LTC)
- Robert Marks — the insured (settlor/dad)
- Via Benefits (donotreply@viabenefits.com) — possibly related to benefits administration

## Sources

- Supabase FTS: 9 emails matching "Hancock", 2 matching "JHC", 11 matching "LTC"
- JH LTC document schema: `doc_data_extraction_spec.md`
- All dates and subjects verified against loaded corpus (2026-04-09)
