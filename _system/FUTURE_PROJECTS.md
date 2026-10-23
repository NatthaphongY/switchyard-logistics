# SW-SYS-09  -  Work after this one (system record)

| Field | Value |
|---|---|
| Document ID | SW-SYS-09 |
| Kind | System record (internal; not published) |
| Version | 1.1 |
| Status | Task A executed 2026-10-23. Tasks B to D recorded, not started |
| Date | 2026-10-23 |
| Machine record | `programme.json -> future_projects` |
| Scope | Separation of the tree, removal of duplication, and the three candidate projects that would join this one |

## 1. Why this file exists

The owner recorded a direction on 2026-10-23 that is not yet work: this tree becomes a
standalone open-source project, the parts that duplicate the host system are deleted, and
three further projects may join it, making four. The direction was given as a note for
later, so nothing here is scheduled. This file exists so that the reasoning is not lost
and so that the next session does not re-derive it.

Nothing in this file is a decision. The name of the family is not chosen, and the three
candidates may not be built in the order listed.

## 2. The boundary, stated once

The host system is a private production system for books. This tree must not depend on it,
must not describe it, and must not carry a token that points back to it. That boundary is
already enforced for published documents by `tests/test_doc_separation_s.py`. Two
consequences follow, and they are the reason for the first task below:

1. A repository that lives inside the host tree is not actually separate. The separation is
   a physical move to its own repository with its own licence file, not a folder name.
2. Work that touches the host system's intellectual property is out of scope for every
   project listed here. Creative, literary, and story-analysis work is not part of this
   family and stays in the private tree permanently. It is not a candidate, it is not a
   later phase, and it is not mentioned in any published document.

## 3. Task A: separate the tree

| Step | Detail |
|---|---|
| 1 | Move `` to its own directory outside the host tree, and start its history there |
| 2 | Keep `_system/` in the new repository; it is internal but it is not host material |
| 3 | Give the repository one licence for code and one for the specification, as recorded in D-2 |
| 4 | Re-run every gate from the new root: `README.md` section 7, then the Rust replay |
| 5 | Publish only the paths listed in `PACKAGE.md` |

A move breaks every path that is written down, so step 1 is a batch of replacements
followed by one full test run. Doing it half way is worse than not doing it.

### Executed on 2026-10-23

| Step | Result |
|---|---|
| Copy | 66 files copied, not moved. `__pycache__`, `.pytest_cache` and `engine/target` were left behind as machine state; the first two are caches and the third is Cargo output |
| Root | The new root is the tree itself, outside the host directory. The original folder still holds the only other copy until section 4 step 6 |
| Gates | Ten guard modules carried across. Their root expression was `parents[1]` plus the old prefix; it is now `parents[1]` alone, so the modules resolve to the new root without a special case |
| Paths | Every written path rewritten. The replacement required a delimiter check rather than a plain search, because `web_research` contains the same letters and must not be touched |
| Records | The registry rule set named the host layout in `write_scope` and `read_only_paths`. Neither path is reachable from the new root, so the scope became `repository/**` and the read-only list became empty. A rule that names an unreachable path is worse than no rule: it reads as a guarantee |
| Licence files | Written on 2026-10-23 (D-26), after the owner settled the holder. `LICENSE` is BUSL-1.1 with the holder named on the Licensor line, Change Date 2028-10-23 and Change License Apache-2.0; `LICENSE-SPEC` is the Apache-2.0 text verbatim. Both were taken from the SPDX licence list rather than retyped, and the record holds a digest of each. The holder is one natural person publishing as an individual, so the tree carries one personal name, on one line, in two files |
| History | Not transferred. The new repository starts from the copied state. The host commit and the uncommitted work still exist only in the original folder, so the folder must not be deleted before step 3 of section 4 |

## 4. Task B: delete what duplicates the host tree

The owner's reason is disk and attention, not tidiness: duplicated files are maintained
twice and drift. The rule is one owner per file.

The measurement below corrects the framing of this section: the duplication is the holding
folder, not the files inside the tree. The tree is 2.1 per cent of that folder, and the folder
is the host repository copied. So Task B is one deletion, after the sequence at the end of this
section, and the file-level rule below applies afterwards, to anything the new repository holds
but does not own.

| Class | Action |
|---|---|
| A file with an identical counterpart in the host tree | Delete the copy here; the host copy stays |
| A file that exists here because the host tool wrote it (caches, build output, generated tables that can be rebuilt) | Delete and add to the ignore list |
| A file that is a genuine second implementation (the Rust core, the Python reference) | Keep both; the pair is the conformance claim |
| A document that summarises host material | Delete; it is either published material or it is host material, and it cannot be both |

A hash comparison across the two trees produces the candidate list. Nothing is deleted on
the strength of a filename alone.

### Measured on 2026-10-23, so the task is not estimated

| Measurement | Value |
|---|---|
| The folder that holds this tree | A git repository of its own, 318.1 MB, 10,485 files, 9,799 tracked |
| This tree | 112 files, 6.8 MB, which is 2.1 per cent of the folder |
| Relationship to the host repository | The two histories share a base; this repository is exactly **one commit ahead** and **zero behind** |
| That commit | `8c4d712a`, 69 files: 40 tree files and 10 guard test modules under the host `tests/` |
| Uncommitted work | 58 paths, all inside the tree or a guard test |

So the duplication is not partial: apart from one commit, this folder **is** the host
repository, copied. Ninety-eight per cent of the bytes are a second copy of something that
already exists elsewhere. That is the disk the owner asked to reclaim.

### The two traps, in order

1. **Deleting the folder deletes the only copy of one commit and of all uncommitted work.**
   The commit is not lost if it is preserved first: it exists as an object in the host
   repository, but no branch there points at it. The uncommitted work exists only on disk.
2. **Ten guard modules live outside the tree.** They are the programme's gates, but they
   sit in the host test directory, so a prefix-only extraction cannot see them: they would
   be lost with the folder while the extracted repository has no gates of its own. They must
   be carried across and have their root paths adjusted.

### Sequence that does not lose anything

| Step | Command or action | Why this order |
|---|---|---|
| 1 | Commit the uncommitted work, or copy the tree aside first | It exists nowhere else |
| 2 | Carry the ten guard modules across, adjusting their root path | A prefix split cannot see files outside the prefix |
| 3 | `git subtree split --prefix=research -b research-only` in the host clone | Produces a branch whose history contains only this tree |
| 4 | Clone that branch into the new directory, add the licence files | History is preserved; the new repository never sees host commits |
| 5 | Run every gate from the new root, then the Rust replay | A move breaks written paths; this is where they are found |
| 6 | Only then delete the 318 MB folder, after confirming the host repository is intact | Deletion is the last step, never the first |

## 5. Task C: the three candidates

Recorded as given, with one correction each, because the reason to write this file down is
to keep the difference between what exists and what is hoped for.

### 5.1 `flow-core`  -  graph and causal invariants

| Field | Value |
|---|---|
| Claim | One dependency-free library that answers three questions about a dependency graph: is there a cycle, where is the bottleneck, which tasks cannot slip |
| Exists today | Maximum flow with a minimum cut certificate, Edmonds-Karp, `src/switchyard/graph.py`, 168 lines. Also a min-cost flow and a shortest path over the same residual construction |
| Does not exist | Cycle and paradox detection as a public function; critical path with slack and float; any notion of a task graph as opposed to a flow network |
| Effort | Moderate. The hard part is the failure message, not the algorithm: a cycle report has to name the nodes that close the loop |
| Audience | Backend, platform, data, and CI engineers. The widest of the three |
| Name check | `flow-core` is free on the Python Package Index and taken on crates.io, so the Rust crate needs a different name or a suffix |

### 5.2 `exact-sim`  -  bit-exact fixed-point replay

| Field | Value |
|---|---|
| Claim | Run anywhere, replay a million times, get the same state hash |
| Exists today | Most of it: integer micro-units and integer minutes throughout, a seeded generator with independent streams, canonical JSON, content hashing, and a dependency-free Rust core that reproduces the Python results on 300 exported instances across 200 repeats with zero mismatches |
| Does not exist | A general state-transition table as a public interface; the current rules are specific to this domain |
| Effort | Lowest of the three, because the arithmetic and the proof already exist. The work is to lift the domain out of the middle |
| Audience | Systems, embedded, game netcode, billing and settlement. Narrow but insistent |
| Name check | `exact-sim` is free on both registries |

### 5.3 `tda-lite`  -  practical Betti-1 detection

| Field | Value |
|---|---|
| Claim | Turn a research-grade tool into a command that reports loops in a graph or point cloud |
| Exists today | **Nothing.** The tree contains no simplicial complex, no boundary operator, no homology, and no persistence code. A search for those terms returns zero hits |
| Does not exist | All of it |
| Effort | Highest of the three. This is a new library, not a lift, and correctness is hard to test without a reference implementation |
| Audience | Quantitative research, fraud, network engineering. The narrowest, and the one where a wrong answer is most expensive |
| Name check | `tda-lite` is free on both registries |

## 6. Task D: how big is the audience, honestly

The three candidates above address pain that is real but concentrated. They share a shape:
the people who need them already know they need them, and everyone else stops reading after
the first sentence. That is a good reason to build something; it is not a reason to expect
reach.

What most developers report as their actual pain is different, and it is worth writing down
before choosing:

| Reported pain | What it means in practice | Why the candidates do not touch it |
|---|---|---|
| Review load and low-quality generated code | Volume of change rose; review capacity did not | A graph library does not read a patch |
| Pipelines that are slow for reasons nobody can name | Waiting on builds, tests, and other teams | Closest of the four: a bottleneck finder is the right instrument, but the queue is usually human rather than computational |
| Debt that grew because generation is cheap | Structure nobody holds in their head | Determinism helps reproducibility, not comprehension |
| Cloud and token cost | Spend rose faster than output | Nothing here measures cost |

The honest ordering, if reach is the objective: a tool that reduces review load, then a tool
that shortens the pipeline, then the three candidates. They are better projects if the
objective is a credible artefact for a technical audience, which is what D-7 records as the
primary objective. Both objectives are legitimate; they produce different work, and the
choice belongs to the owner.

## 7. Open questions for the owner

1. Is the objective reach, or a credible artefact for a technical audience? D-7 says the
   second. This file assumes D-7 stands until it is revised.
2. Does the family get one name with four components, or four independent projects? The
   first is easier to explain and harder to abandon one part of.
3. Build order. `exact-sim` is much cheaper than `tda-lite` and is already most of the way
   there; `flow-core` has the widest audience; `tda-lite` has the strongest claim to
   novelty.
4. What is deleted in Task B is irreversible once the repository is published. The candidate
   list needs a review before anything is removed, not after.
5. A `LICENSE` file needs a copyright holder, and the publication scrub rejects personal
   names by design. Resolved on 2026-10-23 (D-26): the holder is the person, publishing as an
   individual developer, and the scrub learned one exemption resolved by path, which a test
   pins and which is proved not to widen. The alternative - naming an entity - was not taken,
   because forming one costs time the release does not have.

## 8. Directions recorded after separation (2026-10-23)

The owner recorded a second direction in the same conversation: several things look worth
doing, namely bringing the new machinery back into the host system, and fixing pain points
that people are stuck on today. New projects come later; separation comes first. Both
directions are recorded here so that they are not lost, and neither is scheduled.

| Direction | What it would mean | What blocks it today |
|---|---|---|
| Re-entry into the host system | A mechanism from this repository used by production | The re-entry policy already in the registry: a proposal, an owner decision, and an implementation with tests, including a measured comparison against the current implementation. Not a copy of files into the host tree |
| Pain points that people are stuck on | Work chosen by observed pain rather than by novelty | Nothing here measures that pain. It is a separate workstream with its own evidence, not a phase of this one. Section 6 lists the four pains most often reported, and none of the three candidates touches them directly |
| The three candidates | Section 5 | Nothing blocks them. The owner has ordered them after separation |

One consequence deserves stating, because the two directions pull against each other: a
repository that is published openly and a repository welded into the private tree cannot both
be true at once. Re-entry has to happen as a dependency or as a ported mechanism with its own
tests, never by copying files back. Otherwise the boundary in section 2 is gone, and every
gate in this repository stops meaning anything.
