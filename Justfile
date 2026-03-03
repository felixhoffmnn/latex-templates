set dotenv-load := true

CONTAINER_RUNTIME := env("CONTAINER_RUNTIME", "podman")

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
@generate-examples: invoice letter
    -pdftoppm -f 1 -l 1 -r 150 -png "examples/invoice-no-vat.example.pdf" > "examples/invoice-no-vat.preview.png"
    -pdftoppm -f 1 -l 1 -r 150 -png "examples/invoice-vat.example.pdf" > "examples/invoice-vat.preview.png"
    -pdftoppm -f 1 -l 1 -r 150 -png "examples/letter.example.pdf" > "examples/letter.preview.png"

# Build the XRechnung validator container image
[private]
validator-build:
    #!/usr/bin/env bash
    set -euo pipefail
    if ! {{ CONTAINER_RUNTIME }} image inspect xrechnung-validator:latest >/dev/null 2>&1; then
        echo "Building validator image..."
        {{ CONTAINER_RUNTIME }} build -t xrechnung-validator:latest -f container/Containerfile.validator container/
    fi

# Validate XRechnung XML files (usage: just validate [path...])
[group("validator")]
validate *PATH: validator-build
    #!/usr/bin/env bash
    set -euo pipefail
    if [ -n "{{ PATH }}" ]; then
        FILES="{{ PATH }}"
    else
        FILES=$(find out/invoice -name '*.xml' 2>/dev/null || true)
    fi
    for f in $FILES; do
        echo "Validating: $f"
        {{ CONTAINER_RUNTIME }} run --rm -v "$(realpath "$f"):/data/$(basename "$f"):ro" \
            xrechnung-validator:latest "/data/$(basename "$f")"
    done

# Clean up the project
[confirm("Type 'yes' to confirm clean up! Type 'no' to cancel.")]
[group("utils")]
clean:
    -rm template/*.{bak*,log}
    -rm -r {out,tmp}
    -find schema -mindepth 1 ! -name '.gitignore' -delete
