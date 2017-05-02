# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy

class BarepsscraperItem(scrapy.Item):
    page_url = scrapy.Field() # artist url (e.g. http://www.ba-reps.com/photographers/david-goldman)
    artist_name = scrapy.Field() # artist name (e.g. David Goldman)
    category = scrapy.Field() # category name (e.g. Photographers)
    personal_website_url = scrapy.Field() # personal website url (if present)
    instagram_username = scrapy.Field() # instagram username (if present)
    biography_text = scrapy.Field() # biography text (if present)
    clients = scrapy.Field() # a list of clients (if present)
    img_urls = scrapy.Field() #  a list of tuples containing img urls and category name (e.g. [("Menswear Fashion", "http://assets.lookbookspro.com/bernstein-andriulli/gs_5832cba2-d080-4d2a-85c6-63d90a771fd0.jpg"),...])
