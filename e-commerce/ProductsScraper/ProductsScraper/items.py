# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class ProductsscraperItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    pass

class Product(scrapy.Item):
    Name = scrapy.Field()
    description = scrapy.Field()
    reg_price = scrapy.Field()
    sale_price = scrapy.Field()
    website_id = scrapy.Field()
    brand = scrapy.Field()
    original_url = scrapy.Field()
    category_id = scrapy.Field()
    discount = scrapy.Field()
    image_urls = scrapy.Field()
    images = scrapy.Field()
    original_image_url = scrapy.Field()
    temp_image_url = scrapy.Field()
