import tomllib
from pathlib import Path

import typer
from pydantic import BaseModel


class Config(BaseModel):
    """Config model for the config.toml file."""

    company: dict
    address: dict
    bank: dict
    invoice: dict
    style: dict


if __name__ == "__main__":
    app = typer.Typer()

    # Load user and project config
    with Path.open("config.toml") as f:
        config = Config(**tomllib.load(f))
