set dotenv-load

uid := `id -u`
gid := `id -g`

# Print a list of available commands
@help:
    just --list

# Lint python and tex files
lint:
    -poetry run ruff lint ./selbststaendigkeit
    -podman run --rm -it -v {{ justfile_directory() }}:/workdir:z -w /workdir --userns keep-id:uid={{ uid }},gid={{ gid }} custom-texlive:latest chktex ./templates/*.tex

# Format python and tex files
@format:
    poetry run ruff format ./selbststaendigkeit
    podman run --rm -it -v {{ justfile_directory() }}:/workdir:z -w /workdir --userns keep-id:uid={{ uid }},gid={{ gid }} custom-texlive:latest latexindent -s -w ./templates/*.tex

# Generate a new invoice
@invoice:
    poetry run python selbststaendigkeit/manage.py invoice
