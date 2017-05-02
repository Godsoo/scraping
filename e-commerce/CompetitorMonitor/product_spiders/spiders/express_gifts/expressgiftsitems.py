from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT
# -*- coding: utf-8 -*-
import os
import csv
import paramiko

from scrapy.spider import BaseSpider
from scrapy.item import Item, Field

HERE = os.path.abspath(os.path.dirname(__file__))


class ExpressGiftsBaseSpider(BaseSpider):
    def start_requests(self):
        transport = paramiko.Transport((CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT))
        password = "jqh3aMrK"
        username = "expressgifts"
        transport.connect(username = username, password = password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        files = sftp.listdir_attr()
        
        file_path = HERE + '/express_gifts_flat_file.csv'
        sftp.get('express_gifts_flat_file.csv', file_path)


        with open(file_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                yield row

class ExpressGiftsMeta(Item):
    buyer = Field()
