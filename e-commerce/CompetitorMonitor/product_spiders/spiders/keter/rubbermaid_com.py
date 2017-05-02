import time
import re

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from urllib import urlencode

from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader
)

from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals

from phantomjs import PhantomJS

from keteritems import KeterMeta, Review, ReviewLoader


class RubbermaidSpider(BaseSpider):
    name = 'keter-rubbermaid.com'
    allowed_domains = ['rubbermaid.com']

    start_urls = [
        'http://www.rubbermaid.com/category/pages/subcategorylanding.aspx?CatName=Outdoor&SubCatId=shed-accessories',
        'http://www.rubbermaid.com/category/pages/subcategorylanding.aspx?CatName=Outdoor&SubCatId=VerticalSheds',
        'http://www.rubbermaid.com/category/pages/subcategorylanding.aspx?CatName=Outdoor&SubCatId=HorizontalSheds',
        'http://www.rubbermaid.com/category/pages/subcategorylanding.aspx?CatName=Outdoor&SubCatId=DeckBoxesPatioBenches',
        'http://www.rubbermaid.com/category/pages/subcategorylanding.aspx?CatName=GarageOrganization&SubCatId=ResinCabinets',
        'http://www.rubbermaid.com/category/pages/subcategorylanding.aspx?CatName=GarageOrganization&SubCatId=FastTrackGarageOrganizationSystem'
    ]

    def __init__(self, *args, **kwargs):
        super(RubbermaidSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.spider_closed, signals.spider_closed)

        self._browser = PhantomJS.create_browser()

        max_wait = 60
        self._browser.set_page_load_timeout(max_wait)
        self._browser.set_script_timeout(max_wait)

    def spider_closed(self):
        self._browser.quit()

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        for url in hxs.select('//div[@id="foodStorageBlock"]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url),
                          callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        shipping_cost = hxs.select('.//a[contains(text(), "Delivery Surcharge")]//../..//td[2]//span/text()').extract()
        if not shipping_cost:
            shipping_cost = hxs.select('.//td[contains(text(), "Shipping Surcharge")]//..//td[2]//span/text()').extract()

        loader = ProductLoader(item=Product(), selector=hxs)
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//h1[@id="ProductNameH1"]/text()')
        loader.add_value('category', hxs.select('//div[@class="breadcrum"]/div/a/text()').extract()[-1])
        loader.add_xpath('identifier', '//form//input[@id="hdnProdId" or @name="hdnProdId"]/@value')
        price = hxs.select('.//td[contains(text(), "Price:")]//..//td[2]//span/text()').extract()
        if price:
            loader.add_value('price', price[0])
        else:
            loader.add_value('price', 0)
        try:
            loader.add_value('shipping_cost', shipping_cost[0].strip())
        except:
            pass

        item = hxs.select('//td/strong')
        if item and item[0].select('../text()'):
            loader.add_value('sku', item[0].select('../text()').extract()[1].strip('#() '))

        image_url = hxs.select('//div[@id="divImageBlock"]//img/@src').extract()
        if image_url:
            loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))

        loader.add_value('brand', 'Rubbermaid')

        product = loader.load_item()

        product['sku'] = product['sku'].upper()

        metadata = KeterMeta()
        metadata['brand'] = 'Rubbermaid'
        metadata['reviews'] = []
        product['metadata'] = metadata

        self.log('>> BROWSER => GET < %s />' % response.url)
        self._browser.get(response.url)
        self.log('>> OK')

        self.log('>> BROWSER => Looking for more reviews ...')
        try:
            load_more_button = self._browser.find_element_by_xpath('//div[@class="bv-content-pagination"]//button')
            more_reviews = load_more_button.is_displayed()
            max_pages = 25
            while more_reviews and max_pages:
                self.log('>> More reviews found...')
                load_more_button.click()
                self.log('>> BROWSER => CLICK "Load more"')
                time.sleep(20)
                self.log('>> OK')
                load_more_button = self._browser.find_element_by_xpath('//div[@class="bv-content-pagination"]//button')
                more_reviews = load_more_button.is_displayed()
                max_pages -= 1
            self.log('>> No more reviews...')
        except Exception, e:
            self.log('>> ERROR FOUND => %s' % e)

        hxs = HtmlXPathSelector(text=self._browser.page_source)

        for review in hxs.select('//ol[contains(@class, "bv-content-list-Reviews")]//li[contains(@class, "bv-content-review")]'):
            review_loader = ReviewLoader(item=Review(), selector=review, date_format='%m/%d/%Y')

            review_loader.add_xpath('date', u'.//div[@class="bv-content-datetime"][1]//meta[@itemprop="dateCreated"]/@content')
            review_loader.add_xpath('full_text', u'.//div[@itemprop="reviewBody"]/p/text()')
            review_loader.add_xpath('rating', u'.//abbr[contains(@class, "bv-rating-stars-on")][1]/@title')
            review_loader.add_value('url', response.url)

            product['metadata']['reviews'].append(review_loader.load_item())

        yield product
