import json
from pathlib import Path

from loguru import logger

import pawlette.constants as cnst
from pawlette.schemas.config_struct import Config


def generate_default_config():
    cnst.APP_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(cnst.APP_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(
            obj=cnst.DEFAULT_CONFIG,
            fp=f,
            indent=4,
        )


def load_config(path: Path) -> Config:
    if not path.exists():
        logger.warning(
            f"Warning: The config file '{path}' was not found. Using default config."
        )
        return Config(**cnst.DEFAULT_CONFIG)

    try:
        with open(path) as f:
            config_dict = json.load(f)

            if "comment_styles" in config_dict:
                for comment_format in cnst.COMMENT_FORMATS:
                    if comment_format not in config_dict["comment_styles"]:
                        config_dict["comment_styles"][comment_format] = (
                            cnst.COMMENT_FORMATS[comment_format]
                        )

            config = Config(**config_dict)
            return config
    except Exception:
        logger.warning(
            f"Warning: The config file '{path}' is invalid. Using default config."
        )
        return Config(**cnst.DEFAULT_CONFIG)


