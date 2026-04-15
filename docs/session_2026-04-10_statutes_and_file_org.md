# Session: Vermont Statutes Scraping & File Organization

**Date:** 2026-04-10
**Session:** Claude Code (VS Code)

---

## Vermont Statutes Scraped

Scraped all chapters from 8 titles of the Vermont Statutes Annotated from https://legislature.vermont.gov/statutes/

### Titles Scraped

| Title | Name | Chapters | Sections |
|-------|------|----------|----------|
| 8 | Insurance | 101 | ~large |
| 9 | Commerce and Trade | 71 | ~large |
| 12 | Court Procedure | 68 | ~large |
| 13 | Crimes and Criminal Procedure | 78 | ~large |
| 14 | Decedents Estates and Fiduciary Relations | 41 | ~large |
| 14A | Trusts | 14 | ~large |
| 15 | Domestic Relations | 16 | ~large |
| 27 | Property | 13 | ~large |
| **Total** | | **388 chapters** | **5,681 sections** |

### File Format

Each chapter is one markdown file with verbatim statutory text:

```
# VSA Title 14, Chapter 1: Wills

**Title 14:** Decedents Estates and Fiduciary Relations
**Source:** https://legislature.vermont.gov/statutes/fullchapter/14/001
**Retrieved:** 2026-04-10

---

## § 1. Who may make

Every individual 18 years of age or over or emancipated by court order
who is of sound mind may make a will in writing. (Amended 2017, No. 195...)
```

- Section headers as `##` (H2)
- Subsection indentation preserved (3 spaces per level for (a), (1), (A) hierarchy)
- Amendment history included verbatim
- Section symbols (§) preserved
- Source URL and retrieval date in header

### Naming Convention

- Filenames: `VSA_[title].[chapter] [chapter name].md`
- Examples: `VSA_14.1 Wills.md`, `VSA_14A.4 Creation, Validity, Modification, and Termination of Trust.md`
- Title folders: `Title 8`, `Title 14`, `Title 14A`, etc. (number only, no name)
- Index file: `index.md` in root — lists all titles with full names and all chapters

### Scraper Script

`C:\Users\arika\Repo-for-Claude-android\scrape_vsa.py` — reusable if additional titles are needed.

### TODO

- [ ] Prune to chapters actually relevant to the litigation case

---

## Vermont Rules of Probate Procedure (VRPP)

Found 6 individual VRPP rule PDFs on disk (not the complete rulebook):

| File | Original Location |
|------|-------------------|
| VRPP 7 Pleadings and Motions.pdf | Litigation Downloads\Paxton Generated Documents\ |
| VRPp 8 Rules of Pleading.pdf | Litigation Downloads\Paxton Generated Documents\ |
| VRPP 9 Pleading Special Stuff.pdf | Litigation Downloads\Paxton Generated Documents\ |
| VRPP 10 Form of pleadings.pdf | Litigation Downloads\Paxton Generated Documents\ |
| VRPP66.pdf | Pixel 7 files transferred here\Download\ |
| VRPP 67 Fiduciaries and Special fiduciaries.pdf | Litigation Downloads\Paxton Generated Documents\ |

Merged into single PDF in numerical order (7, 8, 9, 10, 66, 67):
`Vermont Rules of Probate Procedure - selected sections.pdf`

---

## Other Court Rules PDFs

Copied from Downloads to Vermont_Rules folder:

| File | Size |
|------|------|
| RULES OF CIVIL PROCEDURE.pdf | 6,027 KB |
| RULES OF CRIMINAL PROCEDURE.pd.pdf | 2,220 KB |
| RULES OF EVIDENCE.pdf | 2,565 KB |
| VERMONT SUPREME COURT ADMINIST.pdf | 10,112 KB |

---

## File Organization Changes

### Moves performed this session:

1. **Probate Court Forms** — moved from `Litigation\Litigation Downloads\Probate Court Forms\` to `Litigation\Statutes\Probate Court Forms\`

2. **Statutes folder renamed** — `Litigation\Statutes\` → `Litigation\VT Statutes and Rules\` (had to copy+delete due to OneDrive sync lock on rename)

3. **Final move** — `Litigation\VT Statutes and Rules\` → `Litigation\06_REFERENCES\VT Statutes and Rules\`

### Final folder structure:

```
C:\Users\arika\OneDrive\Litigation\06_REFERENCES\VT Statutes and Rules\
    index.md                          ← master index of all titles + chapters
    Vermont\                          ← scraped statute markdown files
        Title 8\
            VSA_8.1 [name].md
            ...
        Title 9\
            ...
        Title 12\
            ...
        Title 13\
            ...
        Title 14\
            VSA_14.1 Wills.md
            VSA_14.3 Probate and Procedure for Construction of Wills.md
            ...
        Title 14A\
            VSA_14A.1 General Provisions and Definitions.md
            ...
        Title 15\
            ...
        Title 27\
            ...
    Vermont_Rules\                    ← court rules PDFs
        RULES OF CIVIL PROCEDURE.pdf
        RULES OF CRIMINAL PROCEDURE.pd.pdf
        RULES OF EVIDENCE.pdf
        VERMONT SUPREME COURT ADMINIST.pdf
        Vermont Rules of Probate Procedure - selected sections.pdf
    Probate Court Forms\              ← court forms
        700-00300 - Generic Motion - Probate.pdf
        700-00305 - General Affidavit - Probate.pdf
```
