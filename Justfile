set dotenv-load := true

CONTAINER_RUNTIME := env("CONTAINER_RUNTIME", "podman")
VALIDATOR_IMAGE := "ghcr.io/felixhoffmnn/invoice-toolkit/xrechnung-validator:latest"

# Print a list of available commands
@help:
    just --list

# Install dependencies
[group("dev")]
@install:
    uv sync
    uv run pre-commit install

# Check python code for type hints and linting
[group("dev")]
check:
    -uv run ruff check ./src/invoice_toolkit

# Format python files
[group("dev")]
format:
    -uv run ruff format ./src/invoice_toolkit

# Generate json schemas for pydantic
[group("dev")]
@json-schema:
    uv run invoice-toolkit schemas

# Generate a new invoice (usage: just invoice <invoice_path> <flags>)
[group("typst")]
@invoice *CMD: json-schema
    uv run invoice-toolkit invoice {{ CMD }}

# Render a letter
[group("typst")]
@letter *FLAGS: json-schema
    uv run invoice-toolkit letter {{ FLAGS }}

# Print customer-to-id mapping
[group("utils")]
@print-customer:
    uv run invoice-toolkit print-customer

# Generate examples and previews for the templates
[group("utils")]
generate-examples: json-schema
    #!/usr/bin/env bash
    set -euo pipefail

    # Letter
    uv run invoice-toolkit letter examples/letter/letter.example.md \
        --config-file examples/letter/config.example.yml \
        --output examples/letter/letter.example \
        --dry-run

    # Invoices
    for variant in vat-exempt vat; do
        uv run invoice-toolkit invoice "examples/${variant}/invoices.example.yml" \
            --config-path "examples/${variant}/config.example.yml" \
            --customer-path "examples/${variant}/customer.example.csv" \
            --output "examples/${variant}/invoice.example" \
            --dry-run --make-all
    done

    # Preview PNGs
    for pdf in examples/*/*.example.pdf; do
        name=$(basename "$pdf" .example.pdf)
        pdftoppm -f 1 -l 1 -r 150 -png "$pdf" > "$(dirname "$pdf")/${name}.preview.png"
    done

# Validate a XRechnung XML file (usage: just validate <path>)
[group("validator")]
validate PATH:
    {{ CONTAINER_RUNTIME }} run --rm -v "$(realpath {{ PATH }}):/data/$(basename {{ PATH }}):z,ro" {{ VALIDATOR_IMAGE }} "/data/$(basename {{ PATH }})"

# Clean up the project
[confirm("Type 'yes' to confirm clean up! Type 'no' to cancel.")]
[group("utils")]
clean:
    -rm template/*.{bak*,log}
    -rm -r {out,tmp}
    -find schema -mindepth 1 ! -name '.gitignore' -delete
