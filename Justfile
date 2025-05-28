set dotenv-load

uid := `id -u`
gid := `id -g`

invoice_path := join(env_var_or_default("INVOICE_DIR", "data/"), "customer.csv")

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
    -uv run ruff check ./src

# Format python files
[group("dev")]
format:
    -uv run ruff format ./src

# Generate json schemas for pydantic
[group("dev")]
json-schema:
    uv run python src/manage.py schemas

# Generate a new invoice (usage: just invoice <invoice_path> <flags>)
[group("typst")]
@invoice *COMMANDS: json-schema
    uv run python src/manage.py invoice {{ COMMANDS }}

# Render a letter
[group("typst")]
@letter *FLAGS:
    uv run python src/manage.py letter {{ FLAGS }}

# Print customer-to-id mapping
[group("utils")]
@print-customer:
    uv run python src/manage.py print-customer

# Generate a preview for the templates
[group("utils")]
@generate-preview:
    -pdftoppm -f 1 -l 1 -r 150 -png "examples/invoice.example.pdf" > "examples/invoice.preview.png"
    -pdftoppm -f 1 -l 1 -r 150 -png "examples/letter.example.pdf" > "examples/letter.preview.png"

# Link files outside the project
[group("utils")]
link-files:
    {{ path_exists(invoice_path) }}
    -ln -s {{ invoice_path }} data/customer.csv

# Clean up the project
[group("utils"), confirm("Type 'yes' to confirm clean up! Type 'no' to cancel.")]
clean:
    -rm template/*.{bak*,log}
    -rm -r {out,tmp}
