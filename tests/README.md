# Test

## Requirements

-   ssh
-   git

## Setup

Ensure that you have cloned the submodules with

```bash
git submodule init
git submodule update
```

Install test dependencies with

```bash
poetry install
```

## Run tests

```bash
poetry run python -m pytest
```
