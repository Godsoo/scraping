# -*- coding: utf-8 -*-
import scrapy
from scrapy.http import Request
from BarepsScraper.items import BarepsscraperItem
import re
import requests
from scrapy.selector import Selector

class BarepsSpider(scrapy.Spider):
    name = "bareps"
    start_urls = (
        'http://www.ba-reps.com/',
    )
    all_items = []
    def __init__(self):
        self.all_items = []

    def parse(self, response):
        for category_url in response.xpath('//div[@id="nav"]/div[@class="menu"]/ul/li/a/@href').extract():
            yield Request(url=response.urljoin(category_url), callback=self.parse_category)
            # break

    def parse_category(self, response):
        for page_url in response.xpath('//div[@id="artist_list"]//ul[@class="artist_list"]/li/a/@href').extract():
            yield Request(url=response.urljoin(page_url), callback=self.parse_detail)
            # break

    def parse_detail(self, response):
        item = BarepsscraperItem()

        item['page_url'] = response.url
        item['artist_name'] = response.xpath('//div[@class="blog_content"]/h1[@class="project_reader_artist notranslate"]/text()').extract_first()
        item['category'] = response.xpath('//div[@class="blog_content"]/h1[@class="project_reader_title"]/text()').extract_first()
        item['personal_website_url'] = response.xpath('//div[@class="blog_content"]/div[@id="bio"]//a/@href').extract_first()
        item['instagram_username'] =''
        item['biography_text'] = ''.join([frag.strip() for frag in response.xpath('//div[@class="blog_content"]/div[@id="bio"]//text()').extract()])
        item['clients'] = str([frag_name.strip() for frag_name in ''.join([frag.strip() for frag in response.xpath('//div[@class="blog_content"]/div[@id="clients"]//text()').extract()]).split(',')])
        item['img_urls'] = []

        for img in response.xpath('//div[@class="blog_image"]/ul/li'):
            img_text = img.xpath('div[@class="m_item_text"]/a/text()').extract_first()
            # get from filename
            img_url = img.xpath('.//div[@class="m_item_image"]/img/@filename').extract_first()
            if (img_url is None) or (img_url == ''):
                # get video url
                img_url = img.xpath('.//div[@class="m_item_image"]/video/source/@src').extract_first()
            if (img_url is None) or (img_url == ''):
                # get from src
                img_text = img.xpath('.//div[@class="m_item_image"]/img/@alt').extract_first()
                img_url = img.xpath('.//div[@class="m_item_image"]/img/@src').extract_first()

            img_detail = Selector(text=requests.get(response.urljoin(img.xpath('a/@href').extract_first())).text)
            img_details = img_detail.xpath('//ul[@id="masonry"]/li//div[@class="m_item_image"]/img[contains(@class, "image")]/@filename').extract()
            item['img_urls'].append((img_text, [img_url] + img_details))
        item['img_urls'] = str(item['img_urls'])

        yield item

