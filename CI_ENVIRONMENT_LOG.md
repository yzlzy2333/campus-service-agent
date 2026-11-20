# CI environment incident log

## 2026-11-20 - macOS ARM64 hosted runner capacity

### Diagnosis

GitHub's check annotations identified hosted runner acquisition failure and macOS ARM64 capacity constraints. The failed jobs had runner_id 0, no runner name, and zero executed steps. They were cancelled after approximately 15 minutes in the queue. Dependency installation, application startup, and regression tests had not started.

The runner acquisition error was "The job was not acquired by Runner of type hosted even after multiple attempts".

The same shared application code passed the macOS deployment branch's ARM64 job. A commit comparison between main and deploy/macos showed only the platform README and launcher differences. This evidence localized the reported failure to hosted execution capacity.

### Evidence and recovery

| Branch | Tested commit | Run | Initial result | Retry result |
| --- | --- | --- | --- | --- |
| main | f725727fdab04c76cf9b0cdc43af3bb130f96f26 | [44576676808](https://github.com/yzlzy2333/campus-service-agent/actions/runs/44576676808) | macos-15 cancelled before acquiring a runner | Attempt 2 succeeded |
| verify/apple-silicon | bb8772efbcf4578fbadb9261d3d3057945281a3b | [44541252115](https://github.com/yzlzy2333/campus-service-agent/actions/runs/44541252115) | macos-26 cancelled before acquiring a runner | Attempt 2 succeeded |
| deploy/macos | bc0f8f1d036b51a10df3562892c21819bba50746 | [44576964796](https://github.com/yzlzy2333/campus-service-agent/actions/runs/44576964796) | Latest ARM64 and Intel jobs succeeded | Existing successful run retained |
| deploy/linux | 134a38d72836d11c1eba28a40efeb56ffe3ba4bb | [44577014178](https://github.com/yzlzy2333/campus-service-agent/actions/runs/44577014178) | Latest Ubuntu job succeeded | Existing successful run retained |

Main attempt 2 completed successfully on Windows, Ubuntu 24.04, Intel macOS 15, and ARM64 macOS 15. Its recovered ARM64 job is 136266937446. The recovered macOS 26 verification job is 136267192096.

The verification branch tests an older source snapshot. Its successful retry establishes that the macOS 26 runner was allocated and that snapshot passed. Main and the deployment branches retain the latest application fixes.

### Disposition

Recovery succeeded by retrying the affected jobs after GitHub allocated hosted runners. The existing branches were retained. Application code and test coverage were preserved.

The diagnostic action does not remove historical failed workflow attempts. Run links preserve both the original failure and the successful retry. Future runner-capacity failures should be recorded with the attempted commit, run attempt, annotation, runner ID, and executed-step count before drawing conclusions about application code.
