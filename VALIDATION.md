# Validation record

Date: 2026-11-19

## Final local regression

| Check | Result |
| --- | --- |
| Guide coverage | 962/962 across 90 services |
| Frozen RAG runs | 342/342 |
| Frozen full-guide runs | 294/294 |
| Simulated HTTP runs | 12/12 |
| BM25 expected passages | 96/96 |
| Focused reliability tests | 8/8 |

The original guide and case fingerprints are preserved. A new regression covers recovery from an uncited model answer through the normal live entry point using a simulated HTTP transport.

## Live diagnostic sample

The diagnostic sample used the actual DeepSeek API, with the response model reported as deepseek-flash. It covered A1, B1, and F01-F08, each repeated three times in RAG mode.

| Measurement | Value |
| --- | --- |
| Distinct cases | 10 |
| Scenario runs | 30 |
| Conversation turns | 57 |
| HTTP calls | 118 |
| Input tokens | 215510 |
| Output tokens | 16839 |
| Per-turn median latency | 2260.88 ms |
| Per-turn P95 latency | 3130.2 ms |
| Runs passing automated prechecks | 11/30 |
| Turns rejected by evidence validation | 16/57 |

This sample tested the intermediate strict-validation implementation. It exposed incomplete inline citations, missing full-guide reads for fee questions, and unlogged initial topic searches. The final implementation adds source-text recovery, checks the full guide for missing requested details, and records initial topic searches. All final local regressions pass after these corrections.

The diagnostic sample is retained as failure evidence. These measurements do not describe final-version live accuracy. Full 117-case live acceptance requires authorization to send the public simulated prompts and guide excerpts to DeepSeek and use API credits. Semantic task success and citation support have not been fully reviewed.

Run the acceptance suite with the existing DEEPSEEK_API_KEY environment variable:

~~~sh
python -m evaluation.run --live --repeat 1 --out evaluation/acceptance-live.json
python -m evaluation.review evaluation/acceptance-live.json --labels evaluation/acceptance-labels.json --template
~~~

Each completed live scenario is saved atomically, and progress includes the case, mode, and repetition. Fill the review labels against the original guides and tool arguments, then run the review command without --template. Keep credentials and raw logs local.

## Native deployment checks

Shared CI runs on Windows, Ubuntu 24.04, Intel macOS, and Apple Silicon macOS. Each job installs Python 3.12 dependencies and verifies dependency consistency, startup, guide coverage, focused reliability checks, and the full frozen regression suite. Deployment branches also exercise their setup and launch scripts.

Inspect [GitHub Actions](https://github.com/yzlzy2333/campus-service-agent/actions) for the exact commit and platform results. Release archives contain source and deployment instructions. Python and dependencies are installed on the target machine.
