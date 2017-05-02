import os
from product_spiders.spiders.bi_worldwide_usa.biworldwide_base import BIWBaseSpider

HERE = os.path.abspath(os.path.dirname(__file__))

class BIWAUSSpider(BIWBaseSpider):
    name = 'biw-aus-feed'
    start_urls = ('http://www.biworldwide.com',)
    file_start_with = 'BI AUS File'

    xls_file_path = HERE + '/biw_products.xlsx'
    csv_file_path = HERE + '/biw_products.csv'

    image_url_key = 'BI ImgURL'
