# Maintaining deployment branches

Business logic, guide data, dependency versions, and regression checks are maintained on `main`. Linux and macOS branches contain their platform launcher and installation instructions.

After a shared fix passes CI on `main`, merge that commit into both deployment branches. Preserve each branch's platform-specific `README.md` and `deploy.sh` when resolving conflicts. Run the shared regression workflow on the resulting commits before publishing a release.

The workflow verifies Python 3.12 installation, dependency consistency, startup, 90-guide coverage, the frozen regression suite, and focused reliability checks. The macOS matrix includes Intel and Apple Silicon. Inspect the individual jobs when a runner remains queued or a workflow is cancelled.

Record changes and measured results in `CHANGELOG.md`. A release must identify which platforms completed verification. Keep raw session logs and credentials local. Publish aggregate live measurements with the sample size, model, environment, and human review status.

For live acceptance, use the commands in `OPERATIONS.md`. Review every sampled task against its guide and tool parameters before reporting semantic accuracy. The deterministic citation checks cover inline references, requested sections, and selected literal facts. Human review is still required for paraphrased claims and contradictions.
