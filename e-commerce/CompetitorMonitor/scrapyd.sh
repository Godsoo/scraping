#!/bin/sh
PYTHONPATH="${PYTHONPATH}:~/product-spiders/productspidersweb/:~/product-spiders/product_spiders/"
export PYTHONPATH
~/pythoncrawlers/bin/python patch.py

~/pythoncrawlers/bin/scrapyd
