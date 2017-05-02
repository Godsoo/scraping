import re
import logging
import urllib

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from scrapy import log

from product_spiders.items import Product
from axemusic_item import ProductLoader


class MoogaudioSpider(BaseSpider):
    name = 'moogaudio.com'
    allowed_domains = ['moogaudio.com']
    start_urls = ('http://www.moogaudio.com',)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        # categories
        for category in hxs.select(u'//ul[@id="suckertree1"]//a'):
            url = urljoin_rfc(get_base_url(response), category.select(u'./@href')[0].extract())
            yield Request(url, meta={'category': category.select(u'./text()')[0].extract()})

        # pagination
        for url in hxs.select(u'//a[contains(@title,"Next Page") and u]/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, meta=response.meta)

        # products
        for url in hxs.select(u'//td[@class="productListing-data"]/a[not(child::*)]/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_product, meta=response.meta)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        redirected_urls = response.meta.get('redirect_urls', None)
        if redirected_urls:
            log.msg('Skips product, redirected url: ' + str(redirected_urls[0]))
            return

        product_loader = ProductLoader(item=Product(), selector=hxs)
        product_loader.add_value('url', response.url)
        product_loader.add_value('identifier', re.search('p-(\d+)\.html', response.url).group(1))
        name = hxs.select(u'//td[@class="pageHeading" and @valign="top" and not(@align)]/text()').extract()[0]
        product_loader.add_value('name', name)
        price = ''.join(hxs.select(u'//td[@class="pageHeading" and @valign="top" and @align="right"]/text()').extract()).strip()
        if not price:
            price = ''.join(hxs.select(u'//td[@class="pageHeading" and @valign="top" and @align="right"]/span[@class="productSpecialPrice"]/text()').extract())

        product_loader.add_value('price', price)
        product_loader.add_xpath('sku', u'//td[@class="pageHeading" and @valign="top" and not(@align)]/span[@class="smallText"]/text()', re='\[(.*)\]')
        product_loader.add_value('category', response.meta.get('category'))
        image_url = hxs.select(u'//a[contains(@href,"images") and child::img]/@href').extract()
        if image_url:
            image_url = urljoin_rfc(get_base_url(response), image_url[0])
            product_loader.add_value('image_url', image_url)
        # product_loader.add_xpath('brand', u'')

        brand = ''
        brands = hxs.select('//form[@name="manufacturers"]/select/option/text()').extract()
        for brand in brands:
            if '..' in brand:
                incomplete_brand = ' '.join(brand.split()[:-1])
                if incomplete_brand.lower() in name.lower():
                    product_loader.add_value('brand', brand.replace('..', ''))
            else:
                if brand.lower() in name.lower():
                    product_loader.add_value('brand', brand.replace('..', ''))
                    break

        yield product_loader.load_item()
