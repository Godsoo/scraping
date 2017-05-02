import os
from product_spiders.spiders.bi_worldwide_usa.biworldwide_base import BIWBaseSpider

HERE = os.path.abspath(os.path.dirname(__file__))

class BIWUSASpider(BIWBaseSpider):
    name = 'biw-usa-feed'
    start_urls = ('http://www.biworldwide.com',)
    file_start_with = 'BI USA File'

    xls_file_path = HERE + '/biw_products.xlsx'
    csv_file_path = HERE + '/biw_products.csv'
    image_url_key = 'BI ImgURL'
    tag_keys = {'bi_tag_1': 'BI Tag 1', 'bi_tag_2': 'BI Tag 2'}
