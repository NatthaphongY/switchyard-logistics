# Changelog

All notable changes to the switchyard project will be documented in this file.

The format is based on Keep a Changelog, and this project adheres to Semantic Versioning.

## [3.2.0] - 2026-10-23

### Added
- Standalone repository separation from internal research tree.
- Zero-dependency Rust replay core (`switchyard-core`) achieving 29,653 evaluations per second.
- Gate B4 benchmark measurement harness and validation scripts.
- Bit-exact parity verification suite covering 300 pre-registered scenarios across Python and Rust.
- Ambient climatology physical layer backed by frozen July 1991-2020 ERA5 reanalysis datasets.
- 20-code event-agnostic compliance gate specification (SW-06).

### Changed
- Refactored numeric core to strict integer fixed-point arithmetic (micro-units and integer minutes).
- Updated dual-licensing structure: Apache-2.0 for specification documents and BSL 1.1 for implementation code.

### Security
- Automated research sanitization gate proving zero leaked credentials, private paths, or internal tokens.
