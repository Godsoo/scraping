import os.path
from product_spiders.base_spiders import SecondaryBaseSpider

HERE = os.path.abspath(os.path.dirname(__file__))
SPIDERS_ROOT = os.path.dirname(HERE)
LAKELAND_ROOT = os.path.join(SPIDERS_ROOT, 'lakeland')


class LakelandAmazonSpider(SecondaryBaseSpider):
    name = 'lakeland-copy-amazon.co.uk-marketplace'
    csv_file = os.path.join(LAKELAND_ROOT, 'lakeland_amazon_marketplace_as_prim.csv')
