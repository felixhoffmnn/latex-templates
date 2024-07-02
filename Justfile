set dotenv-load

uid := `id -u`
gid := `id -g`

container_runtime := env_var_or_default("CONTAINER_RUNTIME", "podman")
latex_run := container_runtime + " run --rm -it -v " + justfile_directory() + ":/workdir:z -w /workdir --userns keep-id:uid=" + uid + ",gid=" + gid + " texlive/texlive:latest-full"

# Print a list of available commands
@help:
    just --list

# Install dependencies
@install:
    poetry install
    poetry run pre-commit install

# Create a folder
@_create-folder *PATHS:
    mkdir -p {{ PATHS }}

# Lint python and tex files
lint:
    -poetry run ruff check ./latex_templates
    -{{ latex_run }} chktex ./template/*.{tex.j2,tex,cls}

# Check python types
check:
    poetry run mypy ./latex_templates

# Format python and tex files
@format:
    poetry run ruff format ./latex_templates
    {{ latex_run }} latexindent -s -w ./template/*.{tex.j2,tex,cls}

# Generate json schemas for pydantic
@json-schema:
    poetry run python latex_templates/manage.py schemas

# Generate a new invoice
@invoice *FLAGS:
    poetry run python latex_templates/manage.py invoice {{ FLAGS }}

# Clean up the project
clean:
    -rm template/*.{bak*,log}
    -rm -r {out,tmp}
