# SW-07  -  Licensing Model and Legal Position

| Field | Value |
|---|---|
| Document ID | SW-07 |
| Kind | Repository document (published) |
| Version | 2.0 |
| Status | In force from the first public distribution |
| Date | 2026-10-23 |
| Normative status | Informative; threshold values are held in the registry |

## 1. Structure

The programme produces three artefacts with different purposes. Treating them as one entity
either forfeits the commercial position or discourages adoption.

| Artefact | Licence | Purpose |
|---|---|---|
| Specification: vocabulary, gate codes, unsafe control actions, release schema | Apache-2.0 | Enable citation and independent implementation. A standard that is not freely available is not a standard |
| Reference implementation: checker, simulator, replay | Business Source Licence 1.1 with an Additional Use Grant | Free for parties who cannot pay; licensed for parties who can |
| Names and marks | Trademark policy; no licence granted | Prevent a derivative from representing itself as a certified implementation |

## 2. Business Source Licence 1.1 configuration

Three fields require deliberate configuration.

| Field | Value | Effect |
|---|---|---|
| Additional Use Grant | Production use permitted without charge for individuals, research and teaching, non-profit organisations, and companies with annual revenue below USD 5 million and fewer than 100 employees | Small users require no commercial contact |
| Change Licence | Apache-2.0 | The licence that takes over on the Change Date |
| Change Date | Two years after the first public distribution of each version | Shorter than the legal maximum of four years, chosen for adoption speed |

Use outside the grant requires a commercial licence. This includes large organisations and
any party offering the software as a competing managed or hosted service.

### Why two years, and why four is the ceiling

The Business Source Licence 1.1 text makes the four-year limit unconditional. The
grant converts "effective on the Change Date, or the fourth anniversary of the
first publicly available distribution of a specific version of the Licensed Work
under this License, whichever comes first". A Change Date beyond four years is
therefore inert: conversion happens at four years regardless, and publishing a
later date would misstate the terms.

The Change Date is two years. Two years is inside the limit, and it matches the stated
objective: reputation and adoption rather than revenue. Four years remains the maximum, not
the chosen value.

Longer protection is available by two legitimate routes, neither of which requires
stretching the date.

1. Per-version clocks. The same clause applies the licence separately to each
   version and states that the Change Date may vary per version. Every new release
   starts its own clock, so the current version is protected for the full chosen
   term without any change to the terms.
2. A different licence. If a version must never convert, the Business Source
   Licence is the wrong instrument; PolyForm Shield 1.0.0 has no automatic
   conversion. That route is recorded as the fallback, not as a way to amend this
   one.

Two commitments keep the position credible in a procurement review. Both are
policy, not licence text.

1. No retroactive extension. A published Change Date will not be pushed back for
   that version.
2. No restriction added to the Additional Use Grant. Thresholds may be widened,
   never narrowed, for a version already published.

The exact wording was verified against the canonical licence text published by
SPDX (BUSL-1.1) and MariaDB. The relevant sentence is quoted above.


### Threshold rationale

Revenue and headcount are used rather than fleet size. Fleet size is trivially restructured
through subcontracting and cannot be verified from public filings. Revenue and headcount are
the two tests used by the PolyForm licences, which makes the threshold recognisable to a
procurement review.

Threshold values are data, not code. The free tier is defined by the three values in section 2
(annual revenue, headcount, and the excluded use), and they are held in configuration so the
licence text and the enforcement cannot drift apart.

## 3. Alternatives assessed

| Option | Advantage | Reason not selected |
|---|---|---|
| Business Source Licence 1.1 with Additional Use Grant | Free below threshold, licensed above, and becomes open source on a published date | Not an open source licence while in force; MUST NOT be described as open source |
| PolyForm Small Business 1.0.0 | Prepared legal text; free below 100 people and USD 1 million revenue | Fixed threshold with no change date; never becomes open source, weakening the reputational objective |
| PolyForm Shield or Perimeter | Explicit non-compete wording | Reads as hostile to the intended audience; better used as a clause inside a commercial licence |
| GNU Affero General Public Licence 3.0 | Strong copyleft for hosted services | Routinely rejected by infrastructure buyers and incompatible with a free tier for small users |

Fallback rule: if the Business Source Licence text or the threshold proves impractical with
an actual customer, migrate to PolyForm Small Business. Both are recorded in the registry, so
the change does not affect code.

## 4. Positioning

The programme states its position explicitly:

## 5. Reimplementation risk

Copyright protects the expression of software, not the idea or the behaviour. A third party
that writes an independent implementation from the published specification commits no
copyright infringement, and no licence text prevents this.

The programme therefore assumes independent implementation will occur and treats it as
adoption, with the following consequences.

| Measure | Effect |
|---|---|
| Publish the specification deliberately | Reimplementation extends the standard |
| Offer conformance testing and certification | Value lies in proving compatibility, not in concealment |
| Retain the operational advantage in data, scenario packs, and integration | These are not derivable from a specification |
| Include a patent grant with a retaliation clause in the commercial licence | The only effective instrument against copying a genuinely novel mechanism; use sparingly |
| Price the commercial licence below the cost of an independent reimplementation | Two engineering teams plus legal review over several months exceed a reasonable licence fee; an economic barrier rather than a legal one |
| Apply a trademark policy | A derivative may exist but may not describe itself as certified |

No claim is made that the idea is protected. These measures protect the name, the
certification, and the commercial position.

## 6. Execution checklist for gate B5

1. `LICENSE` with completed Additional Use Grant, Change Licence, and Change Date in the
   reference implementation.
2. `LICENSE` under Apache-2.0 and a `NOTICE` file in the specification.
3. SPDX identifiers in every source file header.
4. `COMMERCIAL.md` stating who requires a licence, how to obtain one, and the price tiers.
5. `TRADEMARK.md` stating what may and may not be described as certified.
6. `CONTRIBUTING.md` with contribution licence terms; without these, contributions cannot be
   relicensed at the Change Date.
7. A plain-language summary in the project overview stating what may be done without payment.
8. Threshold values verified against the registry.

## 7. Limitations of the licence

A passing verdict is not evidence of product safety, regulatory approval, or legal fitness
for carriage. The licence grants software rights only and certifies nothing about cargo. The
release document states this limitation.


1. The source is public.
2. Individuals and small organisations may use it in production without charge.
3. There is a published date on which each release becomes open source.
4. While the Business Source Licence applies, the software is described as source-available,
   not as open source.

The definition of any positioning label MUST be re-verified at publication time rather than
cited from memory.
