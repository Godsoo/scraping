import os
from product_spiders.spiders.bi_worldwide_usa.biworldwide_base import BIWBaseSpider

HERE = os.path.abspath(os.path.dirname(__file__))


class BIWINDSpider(BIWBaseSpider):
    name = 'biw-ind-feed'
    start_urls = ('http://www.biworldwide.com',)
    file_start_with = 'BI IND File'

    xls_file_path = HERE + '/biw_products.xlsx'
    csv_file_path = HERE + '/biw_products.csv'
