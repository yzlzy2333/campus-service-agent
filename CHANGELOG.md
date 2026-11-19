# Changelog

## 0.2.0 - 2026-11-19

### Fixed

- Preserve checked materials while answering additional requests for locations, application entries, opening hours, fees, and processing times.
- Retrieve missing sections from the full guide and explicitly report unavailable information.
- Require inline evidence for each model-generated sentence, check requested-section coverage, and reject unsupported fee, duration, time, and URL literals.
- Recover from invalid model citations with guide text and retain the validation failure in the diagnostic log.
- Record initial topic searches and check the full guide before reporting missing fee or timing information.

### Added

- Eight reliability regression tests, including recovery through the live entry point.
- Shared CI for Windows, Ubuntu, Intel macOS, and Apple Silicon macOS, including the frozen regression suite.
- Atomic live-evaluation checkpoints, per-scenario progress, and configurable repetition counts.
- Deployment branch maintenance instructions and a validation record with actual live diagnostic measurements.
- Versioned source deployment archives for Windows, Linux, and macOS.

### Validation

- Local checks passed 962/962 guide checks, 342/342 RAG runs, 294/294 full-guide runs, 12/12 simulated HTTP runs, 96/96 expected retrieval passages, and 8/8 reliability tests.
- A 30-run, 57-turn DeepSeek diagnostic sample exposed evidence-validation failures in an intermediate implementation. Final corrections passed local regression.
- Final-version full live acceptance and semantic grading remain pending. See [VALIDATION.md](VALIDATION.md) for sample measurements and scope.
