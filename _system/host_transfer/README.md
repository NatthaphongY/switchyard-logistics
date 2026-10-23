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
| `clone_untracked/` | Byte copies of the eight files that were untracked there, at their original paths. |
| `manifest.json` | HEAD, branch, the two stashes, and a SHA-256 for each of the 58 entries. |

## Why this was needed

The host copy sat on branch `research/eda-coldchain` at commit `8c4d712a`, one commit ahead of
its `master` (`4bd94a14`). Its refs were identical to the host repository's refs, so no commit
existed only there. Its working tree, however, held 58 uncommitted paths: 50 tracked
modifications and renames, and eight new files. The eight guard test modules and the research
tree itself were copied into this repository, but the copies were rewritten for the new root,
so the pre-rewrite bytes are kept here as the record.

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
