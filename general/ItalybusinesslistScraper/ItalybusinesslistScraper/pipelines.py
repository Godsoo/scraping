# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html

from scrapy.exceptions import DropItem

class ItalybusinesslistscraperPipeline(object):
    def __init__(self):
        self.companies_seen = set()

    def process_item(self, item, spider):
        company = item['EMAIL'] + item['RAGIONE_SOCIALE']
        if company in self.companies_seen:
            raise DropItem("Duplicate item found: %s" % item)
        else:
            self.companies_seen.add(company)
            return item
