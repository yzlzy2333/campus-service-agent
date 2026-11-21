# Changelog

## Unreleased - 2026-11-21

### Documentation

- Added an explicit Windows, Linux, and macOS support overview to the README.
- Included deployment links for each operating system and documented Intel and Apple Silicon support on macOS.
- Clarified Python 3.12 requirements, source deployment packages, and the environments covered by CI.
- Synchronized the platform overview and changelog across main, deploy/linux, and deploy/macos.

## Unreleased - 2026-11-20

### CI environment recovery

- Diagnosed macOS ARM64 failures as GitHub hosted runner capacity constraints. The cancelled jobs had no assigned runner and executed no test steps.
- Retried the affected main and macOS 26 verification jobs. Both workflows succeeded on attempt 2, and the existing branches were retained.
- Preserved commit IDs, workflow links, error details, and recovery results in [CI_ENVIRONMENT_LOG.md](CI_ENVIRONMENT_LOG.md).

### Fixed

- Prevent material checks from treating explicitly absent documents as provided, including negation before or after a material name and later corrections in the same message.
- Compare complete numeric facts against cited evidence so a source fee of 120 does not validate a claimed fee of 20, and a duration of 21 days does not validate 1 day.
- Create missing parent directories for CLI session logs and report inaccessible log paths as argument errors before starting a conversation.

### Validation

- All 11 reliability tests passed, including three new regressions for negated materials, partial numeric matches, and nested log paths through the CLI.
- The frozen guide and case data are unchanged. Full offline and simulated HTTP regression results are recorded in VALIDATION.md.

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
