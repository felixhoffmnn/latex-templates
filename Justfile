set dotenv-load := true
set default-list

CONTAINER_RUNTIME := env("CONTAINER_RUNTIME", "podman")
OPEN_PDF := if env("OPEN_PDF", "true") == "true" {"--open-pdf"} else {"--no-open-pdf"}
OPEN_MAIL := if env("OPEN_MAIL", "true") == "true" {"--open-mail"} else {"--no-open-mail"}
VALIDATOR_IMAGE := "ghcr.io/felixhoffmnn/invoice-toolkit/xrechnung-validator:latest"

# Install dependencies, bootstrap config, and generate schemas
[group("dev")]
setup:
    #!/usr/bin/env bash
    set -euo pipefail

    uv sync
    uv run prek install

    # Bootstrap .env from example if missing
    if [ ! -f .env ]; then
        cp .env.example .env
        echo "Created .env from .env.example"
    fi

# Run tests
[group("dev")]
test:
    uv run pytest

# Check python code for type hints and linting
[group("dev")]
check:
    -uv run ruff check

# Format python files
[group("dev")]
format:
    -uv run ruff format

# Generate json schemas for pydantic
[group("dev")]
@json-schema:
    uv run --extra cli toolkit schemas

# Generate a new invoice (usage: just invoice <invoice_path> <flags>)
[group("typst")]
@invoice *CMD:
    uv run --extra cli toolkit invoice {{ CMD }} {{ OPEN_PDF }} {{ OPEN_MAIL }}

# Render a letter
[group("typst")]
@letter *FLAGS:
    uv run --extra cli toolkit letter {{ FLAGS }} {{ OPEN_PDF }}

# Print customer-to-id mapping
[group("utils")]
@print-customer:
    uv run --extra cli toolkit print-customer

# Generate examples and previews for the templates
[group("utils")]
generate-examples:
    #!/usr/bin/env bash
    set -euo pipefail

    # Letter
    uv run --extra cli toolkit letter examples/letter/letter.example.md \
        --config examples/letter/config.example.yml \
        --output examples/letter/letter.example \
        --dry-run

    # Invoices
    for variant in vat-exempt vat; do
        uv run --extra cli toolkit invoice --invoices "examples/${variant}/invoices.example.yml" \
            --config "examples/${variant}/config.example.yml" \
            --customer "examples/${variant}/customer.example.csv" \
            --output "examples/${variant}/invoice.example" \
            --dry-run --all
    done

    # Preview PNGs
    for pdf in examples/*/*.example.pdf; do
        name=$(basename "$pdf" .example.pdf)
        pdftoppm -f 1 -l 1 -r 150 -png "$pdf" > "$(dirname "$pdf")/${name}.preview.png"
    done

# Validate a XRechnung XML file (usage: just validate <path>)
[group("utils")]
validate PATH:
    {{ CONTAINER_RUNTIME }} run --rm -v "$(realpath {{ PATH }}):/data/$(basename {{ PATH }}):z,ro" {{ VALIDATOR_IMAGE }} "/data/$(basename {{ PATH }})"

# Run pre-commit hooks
[group("utils")]
pre-commit:
    uv run prek run --all-files

# Clean up the project
[confirm("Type 'yes' to confirm clean up! Type 'no' to cancel.")]
[group("utils")]
clean:
    -rm template/*.{bak*,log}
    -rm -r {out,tmp}
