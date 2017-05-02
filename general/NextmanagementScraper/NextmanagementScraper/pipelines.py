# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html


class NextmanagementscraperPipeline(object):
    def __init__(self):
        self.artists_seen = set()

    def process_item(self, item, spider):
        artistid = item['artist_name'] + item['portfolio_url']
        if artistid in self.artists_seen:
            raise DropItem("Duplicate item found: %s" % item)
        else:
            self.artists_seen.add(artistid)
            return item
