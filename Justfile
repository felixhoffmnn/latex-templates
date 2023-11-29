set dotenv-load

uid := `id -u`
gid := `id -g`

# Print a list of available commands
@help:
    just --list

# Create a folder
@_create-folder *PATHS:
    mkdir -p {{ PATHS }}

# Lint python and tex files
lint:
    -poetry run ruff lint ./latex_templates
    -podman run --rm -it -v {{ justfile_directory() }}:/workdir:z -w /workdir --userns keep-id:uid={{ uid }},gid={{ gid }} custom-texlive:latest chktex ./templates/*.tex

# Format python and tex files
@format:
    poetry run ruff format ./latex_templates
    podman run --rm -it -v {{ justfile_directory() }}:/workdir:z -w /workdir --userns keep-id:uid={{ uid }},gid={{ gid }} custom-texlive:latest latexindent -s -w ./templates/*.tex

# Generate a new invoice
@invoice: (_create-folder "data/invoices/{out,tmp}/")
    poetry run python latex_templates/manage.py invoice

# Clean up the project
clean:
    -rm templates/*.bak*
    -rm -r data/invoices/out/
    -rm -r data/invoices/tmp/
