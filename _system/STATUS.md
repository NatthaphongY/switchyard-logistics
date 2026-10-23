# SW-SYS-06  -  Status of the programme (internal)

| Field | Value |
|---|---|
| Document ID | SW-SYS-06 |
| Kind | System record (internal; not published) |
| Version | 1.0 |
| Status | Active |
| Date | 2026-10-23 |

## 1. Where the work stands

| Item | State |
|---|---|
| Workstream B (logistics) | Complete through gate B4; the gate separates on six pre-registered criteria |
| Workstream A (EDA) | Suspended, unstaffed, not part of any release |
| Published tree | De-branded: no document prefix, module name, crate name, environment variable, or host path that points back to the publisher |
| Document split | Repository documents and system records are separated by directory and enforced by `tests/test_doc_separation_s.py` |
| Ambient layer | Frozen July 1991-2020 ERA5 climatology, three measured sites plus a synthetic profile for replay |
| Public release | Not prepared |
| Separation | Done 2026-10-23 (D-23): standalone repository with its own test suite, and the ten guard modules travel with it |
| History | Grafted 2026-10-23 (D-25): `8c4d712a` is an ancestor of this branch through a root commit whose tree is its `research/` subtree, so the earlier work keeps its author, date and message |
| Host copy | Deleted 2026-10-23 after three checks; 318.1 MB returned. Its uncommitted work is recorded in `_system/host_transfer/`, and the commit it held remains in the host repository |
| Licence | Deferred by the owner (question 4): no `LICENSE` file yet, holder undecided. The texts still declare Apache-2.0 for the specification and a source-available posture for the code |
| Future projects | Three candidates recorded and deferred by the owner (D-23); two further directions recorded and unscheduled (SW-SYS-09 section 8) |

## 2. Open items

1. Personal data in the host tree (two test files, two configuration files) is not scrubbed.
   Those files belong to the host production tree, which this repository must not modify, so
   the decision is the owner's: scrub in place, move them to an ignored path, or accept them.
2. No live forecast ingest. The seam exists (`weather.active_profile`, `SW_WEATHER_PROFILE`);
   only the snapshot is frozen.
3. Rust conformance was re-run after the module and crate rename: 300 exported instances,
   eight threads, 200 repeats, zero mismatches at 26,956 instances per second, and a replay
   of five exported scenarios with zero mismatches. The evidence files still describe the
   pre-rename binary, so the numbers in them are unchanged and still true.
4. This repository's own suite is green from the new root: 113 tests across the ten guard
   modules, run on 2026-10-23 after the move. The host suite is a separate matter and was never
   the gate; the commands are in `README.md` section 7.
5. Separation is closed as of 2026-10-23 (D-23, D-25). The earlier commit is an ancestor, the host
   copy is deleted, and its uncommitted work is recorded in `_system/host_transfer/` with a hash
   for every path. What is left from that batch is the licence (question 4).
6. Duplication was measured before the deletion, not assumed: the copy held 147 refs that all
   resolved to objects the host repository holds, 58 uncommitted paths (recorded), and 37 files
   written inside it after it was made, of which nothing but the 20 now archived carried their
   bytes. The file-level rule in SW-SYS-09 section 4 now applies to anything this repository holds
   but does not own.
7. The three candidate projects are deferred by the owner (D-23). Two further directions are
   recorded and unscheduled: re-entry of a mechanism into the host system, and repair of the
   pain points reported there. Section 8 of SW-SYS-09 states why the two cannot be pursued by
   copying files back.
8. Re-verification from the new root on 2026-10-23: export, gate B4 and the stress harness were
   all run again. `evidence/instances.txt` came back byte-identical, gate B4 returned SEPARATES
   with six of six pre-registered criteria and the same headline figures, and the harness passed
   bit-exact parity. Throughput measured faster on this machine (29,653 per second from the
   release binary, 37,475 from the harness) and is machine-dependent by design, so the evidence
   files were left as published instead of being overwritten by a speedier run.

## 3. Next review

Features, security, and code quality are the next pass. Order matters: security before
features, because a feature added on an unreviewed surface is a feature that has to be reviewed
twice.
