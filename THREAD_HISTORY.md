# Thread History

This file is updated after each significant interaction in this Claude Code session.

| # | Date | Topic | Key Decision / Output |
|---|------|-------|----------------------|
| 1 | 2026-02-25 | Initial build: Excel workbook with Android-safe structured references | Chose openpyxl + ZIP post-processor pipeline. Produces `<calculatedColumnFormula>` in table XML + `t="shared"` shared-formula pattern in worksheet XML. Generated `workbook.xlsx` with 5 sheets (01_Entities, 02_Aliases, 03_Contacts, 04_EntityRoles, 90_MasterIndex). 10 formulas injected into tblMasterIndex; all verified in OOXML. |
| 2 | 2026-02-25 | User clarified: on Win10 Claude Desktop app, wants 90_MasterIndex formulas correctly written | No change to approach. Implementation proceeded. |

---

## Architecture Reference

| Sheet | Table Name | Key |
|-------|-----------|-----|
| 01_Entities | tblEntities | Entity_ID (PK) |
| 02_Aliases | tblAliases | Entity_ID (FK) |
| 03_Contacts | tblContacts | Entity_ID (FK) |
| 04_EntityRoles | tblEntityRoles | Entity_ID (FK) |
| 90_MasterIndex | tblMasterIndex | Entity_ID (formula-driven) |

## Build Command

```bash
pip install -r requirements.txt
python build_workbook.py
```

Output: `workbook.xlsx`

## Ongoing Change Workflow

All changes go into `build_workbook.py` — then `python build_workbook.py` to regenerate.
Never hand-edit the `.xlsx` directly.
