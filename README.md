## Requirements

### Local Requirements:

-   poetry with python>=3.9
-   docker/podman
-   docker-compose

### Basic remote server requirements

-   docker
-   docker-compose
-   ssh

### Automatically installed requirements

Note: they need to available to be installed from a package manager

-   tcpdump
-   iproute2
-   git

## Installation

Install the python dependencies with poetry

```bash
poetry install
```

Prepare the docker images

```bash
docker-compose build
```

## Usage

When the competition starts run

```bash
poetry run python -m worker autosetup
```

and follow the instructions
