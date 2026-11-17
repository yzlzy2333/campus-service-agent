# Operations and evaluation

Run these commands from the repository root in the environment where you installed the dependencies:

~~~sh
python -m campus --rebuild-index
python -m campus --list-guides
python -m campus --offline --mode full
python -m campus --offline --log session.jsonl
python -m evaluation.audit
python -m evaluation.run --out evaluation/local-results.json
~~~

The index check should load 90 services and 373 passages. Logs can record guide names, versions, and sections used as evidence. Review logs before sharing them.

The frozen suite in evaluation/cases.json includes 117 cases. The corresponding hashes are in evaluation/freeze.json. The audit checks guide coverage, while the regression runner covers scenarios such as retrieval, material checks, and conversation state. Offline tests and simulated HTTP tests do not measure the accuracy of answers from a live model.

After configuring DEEPSEEK_API_KEY, you can run a small live sample and generate a human review template:

~~~sh
python -m evaluation.run --live --case A1 --case B1 --out evaluation/live-sample.json
python -m evaluation.review evaluation/live-sample.json --labels evaluation/live-labels.json --template
~~~

Review task completion, tool use, and citation support against the original guides. To summarize your labels, repeat the review command without --template. Omitting --case runs the full live evaluation and consumes more API credits.
