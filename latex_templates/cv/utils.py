from pathlib import Path

import yaml

from latex_templates.cv.models import CV


def load_cv(file: Path) -> CV:
    """Load config file.

    Parameters
    ----------
    file : Path
        Path to config file.

    Returns
    -------
    Config
        Config object.
    """
    with file.open("rb") as f:
        parsed_file = yaml.safe_load(f)
        config = CV(**parsed_file)
    return config
