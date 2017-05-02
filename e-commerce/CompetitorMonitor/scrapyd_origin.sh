#!/bin/sh
PYTHONPATH="${PYTHONPATH}:~/product-spiders-scrapy1/productspidersweb/:~/product-spiders-scrapy1/product_spiders/"
export PYTHONPATH
~/pythoncrawlers_scrapy1/bin/python patch.py

~/pythoncrawlers_scrapy1/bin/scrapyd
