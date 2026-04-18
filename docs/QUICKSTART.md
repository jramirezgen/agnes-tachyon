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
