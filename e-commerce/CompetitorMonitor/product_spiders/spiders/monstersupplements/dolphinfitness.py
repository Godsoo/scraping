from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector

from scrapy.http import Request

from scrapy.utils.response import get_base_url

from scrapy.utils.url import  urljoin_rfc

from product_spiders.items import Product, ProductLoader

import logging


def is_number(arg):
    try:
        float(arg)
        return True
    except ValueError:
        return False

class DolphinFitnessSpider(BaseSpider):
    name = "www.dolphinfitness.co.uk"
    allowed_domains = ["dolphinfitness.co.uk"]
    start_urls = (
        "http://www.dolphinfitness.co.uk",
    )

    products_parsed = []

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        div_tabs = hxs.select('//div[@class="tabs_menu"]')

        for tab in div_tabs:
            # span = tab.select('span/text()').extract()
            # if span and 'Brands' in span:
            #    continue
            clickable_category = tab.select('a/@href').extract()

            if clickable_category:
                cat = tab.select('a/text()').extract()

                new_url = urljoin_rfc(base_url, clickable_category[0])
                request = Request(new_url, callback=self.parse_product_listing)
                if cat:
                    request.meta['category'] = cat[0]
                yield request
            else:
                category = tab.select('.//span[1]/text()').extract()

                links = tab.select('./ul//li/a/@href').extract()
                for link in links:
                    split_link = link.split('/')[-1]
                    new_url = urljoin_rfc(base_url, link)
                    if is_number(split_link):
                        request = Request(new_url,
                                        callback=self.parse_product)
                        if category:
                            request.meta['category'] = category[0]
                        yield request
                    else:
                        request = Request(new_url,
                                        callback=self.parse_product_listing)
                        if category:
                            request.meta['category'] = category[0]
                        yield request

        offers_url = urljoin_rfc(base_url, 'en/dolphin-fitness')
        yield Request(offers_url, callback=self.parse_offers_page)

    def parse_offers_page(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        offer_urls = hxs.select('//div[@id="content"]//a/@href').extract()
        for url in offer_urls:
            new_url = urljoin_rfc(base_url, url)
            yield Request(new_url, callback=self.parse_offer)

    def parse_offer(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        name = hxs.select(
            '//div[@class="ajax_promo_wrap_info"]/h1/text()').extract()

        identifier = '%s - %s' % ('Special Offer', name[0])

        img_url = hxs.select(
            '//div[@class="ajax_promo_wrap_pic"]//img/@src').extract()
        img_url_final = '%s%s' % (base_url, img_url[0])

        loader = ProductLoader(response=response, item=Product())
        loader.add_value('name', name[0])
        loader.add_value('url', response.url)
        loader.add_xpath('price',
                    '//span[@id="ajax_promo_price_span"]/text()')
        loader.add_value('image_url', img_url_final)
        # loader.add_value('metadata', '')
        loader.add_value('category', 'Special offers')
        loader.add_value('shipping_cost', 'Not Available')
        loader.add_value('identifier', identifier)
        yield loader.load_item()

    def parse_product_listing(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        product_urls = hxs.select(\
                        '//div[@class="snapshot"]/div[@class="dsc"]/a/@href')\
                                                                    .extract()
        # logging.error("producturls")
        # logging.error(product_urls)
        category = hxs.select('//div[@id="content"]/h1/text()').extract()

        for url in product_urls:
            if 'en/dolphin-fitness' in url:
                continue
            new_url = urljoin_rfc(base_url, url)
            request = Request(new_url,
                            callback=self.parse_product)
            request.meta['category'] = category
            yield request

    def parse_product(self, response):
        '''
            Handle information extraction in product page. Loads 
            item in Loader object
        '''
        hxs = HtmlXPathSelector(response)
        name = hxs.select('//div[@id="prodinfo"]/h2/text()').extract()
        if name in self.products_parsed:
            return
        base_url = get_base_url(response)

        img_url = hxs.select('//img[@id="prodphoto"]/@src').extract()
        img_url_final = urljoin_rfc(base_url, img_url[0])

        product_id = response.url.split('/')[-1]

        # unavailable = hxs.select(
        #                        '//form[@id="buyoptions"]//em/text()').\
        #                                                        extract()
        # if unavailable:
        #    logging.error("UNAVAILABLE")
        #    logging.error(product_id)

        if name not in self.products_parsed:
            identifier = '%s - %s' % (product_id, name[0])

            loader = ProductLoader(response=response, item=Product())
            loader.add_value('name', name)
            loader.add_value('url', response.url)
            loader.add_xpath('price',
                        '//div[@id="price"]//div[@id="prodprice"]/text()')
            loader.add_value('image_url', img_url_final)
            # loader.add_value('metadata', 'Product ID: %s' % product_id)
            try:
                loader.add_value('category', response.meta['category'])
            except KeyError:
                pass
            loader.add_value('shipping_cost', 'Not Available')
            loader.add_value('identifier', identifier)
            if name and is_number(product_id):
                yield loader.load_item()
