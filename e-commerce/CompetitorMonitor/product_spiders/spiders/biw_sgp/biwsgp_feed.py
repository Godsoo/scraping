import os
from product_spiders.spiders.bi_worldwide_usa.biworldwide_base import BIWBaseSpider

HERE = os.path.abspath(os.path.dirname(__file__))

class BIWSGPSpider(BIWBaseSpider):
    name = 'biw-sgp-feed'
    start_urls = ('http://www.biworldwide.com',)
    file_start_with = 'BI SGP File'

    xls_file_path = HERE + '/biw_products.xlsx'
    csv_file_path = HERE + '/biw_products.csv'
