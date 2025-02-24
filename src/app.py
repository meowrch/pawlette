#!/usr/bin/env python3
import constants as cnst
from utils.misc import create_dirs


def main() -> None:
    # Создание каталогов, если их нет.
    create_dirs(paths=[cnst.APP_DATA_DIR, cnst.APP_CACHE_DIR, cnst.APP_CONFIG_DIR])


if __name__ == "__main__":
    main()
