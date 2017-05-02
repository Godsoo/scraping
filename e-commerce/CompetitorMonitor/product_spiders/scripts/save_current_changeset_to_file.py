# -*- coding: utf-8 -*-
import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))
PRODUCT_SPIDERS = os.path.dirname(HERE)
ROOT = os.path.dirname(PRODUCT_SPIDERS)

sys.path.append(ROOT)
from product_spiders.config import HG_EXEC
from product_spiders.hgread import save_root_active_changeset_data


def main():
    save_root_active_changeset_data(HG_EXEC)


if __name__ == '__main__':
    main()
