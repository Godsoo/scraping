import re
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

import logging


class CurrysSpider(BaseSpider):
    name = 'currys.co.uk-tech'
    allowed_domains = ['currys.co.uk']
    start_urls = [
        'http://www.currys.co.uk/gbuk/televisions/301_3002_30002_xx_xx/xx-criteria.html',
        'http://www.currys.co.uk/gbuk/tv-dvd-blu-ray/digital-tv-services-304-c.html',
        'http://www.currys.co.uk/gbuk/blu-ray-players/303_3016_30016_xx_xx/xx-criteria.html',
        'http://www.currys.co.uk/gbuk/dvd-recorders/303_3017_30017_xx_xx/xx-criteria.html',
        'http://www.currys.co.uk/gbuk/home-cinema-systems/303_3018_30018_xx_xx/xx-criteria.html',
        'http://www.currys.co.uk/gbuk/cameras/digital-cameras-344-c.html',
        'http://www.currys.co.uk/gbuk/cameras/digital-camcorders-347-c.html',
        'http://www.currys.co.uk/gbuk/phones-broadband-gps/home-phones-343-c.html',
        'http://www.currys.co.uk/gbuk/search-keywords/xx_xx_xx_xx_xx/ipod+docking/xx-criteria.html',
        'http://www.currys.co.uk/gbuk/audio/hi-fi-speaker-docks-290-c.html',
        'http://www.currys.co.uk/gbuk/audio/radios-309-c.html',
        'http://www.currys.co.uk/gbuk/audio/portable-audio-313-c.html',
        'http://www.currys.co.uk/gbuk/audio/headphones/headphones-3919-m.html',
        'http://www.currys.co.uk/gbuk/computing/laptops-315-c.html',
        'http://www.currys.co.uk/gbuk/apple-laptops/315_3047_30047_xx_xx/xx-criteria.html',
        'http://www.currys.co.uk/gbuk/ultrabooks/315_3798_31510_xx_xx/xx-criteria.html',
        'http://www.currys.co.uk/gbuk/computing/ipad-tablets-and-ereaders/tablets-3396-m.html',
        'http://www.currys.co.uk/gbuk/computing/ipad-tablets-and-ereaders/apple-ipad-3402-m.html',
        'http://www.currys.co.uk/gbuk/computing/ipad-tablets-and-ereaders/ereaders-3415-m.html'
    ]

    ipod_urls = [
        'http://www.currys.co.uk/gbuk/apple-ipod-1241-commercial.html',
    ]

    def start_requests(self):
        for url in self.start_urls:
            yield Request(url=url, callback=self.parse)
        for url in self.ipod_urls:
            yield Request(url=url, callback=self.parse_ipods)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        URL_BASE = get_base_url(response)

        categories = hxs.select("//nav[contains(@class, 'section_nav')]/ul/li//a/@href").extract()
        for url in categories:
            url = urljoin_rfc(URL_BASE, url)
            request = Request(url, callback=self.parse)
            yield request

        pages = hxs.select("//ul[@class='pagination']//a/@href").extract()
        for url in pages:
            url = urljoin_rfc(URL_BASE, url)
            request = Request(url, callback=self.parse)
            yield request

        category = hxs.select('//span[@class="current"]/text()').extract()[0]
        items = hxs.select("//article[contains(@class, 'product')]")
        for item in items:
            name = item.select(".//div/header[@class='productTitle']/a/text()").extract()
            if not name:
                continue
            name = name[0].strip()
            name = re.sub("[\s]+", " ", name)
            
            identifier = item.select('div/div/input[@name="sFUPID"]/@value').extract()
            if identifier:
                identifier = identifier[0]
            else:
                identifier = item.select('div[@class="productAdditional"]/p/@id').extract()
                if identifier:
                    identifier = identifier[0].split('desc_')[-1]
                else:
                    identifier = ''
           
            url = item.select(".//div/div/header[@class='productTitle']/a/@href").extract()
            if not url:
                logging.error("ERROR! NO URL! URL: %s. NAME: %s" % (response.url, name))
                continue
            url = url[0]
            price = item.select(".//div//span[@class='currentPrice']/ins/text()").extract()
            if not price:
                logging.error("ERROR! NO PRICE! URL: %s. NAME: %s" % (response.url, name))
                continue
            price = price[0].strip()

            l = ProductLoader(item=Product(), selector=item)
            l.add_value('name', name)
            l.add_value('url', url)
            l.add_value('identifier', identifier)
            l.add_value('price', price)
            l.add_value('category', hxs.select('//span[@class="current"]/text()').extract()[0])
            l.add_xpath('image_url', "a/img/@src")
            yield l.load_item()

    def parse_ipods(self, response):
        hxs = HtmlXPathSelector(response)
        items = hxs.select("//article[contains(@class, 'product')]/a[@class='productLink']/@href").extract()
        for url in items:
            yield Request(url=url, callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        url = response.url

        name = hxs.select("//h1[@class='pageTitle']/span/text()").extract()
        if not name:
            logging.error("ERROR! NO NAME! %s" % url)
            return
        name = " ".join(name)
        name = re.sub("[\s]+", " ", name)

        identifier = hxs.select('//input[@name="sFUPID"]/@value').extract()
        if not identifier:
            identifier = response.url.split('-pdt.')[0].split('-')[-1]

        price = ''.join(hxs.select("//div[contains(@class, 'productDetail')]//span[contains(@class, 'currentPrice')]/text()").extract()).strip()
        if not price:
            price = ''.join(hxs.select("//div[contains(@class, 'productDetail')]//span[contains(@class, 'currentPrice')]/ins/text()").extract()).strip()

        if not price:
            logging.error("ERROR! NO PRICE! %s %s" % (url, name))
            return
        
        category = hxs.select('//span[@itemprop="title"]/text()').extract()[-1]
        sku = hxs.select('//meta[@itemprop="identifier"]/@content').extract()[0].replace('sku:', '')

        l = ProductLoader(item=Product(), response=response)
        l.add_value('name', name)
        l.add_xpath('brand', '//span[@itemprop="brand"]/text()')
        l.add_value('identifier', identifier)
        l.add_value('category', category)
        l.add_value('sku', sku)
        l.add_value('url', url)
        l.add_value('price', price)
        l.add_xpath('image_url', '//img[@itemprop="image"]/@src')
        yield l.load_item()
