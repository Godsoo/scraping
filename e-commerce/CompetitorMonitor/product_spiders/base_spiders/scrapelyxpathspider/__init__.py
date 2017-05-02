# coding=utf-8
__author__ = 'juraseg'
import sys
import os.path

from product_spiders.base_spiders.scrapelyxpathspider.spider import ScrapelySpider
from product_spiders.db import Session

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

sys.path.append(os.path.abspath(os.path.join(HERE, '../../../productspidersweb')))

from productspidersweb.models import Spider, ScrapelySpiderData, ScrapelySpiderExtractor

spcls_name = ScrapelySpider.__name__

def get_spider_cls(spider_name):
    db_session = Session()
    db_spider = db_session.query(Spider).filter(Spider.name == spider_name).first()
    if not db_spider:
        return None
    db_scrapely_spider = db_session.query(ScrapelySpiderData)\
        .filter(ScrapelySpiderData.spider_id == db_spider.id)\
        .first()
    if not db_scrapely_spider:
        return None
    db_extractors = db_session.query(ScrapelySpiderExtractor)\
        .filter(ScrapelySpiderExtractor.scrapely_spider_data_id == db_scrapely_spider.id)
    if not db_extractors.count():
        return None

    db_session.close()

    return ScrapelySpider