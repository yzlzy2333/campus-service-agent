# Changelog

## 0.2.0 - 2026-11-19

### Fixed

- Preserve material-check results while answering additional requests for a location, application entry, opening hours, fees, or processing time in both offline and live modes.
- Retrieve missing sections from the full guide and explicitly report unavailable information.
- Require inline references for every model-generated sentence and reject unused, unknown, or incomplete reference sets.
- Check requested-section coverage and selected fee, duration, time, and URL literals against the evidence cited by each sentence.

### Added

- Seven focused regression tests for mixed requests and citation validation.
- Shared deployment and regression CI for Windows, Ubuntu, Intel macOS, and Apple Silicon macOS.
- Full frozen regression checks and dependency consistency checks in CI.
- Deployment branch maintenance instructions.

### Validation

- Local guide audit passed 962/962 checks across 90 services.
- Frozen offline regressions passed 342/342 RAG runs and 294/294 full-guide runs.
- Simulated HTTP checks passed 12/12, retrieval hit 96/96 expected passages, and all seven reliability tests passed.
- Live sampling and native CI validation are being recorded separately as they complete.
- Literal checks and citation structure validation do not establish semantic entailment. Human review is required for semantic accuracy.
