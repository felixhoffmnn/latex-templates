set dotenv-load := true

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
    -pdftoppm -f 1 -l 1 -r 150 -png "examples/invoice.example.pdf" > "examples/invoice.preview.png"
    -pdftoppm -f 1 -l 1 -r 150 -png "examples/letter.example.pdf" > "examples/letter.preview.png"

# Clean up the project
[confirm("Type 'yes' to confirm clean up! Type 'no' to cancel.")]
[group("utils")]
clean:
    -rm template/*.{bak*,log}
    -rm -r {out,tmp}
