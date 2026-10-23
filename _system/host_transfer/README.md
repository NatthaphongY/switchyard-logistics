# Host transfer record

| Field | Value |
|---|---|
| Document ID | SW-SYS-TRANSFER |
| Kind | System record |
| Status | internal, closed 2026-10-23 |
| Scope | provenance of the extraction; not part of the published artefact |

The research programme was extracted from a host repository on 2026-10-23 (D-23). The host copy
was a full copy of that repository, 318.1 MB against 1.5 MB for this tree. Before the copy was
deleted, its uncommitted state was captured here, because that state existed nowhere else.

## What is here

| File | Contents |
|---|---|
| `clone_uncommitted.patch` | Binary patch of every tracked change in the host copy against its own HEAD (`8c4d712a`). |
| `clone_untracked.tar.gz` | The eight files that were untracked there, at their original paths, archived rather than stored as text: a copy of a host document is not a document of this repository, and the separation gate reads every text file in the tree. |
| `copy_orphans.tar.gz` | **Not in this repository.** Twenty files that state written inside the copy left behind: approval records, ledger databases, a release pack and one test log. Absent from the host repository and from every commit, so nothing else carries them. Moved out on the owner's instruction of 2026-10-23; `manifest.json` keeps the digest of the archive as it left, so any copy can be verified against this record. |
| `manifest.json` | HEAD, branch, the two stashes, a SHA-256 for each of the 58 status entries, the contents of both archives, and the account of the move. |

## Why this was needed

The host copy sat on branch `research/eda-coldchain` at commit `8c4d712a`, one commit ahead of
its `master` (`4bd94a14`). Its refs were identical to the host repository's refs, so no commit
existed only there. Its working tree, however, held 58 uncommitted paths: 50 tracked
modifications and renames, and eight new files. The eight guard test modules and the research
tree itself were copied into this repository, but the copies were rewritten for the new root,
so the pre-rewrite bytes are kept here as the record.

## How the deletion was cleared

Three questions, each answered before the copy was removed.

1. **Did the copy hold a commit the host repository does not?** No. All 147 refs in the copy,
   including the two stashes, the tag and the tool checkpoints, resolve to objects present in
   the host repository with the same ids.
2. **Did its working tree hold tracked changes nothing else carries?** They are in the patch,
   path by path, with a hash each.
3. **Did it hold files that were never committed at all?** Twenty, listed above. Everything else
   written inside the copy after it was made either matched a file in the host repository, or
   matched its own committed blob, or is one of the eight recorded in the untracked archive.


## Where the orphan box is kept

The box is state of the host side, not work of this repository, so it lives outside the tree: in
the folder `switchyard_host_transfer_20261023` in the machine's backup area, beside its own short
README. The record stays here, which is the part that matters: the twenty paths, their sizes, a
SHA-256 for each, and the digest of the archive itself
(`4c119463baf1ebeb508e898ff946399a898c5a7d49d29729ae8c45f2a9e740ec`, 10,039 bytes). A copy found
anywhere can be checked against that digest without trusting where it came from.

## How to read the patch

```text
git apply --check --reverse _system/host_transfer/clone_uncommitted.patch   # inside a host copy
git apply --stat _system/host_transfer/clone_uncommitted.patch
```

The patch is against a tree whose paths are prefixed with `research/`. It does not apply to this
repository, and it is not meant to: it is provenance, not a change set.

## Cross-check

`manifest.json` records the commit the patch applies to. The host repository at
`4bd94a14` holds the same commit object and the same branches, tags and stashes, so the commit
graph and the stashes survived the deletion without a copy here.
