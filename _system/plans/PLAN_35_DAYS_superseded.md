# SW-SYS-08  -  Execution Plan, 35 Working Days (withdrawn)

> **WITHDRAWN 2026-10-22.** This plan priced work that turned out to be one afternoon each.
> The executed plan is `plans/PLAN_5_DAYS.md`. This file is kept as history so the estimate
> error stays visible; it is not a commitment.

| Field | Value |
|---|---|
| Document ID | SW-SYS-08 |
| Kind | System record (internal; not published) |
| Version | 2.1 |
| Status | Withdrawn; kept as history |
| Date | 2026-10-23 |
| Basis | Decision D-8: the 90-day plan is withdrawn; the required work is definition and packaging |
| Capacity assumption | 10 to 15 hours per week |
| Normative status | Informative; gate criteria are binding |

## 1. Planning principle

The 90-day plan assumed that the domain model had to be invented and validated from first
principles. The capability audit shows otherwise: the graph machinery exists and is tested,
and the missing work is vocabulary, packaging, and one honest measurement. The calendar is
therefore 35 working days. If capacity falls, the calendar extends; gate criteria MUST NOT
be relaxed.

## 2. Work completed before day 1

| Item | Reference |
|---|---|
| Capability audit complete | SW-SYS-02 |
| Evidence register complete for available sources | SW-03 |
| Asset inventory complete | SW-SYS-04 |
| Programme separated onto an isolated branch and worktree | Project overview, section 6 |
| Decisions D-1 to D-8 recorded | Project overview, section 3 |

## 3. Phases

| Phase | Days | Deliverable | Exit gate | Termination |
|---|---|---|---|---|
| P0 Definition and packaging | 1 to 5 | Specification frozen: six physical axes plus propagation, information, institutional and catalyst layers (SW-09), six damage patterns, sixteen unsafe control actions, eighteen gate codes, release schema, licensing split | B0: a third party predicts four of five sample verdicts | Two or more incorrect predictions indicate an ambiguous specification; rewrite before code |
| P1 Gate v0 | 6 to 15 | Lane dataset, deterministic checker, twenty gold cases | B1 loads and validates; B2 twenty of twenty agree with an identical hash across three runs | Open data insufficient: use a documented synthetic set. Unstable hash: stop |
| P2 Event-agnostic stress | 16 to 28 | Event generator over all layers, remedy menu, cascade with reproduction number, comparison against a greedy baseline | B3 unseen vectors execute with no event-name branch; B4 measured on the pre-registered rule (SW-08): 15 percentage points fewer unsafe control actions or 10 per cent fewer excursion minutes, paired, 95 per cent CI, with a block-rate guard | Event-name branch required: return to P0. No separation: release as plan auditor |
| P3 Release | 29 to 35 | Specification under Apache-2.0, reference implementation under the Business Source Licence, five-minute demonstration, one published article with the measured numbers | B5 one external reproduction of the same hash | A release that cannot be reproduced is not a release |

## 4. Phase P0 detail

No code is written in this phase. The objective is a frozen vocabulary.

| Day | Output | Completion criterion |
|---|---|---|
| 1 | Vocabulary: plan, leg, release, condition, finding, severity, verdict | Each term defined once with a single-sentence definition |
| 2 | Event axes, plus conversion of three named events into six-axis vectors | Named events appear only as data |
| 3 | Damage patterns with measurable thresholds | Each pattern states signal, unit, threshold source, consequence |
| 4 | Unsafe control actions, gate codes, release schema | Every code maps to at least one action; every action maps to at least one code |
| 5 | Gate B0 review with an independent reader | Four of five predictions correct |

Explicitly out of scope in P0: solvers, mathematical programming, thermal model refinement,
and user interface work.

## 5. Working rules

1. Determinism takes precedence over features. A non-reproducible result invalidates
   everything downstream.
2. Thresholds are data. They reside in `config/*.json` and are read by code.
3. Deterministic tasks are not delegated to language models.
4. A missing field produces a blocking finding, never a default value.
5. Text under `**` is English and free of decorative notation.
6. Production source code is not modified from this branch without an approved proposal and
   a corresponding test.
7. Arithmetic in the gate and the planners is integer micro-units and integer minutes
   (SW-10). Floating point is confined to transport and reporting.


## 6. Definition of completion

Gate B5 is satisfied when an independent party clones the repository, runs one command on a
machine without a graphics processor and without credentials, obtains the same release hash,
and can explain the verdict within five minutes.

It does not imply commercial adoption, regulatory acceptance, or protection of a shipment.
Those are separate claims and are not made by this programme.

## 7. Justification for the 35-day calendar

| Work item | State before day 1 | Remaining effort |
|---|---|---|
| Graph machinery | Exists and tested | None |
| Deterministic core and harness pattern | Exists in the adjacent programme | Reuse only |
| Gates as data and audit trail | Exists | Adapt thresholds |
| Vocabulary, codes, release format | Does not exist | P0, five days |
| Lane dataset, checker, gold cases | Does not exist | P1, ten days |
| Event generator and measurement | Does not exist | P2, thirteen days |
| Packaging, licence, demonstration | Does not exist | P3, seven days |
