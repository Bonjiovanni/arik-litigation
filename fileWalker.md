# fileWalker.md

This is a **RECOMMENDED design/specification**, not a final locked instruction set.
Read the full spec first, then **STOP and ask me targeted clarification questions before you start coding**.
Do **not** begin implementation immediately after reading.

First, give me:
1. a short gap list of what is clear vs unclear,
2. the minimum questions needed to lock v1,
3. your recommended implementation order.

I want you to build a **Python-based file walker + first-pass triage system** that updates an Excel workbook used to manage scanning/triage of potentially useful litigation evidence files.

## CONTEXT / PURPOSE

This tool is for early litigation evidence surfacing for an initial lawsuit filing, not discovery-grade defensibility.
Priority is practical issue-spotting and efficient surfacing of likely useful files.
It should scan selected folders, record what has already been walked, avoid accidental duplicate rescans, and create/update a workbook that tracks one row per file plus run-level review outputs.

This is **NOT** a "scan everything blindly" crawler.
It must support targeted, user-selected scan roots.

## HIGH-LEVEL GOAL

Build a script that:
1. lets me choose which folders/scan roots to walk,
2. checks prior history/coverage before rescanning,
3. inventories files found,
4. records one row per file in a master inventory sheet,
5. performs cheap first-pass triage/classification/grouping,
6. records run-level summaries and review items,
7. tracks known entities and candidate new entities,
8. is designed so deeper processing can be layered later.

## OPERATING ASSUMPTIONS

- Primary environment is Windows 10.
- Primary file storage is OneDrive, rooted under:
  `C:\Users\arika\OneDrive\Litigation`
- There may also be local folders and possibly Google Drive synced folders.
- I want the script to work on ordinary Windows paths.
- Output should be an Excel workbook (`.xlsx`). Do not require a database for v1.
- Use Python.
- Use `openpyxl` unless you have a very strong reason to recommend something else.
- Prefer deterministic behavior and workbook transparency over fancy architecture.
- Keep code modular.
- Make the script production-usable, not just a sketch.

## IMPORTANT DESIGN PRINCIPLES

1. The walker is targeted, not universal.
   At runtime I should be able to choose one or more directories / scan roots.
   I should also be able to save "favorite" scan targets.

2. The script must remember what has already been walked.
   It should record path coverage and run history.

3. If I request a path already covered, the script should detect overlap and warn me.
   It should not silently rewalk already-covered paths.

4. A file can belong to multiple broad categories.
   Category assignment must be multi-label.

5. Document classification is hierarchical.
   Store:
   - `DocType` (broad)
   - `DocSubtype` (specific)
   as separate fields.

6. Entities matter.
   Anything related to known entities should be flagged.
   Newly discovered possible entities should go to a candidate list, not directly into the approved entity list.

7. The tool is for first-pass triage.
   It should surface likely useful files, not try to do full deep extraction in v1.

8. The output must be human-usable in Excel.

## WORKBOOK DESIGN

For v1, assume a single workbook containing these tabs:

1. `Walk_Targets_Master`
2. `Walk_History`
3. `Walk_Coverage`
4. `Master_File_Inventory`
5. `Entity_Master`
6. `Entity_Candidates`
7. `DocType_Master`
8. `CategoryTag_Master`
9. `Run_Summary`
10. `Run_Review_Items`

If you think any sheet should be optional or deferred, tell me before coding.

## SHEET SPECIFICATIONS

---

## 1. Walk_Targets_Master

**Purpose:**
Saved "favorites list" of scan locations I may want to choose from later.

This is **NOT**:
- a history of what has been scanned
- a to-do list
- coverage map

One row = one saved scan target.

**Suggested columns:**
- `TargetID`
- `FriendlyName`
- `PathRaw`
- `PathNormalized`
- `SourceStore`
- `DefaultRecursive`
- `Enabled`
- `PriorityOrder`
- `LastWalkedAt`
- `Notes`

**Meanings:**
- `TargetID`: stable unique ID like `T001`
- `FriendlyName`: human label
- `PathRaw`: exact entered path
- `PathNormalized`: cleaned/normalized path for comparison
- `SourceStore`: `OneDrive` / `Local` / `GoogleDriveSync` / `ExternalDrive` etc.
- `DefaultRecursive`: `Y/N`
- `Enabled`: `Y/N`
- `PriorityOrder`: menu ordering
- `LastWalkedAt`: most recent scan time for that target
- `Notes`: freeform

**Behavior:**
- Script should be able to present these as menu choices at runtime.
- User may also enter ad hoc custom paths not in this sheet.

---

## 2. Walk_History

**Purpose:**
Mechanical run log.
One row = one actual run.

Do **NOT** transpose this sheet.

**Suggested columns:**
- `RunID`
- `RunStartAt`
- `RunEndAt`
- `RequestedByUser`
- `RequestedPathsRaw`
- `RequestedPathsNormalized`
- `Recursive`
- `ScanMode`
- `OverlapStatus`
- `PriorWalkReference`
- `UserDecisionOnOverlap`
- `FilesEnumerated`
- `FilesNew`
- `FilesChanged`
- `FilesUnchanged`
- `FilesSkipped`
- `RunStatus`
- `OutputWorkbookPath`
- `Notes`

**Recommended value examples:**

`ScanMode`:
- `full`
- `incremental`
- `changed_only`
- `skip`

`OverlapStatus`:
- `none`
- `exact_match_prior_walk`
- `child_of_prior_walk`
- `parent_of_prior_walk`
- `partial_overlap`

`RunStatus`:
- `success`
- `skipped`
- `failed`

**Behavior:**
- Every run appends a new row.
- This is the authoritative run log.
- It should not be reformatted into dashboard style.

---

## 3. Walk_Coverage

**Purpose:**
Quick path-level summary of known coverage.
One row = one normalized tracked path.

**Suggested columns:**
- `CoverageID`
- `PathNormalized`
- `SourceStore`
- `LastRunID`
- `LastWalkedAt`
- `Recursive`
- `LastScanMode`
- `TotalFilesSeenLastRun`
- `CoverageStatus`
- `Notes`

**Recommended `CoverageStatus` examples:**
- `covered`
- `not_scanned`
- `partially_covered`
- `stale`

**Behavior:**
- Used for overlap checking and quick reminder of path coverage.
- Should reflect latest known coverage state per tracked path.
- Separate from full run history.

---

## 4. Master_File_Inventory

**Purpose:**
Main working tab.
One row = one file.
This is the core inventory + first-pass triage table.

**IMPORTANT:**
For location/path fields, use only these:
- `FilePath`
- `ParentFolder`
- `FileName`

Optional:
- `ScanRootPath`

Do **NOT** use `RelativePath`.
Do **NOT** use ambiguous `FullPath` naming.
`FilePath` should be the actual full usable copy-pasteable file path.

**Suggested columns:**

### A. Location / identity
- `FileID`
- `RunID_FirstSeen`
- `RunID_LastSeen`
- `FilePath`
- `ParentFolder`
- `FileName`
- `ScanRootPath`
- `SourceStore`
- `TopLevelTargetID`

### B. File metadata
- `SizeBytes`
- `CreatedTime`
- `ModifiedTime`
- `AccessedTime`
- `SHA256`
- `IsDuplicateExact`
- `DuplicateGroupID`

**Note:**
`AccessedTime` is lower priority and may be optional.

### C. Physical/source classification
- `FileFamily`
- `SourceType`
- `LikelyTextBearing`
- `LikelyImage`
- `LikelySpreadsheet`
- `LikelyDocument`
- `LikelyScreenshot`
- `NeedsOCR`
- `IsContainerType`
- `SkipReason`

**Suggested `FileFamily` examples:**
- `pdf`
- `word_doc`
- `spreadsheet`
- `presentation`
- `image`
- `email_file`
- `json_text_export`
- `archive`
- `audio`
- `video`
- `other`

**Suggested `SourceType` examples:**
- `standalone_file`
- `email_attachment`
- `embedded_attachment`
- `text_export_item`
- `derived_output`
- `unknown`

### D. Existing structured joins
These matter because I already have structured exports for email/attachments/texts.

**Suggested columns:**
- `MsgID`
- `AttachmentID`
- `AttachmentKind`
- `RelatedEmailSubject`
- `RelatedEmailFrom`
- `RelatedEmailDate`
- `RelatedEmailPDFPath`
- `RelatedTextThreadID`

### E. Cheap first-pass extraction signals
**Suggested columns:**
- `TextSample`
- `OCRSnippet`
- `KeywordHits`
- `MoneyDetected`
- `DateDetected`
- `SignatureLike`
- `HandwritingLike`
- `LogoLetterheadLike`
- `TableLayoutLike`

### F. Classification / semantics
**IMPORTANT:** separate fields for parent and subtype.

**Suggested columns:**
- `DocType`
- `DocSubtype`
- `DocTypeConfidence`
- `CategoryTags`
- `ReviewGroup`
- `PrimaryEntity`
- `MatchedEntities`
- `NewEntityCandidates`
- `EntityMatchSource`
- `EntityConfidence`

**Key rules:**
- `DocType` = broad parent class
- `DocSubtype` = most specific best-fit label
- `CategoryTags` = semicolon-delimited multi-value tags
- `MatchedEntities` = semicolon-delimited known entities
- `NewEntityCandidates` = semicolon-delimited possible new entities not yet approved

**Examples:**

`DocType`:
- `Financial document`
- `Legal document`
- `Medical communication`
- `Business correspondence`
- `Screenshot`
- `Handwritten item`

`DocSubtype`:
- `Mortgage bill`
- `Bank statement`
- `Power of attorney`
- `Provider message screenshot`
- `Insurance cancellation notice`
- `Handwritten note`

`EntityMatchSource` examples:
- `filename`
- `path`
- `text_extract`
- `ocr`
- `sheet_name`
- `cell_sample`
- `email_metadata`
- `multiple`

### G. Triage / routing
**Suggested columns:**
- `TriageScore`
- `TriageBand`
- `ReasonFlagged`
- `NextStep`
- `ManualReviewStatus`
- `KeepForCase`
- `PossibleExhibit`
- `ProcessingStatus`

**Suggested `TriageBand` values:**
- `high`
- `medium`
- `low`
- `ignore_for_now`

**Suggested `ManualReviewStatus` values:**
- `unreviewed`
- `reviewed_keep`
- `reviewed_drop`
- `needs_followup`

**Suggested `NextStep` examples:**
- `send_to_legal_doc_processor`
- `send_to_financial_doc_processor`
- `send_to_screenshot_context_processor`
- `send_to_handwriting_review`
- `send_to_property_review`
- `manual_review_only`
- `deprioritize`

**IMPORTANT INVENTORY BEHAVIOR**
- one row per file
- preserve stable `FileID` if possible
- if file seen again, update `RunID_LastSeen` and relevant metadata
- use `SHA256` for exact duplicate detection
- do not overwrite useful review fields casually if row already exists
- design update logic carefully and explain it before coding

---

## 5. Entity_Master

**Purpose:**
Approved canonical entities.

One row = one approved entity.

**Suggested columns:**
- `EntityID`
- `CanonicalName`
- `EntityType`
- `KnownAliases`
- `Status`
- `FirstSeenFileID`
- `FirstSeenRunID`
- `Notes`

**`EntityType` examples:**
- `person`
- `family_member`
- `bank`
- `insurer`
- `law_firm`
- `medical_provider`
- `business`
- `government`
- `institution`
- `trust_estate_actor`
- `other`

**`Status` examples:**
- `confirmed`
- `merged`
- `inactive`

**Behavior:**
- Used for known-entity matching during triage.
- `KnownAliases` should help map variants to `CanonicalName`.

---

## 6. Entity_Candidates

**Purpose:**
Holding pen for newly found possible entities.

One row = one candidate entity.

**Suggested columns:**
- `CandidateID`
- `CandidateText`
- `SuggestedCanonicalName`
- `LikelyEntityType`
- `SeenCount`
- `FirstSeenFileID`
- `FirstSeenRunID`
- `ExampleContext`
- `PromotionStatus`
- `MergedIntoEntityID`
- `Notes`

**`PromotionStatus` examples:**
- `pending`
- `approved`
- `rejected`
- `merged`

**Behavior:**
- Newly discovered possible entities should go here, not directly into `Entity_Master`.
- Script should increment/update candidate rows when same candidate is seen again.
- Ask me how aggressive normalization should be before coding.

---

## 7. DocType_Master

**Purpose:**
Reference table for doc types and subtypes.

**IMPORTANT:**
The decision of whether this ultimately lives in this workbook or another master file is not locked yet.
But conceptually this table must exist.

**Suggested columns:**
- `DocTypeID`
- `DocType`
- `DocSubtype`
- `ParentDocTypeID`
- `Description`
- `Active`
- `Notes`

**Behavior:**
- Support hierarchical type/subtype structure.
- Do not flatten everything into one label.

---

## 8. CategoryTag_Master

**Purpose:**
Reference table for approved category tags.

**Suggested columns:**
- `TagID`
- `TagName`
- `TagGroup`
- `Description`
- `Active`

**Examples:**
- `financial`
- `legal`
- `medical`
- `estate`
- `trustee_administration`
- `property`
- `communication`
- `business_correspondence`
- `screenshot`
- `handwritten`
- `document_image`
- `insurance`

**Behavior:**
- Category tags are multi-value and separate from `DocType` / `DocSubtype`.

---

## 9. Run_Summary

**Purpose:**
Human-facing dashboard for each run.

**IMPORTANT:**
This sheet is transposed compared to `Walk_History`.
Do **NOT** use one-row-per-run here.

Use:
- one run per column
- metrics down rows

**Suggested row labels in column A:**
- `RunStartAt`
- `RunEndAt`
- `RequestedPaths`
- `FilesEnumerated`
- `FilesNew`
- `FilesChanged`
- `FilesUnchanged`
- `FilesSkipped`
- `HighTriageCount`
- `MediumTriageCount`
- `LowTriageCount`
- `IgnoreCount`
- `PossibleNewEntityCount`
- `PossibleNewDocTypeCount`
- `NeedsManualReviewCount`
- `PossibleDuplicateCount`
- `ErrorsCount`
- `SummaryNotes`
- `OpenReviewItems`

Then each run gets its own column:
- `R0001`
- `R0002`
- `R0003`

**Behavior:**
- This is a dashboard sheet, not the authoritative log.
- It should be built from run results.
- It should be easy to read on a phone.
- The `OpenReviewItems` cell for a run should hyperlink/jump to that run's review items in `Run_Review_Items` if feasible.

---

## 10. Run_Review_Items

**Purpose:**
Detailed list of follow-up items that need review after each run.

One row = one review item.

**Suggested columns:**
- `RunID`
- `ReviewItemID`
- `ReviewType`
- `Priority`
- `RelatedFileID`
- `RelatedPath`
- `RelatedEntityCandidate`
- `RelatedDocTypeCandidate`
- `Reason`
- `SuggestedAction`
- `ReviewStatus`
- `Notes`

**`ReviewType` examples:**
- `new_entity_candidate`
- `uncertain_doc_type`
- `manual_review_needed`
- `duplicate_conflict`
- `processing_error`
- `possible_new_category`
- `low_confidence_entity_match`

**`Priority` examples:**
- `high`
- `medium`
- `low`

**`ReviewStatus` examples:**
- `unreviewed`
- `reviewed`
- `resolved`
- `dismissed`

**Behavior:**
- This should capture actionable follow-up, not just stats.
- Example:
  "3 possible new entities found" should exist both as:
  - count in `Run_Summary`
  - detailed items here

## FILE WALKING / PATH BEHAVIOR

Runtime behavior should support:
1. Choose from `Walk_Targets_Master` favorites
2. Enter one or more custom paths
3. Possibly combine both

The script should:
- validate requested paths
- normalize paths
- compare against `Walk_Coverage` and/or `Walk_History`
- detect:
  - exact overlap
  - child-of-prior-walk
  - parent-of-prior-walk
  - partial overlap
- warn me before rewalking already-covered areas

If overlap is found, script should prompt for what to do.

Recommended choices:
- `skip`
- `full rewalk`
- `changed-only`
- `continue anyway`

Log my decision.

## FIRST-PASS TRIAGE INTENT

This is not deep processing.
This is first-pass surfacing of likely useful files.

Priority is to identify and flag likely-useful evidence, especially:
- bills
- invoices
- statements
- business letters
- legal documents
- wills
- powers of attorney
- health care agent forms
- DNRs
- COLST forms
- screenshots with meaningful context
- screenshots of emails/messages/portals/accounts/transactions
- provider/medical portal communications
- handwritten items
- financial/account-related items
- property condition items if relevant

Ordinary personal photos should usually be down-ranked unless they show:
- property condition
- documents
- handwriting
- medical/care context
- financial/institutional context

## MULTI-LABEL CATEGORY LOGIC

A file can belong to multiple broad categories.
Do not use a single-category model.

Examples:
- `financial; screenshot`
- `legal; estate`
- `medical; communication`
- `business_correspondence; insurance`

## ENTITY LOGIC

Known entities:
- come from `Entity_Master`
- if matched, record in `MatchedEntities` and possibly `PrimaryEntity`

New possible entities:
- go to `Entity_Candidates` / `NewEntityCandidates`
- do not auto-promote to `Entity_Master` without review

The script should be designed so entity matching can use:
- filename
- path
- text extract
- OCR
- spreadsheet sheet names / sampled cells
- email metadata if available

## DOC TYPE LOGIC

Use both:
- `DocType`
- `DocSubtype`

Examples:
- `DocType = Financial document`
- `DocSubtype = Mortgage bill`

- `DocType = Legal document`
- `DocSubtype = Power of attorney`

- `DocType = Medical communication`
- `DocSubtype = Provider message screenshot`

## CATEGORY TAG LOGIC

Separate from doc type.
Semicolon-delimited multi-value tags.

## EXISTING STRUCTURED DATA CONTEXT

I already have substantial structured evidence layers outside this specific walker, including:
- email exports from Aid4Mail
- attachment exports/logs
- text message exports/logs
- some custom extraction processes for known document families

So this walker should be designed so files can later link into those existing structures where relevant.
Do not assume this walker is my only evidence system.

## V1 IMPLEMENTATION PRIORITIES

Recommend building in this order:
1. runtime path selection
2. path normalization and overlap detection
3. walk history logging
4. coverage updating
5. master inventory insert/update logic
6. file hashing
7. file-family classification
8. cheap first-pass signal extraction
9. entity matching + entity candidates
10. doc type / subtype and category assignment
11. run summary creation
12. run review items creation

## WHAT I WANT FROM YOU BEFORE CODING

After reading this, do **NOT** code yet.
Instead:

1. Tell me what parts of this spec are sufficiently clear for v1.
2. Tell me what parts are still ambiguous or risky.
3. Ask me targeted questions needed to lock the implementation.
4. Recommend a concrete v1 architecture:
   - file layout
   - Python modules
   - workbook update strategy
   - required libraries
5. Tell me which parts you would defer to v2.
6. Only after I answer, begin implementation.

## WHEN YOU DO IMPLEMENT

Please produce:
- a main Python script
- any helper modules
- clear dependency list
- a short README
- comments in code
- safe workbook update behavior
- clear prompt/CLI flow
- no destructive file operations
- no hardcoded assumptions that all scans are under Litigation root
- but allow OneDrive Litigation defaults where sensible

Also:
- prefer readable code over overengineered abstractions
- explain any significant design deviations from this recommendation before making them
