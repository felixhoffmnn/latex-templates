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
    -poetry run ruff lint ./selbststaendigkeit
    -podman run --rm -it -v {{ justfile_directory() }}:/workdir:z -w /workdir --userns keep-id:uid={{ uid }},gid={{ gid }} custom-texlive:latest chktex ./templates/*.tex

# Format python and tex files
@format:
    poetry run ruff format ./selbststaendigkeit
    podman run --rm -it -v {{ justfile_directory() }}:/workdir:z -w /workdir --userns keep-id:uid={{ uid }},gid={{ gid }} custom-texlive:latest latexindent -s -w ./templates/*.tex

# Generate a new invoice (we first need to create tmp and out folders)
@invoice: (_create-folder "invoices/{out,tmp}/")
    poetry run python selbststaendigkeit/manage.py invoice

# Clean up the project
clean:
    -rm templates/*.bak*
    -rm -r invoices/out/
    -rm -r invoices/tmp/
