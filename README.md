# Campus Service Agent

A command-line assistant for Windows, Linux, and macOS that helps students find campus procedures and check which application materials they still need. It covers 90 simulated services, including student records, housing, dining, campus cards, and financial aid. The guides contain fictional procedures for demonstration and do not represent any university's policies. The assistant does not submit applications.

The interface and knowledge base support Mandarin. The application can run offline, or use a DeepSeek model through LangChain for tool-driven responses. Both modes share the same guides and material rules.

## Supported platforms

Campus Service Agent supports Windows, Linux, and macOS with Python 3.12. Offline mode and DeepSeek mode are available on all three platforms.

| Platform | Deployment guide |
| --- | --- |
| Windows | [Windows source setup](https://github.com/yzlzy2333/campus-service-agent/blob/main/README.md#getting-started) |
| Linux | [Linux deployment branch](https://github.com/yzlzy2333/campus-service-agent/tree/deploy/linux) |
| macOS (Intel and Apple Silicon) | [macOS deployment branch](https://github.com/yzlzy2333/campus-service-agent/tree/deploy/macos) |

The main branch includes source installation commands for all three systems. The Linux and macOS deployment branches provide platform-specific setup and launch scripts. Each target machine needs Python 3.12 and the project's dependencies.

CI covers Windows, Ubuntu 24.04, Intel macOS, and Apple Silicon macOS, including dependency installation, offline startup, and regression checks. See [validation details](VALIDATION.md) and [source deployment downloads](https://github.com/yzlzy2333/campus-service-agent/releases).

## Getting started

Use Python 3.12 from the project directory. On Windows PowerShell:

~~~powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m campus --offline
~~~

On macOS or Linux:

~~~sh
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m campus --offline
~~~

Type /list to browse services, /new to reset the conversation, or /exit to quit. In a single conversation, try asking in Mandarin about replacing a lost student ID, then say which documents you already have and ask what is still missing. Switch to a campus card question to see how the assistant changes context.

For model-backed responses, set DEEPSEEK_API_KEY in your environment and run python -m campus. DEEPSEEK_MODEL can override the default. Online requests require network access and may consume API credits.

## How it works

The guides combine Markdown text with structured metadata for service aliases and material requirements. BM25 ranks relevant passages and the assistant can fall back to the full guide. Use --mode full to compare full-guide retrieval. The material checker separates items already provided, items still missing, and requirements that depend on unresolved conditions.

See [operations and evaluation](OPERATIONS.md) for index checks, diagnostic logging, and the frozen evaluation suite.
