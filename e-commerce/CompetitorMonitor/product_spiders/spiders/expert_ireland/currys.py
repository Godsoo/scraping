"""
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4534
Spider uses CrawlSpider class with rules
"""
from scrapy.spiders import CrawlSpider, Rule
from scrapy.http import FormRequest
from scrapy.linkextractors import LinkExtractor
from urllib2 import urlopen

from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader

class Currys(CrawlSpider):
    name = "expert_ireland_currys"
    allowed_domains = ['currys.ie']
    start_urls = ('http://www.currys.ie/',)
    base_url = 'http://www.currys.ie/'
    
    rules = (
        Rule(LinkExtractor(restrict_xpaths='//div[@id="navcontainer"]'),
             callback='parse_category', follow=True),
        Rule(LinkExtractor(restrict_xpaths=('//div[@id="ProductListingCtr"]',
                                            '//a[@data-product-id]')),
             callback='parse_product')
        )

    def parse_category(self, response):
        form = {}
        for par in response.xpath('//input[@type="hidden"][@value]/@id').extract():
            form[par] = response.xpath('//input[@type="hidden"][@id="%s"]/@value' %par).extract()[0]
        form['__EVENTTARGET'] = 'ctl00$ctl00$_nestedContent$_mainpageContent$_pagingTop1$_showAll'
        yield FormRequest(response.url, formdata=form)
        
    def parse_product(self, response):
        loader = ProductLoader(item=Product(), response=response)
        loader.add_xpath('name', '//div[@class="detailstitle"]/text()')
        loader.add_xpath('identifier', '//script/text()', re="'productID':'(\w+?)'")
        loader.add_xpath('sku', '//script/text()', re="'productID':'(\w+?)'")
        loader.add_value('url', response.url)
        loader.add_xpath('price', '//script/text()', re="'productValue':'([\d\.]+?)'")
        loader.add_xpath('category', '//div[@class="breadcrumb"]/a[position()>1]/text()')
        image_url = response.xpath('//div[@class="mainProductImage"]//img/@src').extract()
        if not image_url:
            image_url = response.xpath('(//div[@class="thumbnail"])[2]//input[@type="image"]/@src').extract()
            image_url = [image_url[0].replace('XSmall', 'Large')]
        if image_url:
            loader.add_value('image_url', response.urljoin(image_url[0]))
        loader.add_xpath('brand', '(//td[contains(h5/text(), "Brand")])[1]/following-sibling::td[1]/span/text()')
        if not response.xpath('//div[@id="availDelTick"]//a[@class="BasketTickOn"]'):
            loader.add_value('stock', 0)
        yield loader.load_item()
