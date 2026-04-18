# Quickstart

## Install

```bash
cd /path/to/agnes
pip install -e .
```

## Validate the CLI

```bash
agnes-tachyon --help
agnes-tachyon version
```

## Start backend only

```bash
agnes-tachyon server
```

Then validate:

```bash
agnes-tachyon health
curl -fsS http://localhost:7777/health
```

## Start the integrated operational stack

```bash
agnes-tachyon stack start
```

## Stop services

```bash
agnes-tachyon stop
agnes-tachyon stack stop
```

## Portable workflow

```bash
agnes-tachyon portable export --profile code-only
agnes-tachyon portable restore /path/to/bundle.tar.gz ~/restore-agnes
agnes-tachyon portable verify /path/to/restored/repo/agnes
```

## Automatic merge evaluation reports

The learner writes an evaluation report after each successful merged export.

Required:

```bash
export LIBRARIAN_SWIFT_EXPORT_MERGED=1
```

Recommended:

```bash
export LIBRARIAN_SWIFT_EVAL_ON_MERGE=1
export LIBRARIAN_SWIFT_EVAL_CASES=6
export LIBRARIAN_SWIFT_EVAL_MIN_DELTA=0.03
```

Optional direct A/B against a candidate model already available in Ollama:

```bash
export LIBRARIAN_SWIFT_EVAL_CANDIDATE_MODEL=tachyon:candidate
```

Reports are saved at:

- `data/models/librarian_swift/reports/merge_eval_*.json`
- `data/models/librarian_swift/reports/merge_eval_*.md`
- `data/models/librarian_swift/reports/LATEST_EVAL_REPORT.txt`
