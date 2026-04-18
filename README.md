# Agnes Tachyon

Agnes Tachyon is a local cognitive systems prototype for research workflows. It combines a FastAPI backend, local Ollama/Qwen inference, voice input/output, continuous fine-tuning hooks, and Miniverse integration for multi-agent execution.

This repository is being formalized from an active prototype into a public monorepo. The current focus is Linux/WSL as the primary backend target, with the frontend and operational runtime kept in the same repository.

## What It Includes

- `tachyon/`: Python backend, voice pipeline, memory, personality/state, training, and bridges.
- `apps/miniverse/`: integrated frontend/runtime components.
- `bin/`: legacy operational wrappers kept for compatibility.
- `.github/skills/agnes-tachyon-portable/`: internal tooling for portable export/restore/verify.

## Current Status

- Installable Python package metadata is now included via `pyproject.toml`.
- A first standard CLI is available through `agnes-tachyon`.
- Legacy scripts are still supported while the CLI absorbs their responsibilities.

## Quick Start

### 1. Install in editable mode

```bash
pip install -e .
```

### 2. Check the CLI

```bash
agnes-tachyon --help
agnes-tachyon version
```

### 3. Start the backend server

```bash
agnes-tachyon server
```

### 4. Check health

```bash
agnes-tachyon health
```

### 5. Start the integrated stack

```bash
agnes-tachyon stack start
```

## External Prerequisites

- Python 3.10+
- Node.js for Miniverse/frontend pieces
- Ollama running locally for inference
- Optional GPU Python environment for training and learner flows

## Repository Direction

The public package name is `agnes-tachyon`.

The implementation is intentionally incremental:
- standard packaging first
- standard CLI second
- shell wrappers retained temporarily
- frontend normalization and CI next

## Notes

- The repository still contains prototype-era assumptions that are being normalized.
- Large trained models and generated runs are intentionally not part of the public baseline.
- Linux/WSL is the primary supported backend target for now.

See [docs/QUICKSTART.md](docs/QUICKSTART.md) for a slightly more explicit bootstrap path.
