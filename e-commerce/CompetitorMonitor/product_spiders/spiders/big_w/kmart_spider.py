import re
import time

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc, add_or_replace_parameter, url_query_parameter
from scrapy.utils.response import get_base_url
from scrapy.spider import BaseSpider

from product_spiders.spiders.BeautifulSoup import BeautifulSoup

from scrapy import log

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

def _soup_el_get_attr(soup_el, attr):
    for name, value in soup_el.attrs:
        if name == attr:
            return value


class KmartSpider(BaseSpider):
    name = 'bigw-kmart.com.au'
    allowed_domains = ['kmart.com.au']
    start_urls = ['http://www.kmart.com.au']

    rotate_agent = True
    #user_agent = 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:37.0) Gecko/20100101 Firefox/37.0'

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = hxs.select('//ul[@id="main-menu"]//a/@href').extract()
        categories += hxs.select('//div[contains(@id, "DepartmentLanding")]//a/@href').extract()
        categories += hxs.select('//div[@id="search_facet_category"]//li/a/@href').extract()

        for category in categories:
            yield Request(urljoin_rfc(base_url, category), meta=response.meta)

        js_url = re.findall("SearchBasedNavigationDisplayJS.init\('(.*)'\);", response.body)
        if js_url:
            url = js_url[0] + '&pageSize=500'
            yield Request(url, callback=self.parse_products)

        products = hxs.select('//div[@class="product_name"]/a/@href').extract()

        for product in products:
            yield Request(urljoin_rfc(get_base_url(response), product), callback=self.parse_product, meta=response.meta)

    def parse_products(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        try:
            products = hxs.select('//div[@class="product_name"]/a/@href').extract()
            for product in products:
                yield Request(urljoin_rfc(get_base_url(response), product), callback=self.parse_product, meta=response.meta)

            if len(products)>=500:
                index = int(url_query_parameter(response.url, 'beginIndex', 0))
                url = add_or_replace_parameter(response.url, 'beginIndex', str(index + 500))
                yield Request(url, callback=self.parse_products, meta=response.meta)

        except:
            log.msg('PAGE ERROR >>>')
            log.msg(str(response.body))
            retry = response.meta.get('retry', 0) + 1
            if retry <= 7:
                log.msg('Retry: ' + response.url)
                time.sleep(5)
                yield Request(response.url, dont_filter=True, callback=self.parse_products, meta={'retry': retry})

    def parse_product(self, response):
        hxs = HtmlXPathSelector(text=response.body_as_unicode())

        loader = ProductLoader(response=response, item=Product())

        loader.add_value('url', response.url)
        identifier = hxs.select('//input[@id="catentryId"]/@value').extract()
        loader.add_value('identifier', identifier)
        loader.add_value('sku',identifier)
        loader.add_xpath('name', '//h1[@itemprop="name"]/text()')

        price = ''.join(hxs.select('//div[@itemprop="price"]//span[@class="price"]//text()').extract()).strip()
        loader.add_value('price', price)

        categories = hxs.select('//ul[@class="breadcrumbs"]//li[not(@class="home")]/a/span/text()').extract()[1:]
        loader.add_value('category', categories)

        image_url = hxs.select('//img[@id="productMainImage"]/@src').extract()
        if image_url:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), image_url[0]))

        brand = hxs.select('//li[contains(text(), "BRAND")]/span/text()').extract()
        loader.add_value('brand', brand)

        item = loader.load_item()

        if not item.get('name'):
            log.msg('Using BeautifulSoup: ' + response.url)
            loader = ProductLoader(response=response, item=Product())
            soup = BeautifulSoup(response.body)

            loader.add_value('url', response.url)
            identifier = soup.find('input', attrs={'id': 'catentryId'})
            identifier = _soup_el_get_attr(identifier, 'value')
            loader.add_value('identifier', identifier)
            loader.add_value('sku',identifier)
            name = soup.find('h1', attrs={'itemprop': 'name'}).text
            loader.add_value('name', name)
            categories = [li.a.span.text for li in soup.find('ul', attrs={'class': 'breadcrumbs'}).findAll('li') if li.a][2:]
            loader.add_value('category', categories)
            price = soup.find('div', attrs={'itemprop': 'price'}).find('span', attrs={'class': 'price'}).text
            loader.add_value('price', price)

            image_url = soup.find('img', attrs={'id': 'productMainImage'})
            if image_url:
                image_url = _soup_el_get_attr(image_url, 'src')
                loader.add_value('image_url', urljoin_rfc(get_base_url(response), image_url))

            brand = ''
            for li in soup.findAll('li'):
                if 'BRAND' in li.text.upper():
                    brand = li.span.text
                    break

            loader.add_value('brand', brand)
            item = loader.load_item()
            if item['identifier']:
                yield item
        else:
            if item['identifier']:
                yield item

        if not item.get('name'):
            request = self.retry(response, "No name for product: " + response.url)
            if request:
                yield request
            return



    def retry(self, response, error="", retries=3):
        meta = response.meta.copy()
        retry = int(meta.get('retry', 0))
        if 'redirect_urls' in meta and meta['redirect_urls']:
            url = meta['redirect_urls']
        else:
            url = response.request.url
        if retry < retries:
            retry += 1
            meta['retry'] = retry
            meta['recache'] = True
            return Request(url, dont_filter=True, meta=meta, callback=response.request.callback)

