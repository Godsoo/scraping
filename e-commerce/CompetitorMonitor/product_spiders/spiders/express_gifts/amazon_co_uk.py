import os
import csv
import paramiko
from product_spiders.base_spiders.amazonspider2 import BaseAmazonSpider
from product_spiders.base_spiders.amazonspider2.scraper import AmazonUrlCreator
from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT

HERE = os.path.abspath(os.path.dirname(__file__))


class ExpressGiftsAmazonSpider(BaseAmazonSpider):
    name = 'expressgifts-amazon.co.uk'
    domain = "amazon.co.uk"
    type = 'asins'
    only_buybox = True
    file_path = HERE + '/express_gifts_flat_file.csv'

    def __init__(self, *args, **kwargs):
        super(ExpressGiftsAmazonSpider, self).__init__(*args, **kwargs)
        transport = paramiko.Transport((CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT))
        password = "jqh3aMrK"
        username = "expressgifts"
        transport.connect(username=username, password=password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        sftp.get('express_gifts_flat_file.csv', self.file_path)

    def get_asins_generator(self):
        with open(self.file_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['AMAZON'].strip():
                    yield(AmazonUrlCreator.get_product_asin_from_url(row['AMAZON']), row['PRODUCT_NUMBER'])
