# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class NextmanagementscraperItem(scrapy.Item):	
    portfolio_url = scrapy.Field() # portfolio url (e.g. http://www.nextmanagement.com/new-york/profile/alice-glass)
    artist_name = scrapy.Field() # artist name (e.g. Adrianne Parkhouse)
    subcategory_name = scrapy.Field() # subcategory name (e.g. Men, Hair, New Faces Women)
    city = scrapy.Field()
    biography_text = scrapy.Field() # biography text (if present)
    instagram_username = scrapy.Field() # instagram username (if present)
    img_urls = scrapy.Field() # a dict of portfolio images with album title as the key and a list of images as value (e.g. {‘Portfolio’ : [‘url1’, ‘url2’], ‘Covers’ : [‘url3’, ‘url4’]} ))
