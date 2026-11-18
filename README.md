# Campus Service Agent

A command-line assistant for finding campus procedures and checking which application materials a student still needs. It covers 90 simulated services, including student records, housing, dining, campus cards, and financial aid. The guides contain fictional procedures for demonstration and do not represent any university's policies. The assistant does not submit applications.

The interface and knowledge base support Mandarin. The application can run offline, or use a DeepSeek model through LangChain for tool-driven responses. Both modes share the same guides and material rules.

## Getting started on Linux

Install Git and Python 3.12 with your distribution's package manager. For Ubuntu 24.04:

```sh
sudo apt update
sudo apt install git python3.12 python3.12-venv
```

On other distributions, make sure Git and an interpreter with working `python3.12 -m venv` are available on your PATH.

```sh
git clone --branch deploy/linux --single-branch https://github.com/yzlzy2333/campus-service-agent.git
cd campus-service-agent
./deploy.sh setup
./deploy.sh run --offline
```

To verify the guide index, run `./deploy.sh run --rebuild-index`. Run `./deploy.sh setup` again after updating dependencies. The setup script installs the pinned requirements into `.venv`.

Type /list to browse services, /new to reset the conversation, or /exit to quit. In a single conversation, try asking in Mandarin about replacing a lost student ID, then say which documents you already have and ask what is still missing. Switch to a campus card question to see how the assistant changes context.

For model-backed responses, set `DEEPSEEK_API_KEY` in your environment and run `./deploy.sh run`. DEEPSEEK_MODEL can override the default. Online requests require network access and may consume API credits.

## How it works

The guides combine Markdown text with structured metadata for service aliases and material requirements. BM25 ranks relevant passages and the assistant can fall back to the full guide. Use --mode full to compare full-guide retrieval. The material checker separates items already provided, items still missing, and requirements that depend on unresolved conditions.

See [operations and evaluation](OPERATIONS.md) for index checks, diagnostic logging, and the frozen evaluation suite.
