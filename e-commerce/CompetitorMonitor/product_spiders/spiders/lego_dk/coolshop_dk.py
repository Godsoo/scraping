
from scrapy.spider import BaseSpider
from scrapy.http import Request, FormRequest
from scrapy.selector import HtmlXPathSelector
from product_spiders.items import Product, ProductLoaderWithNameStripEU as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price_eu
import re
import json


class CoolshopDkSpider(BaseSpider):
    name = 'coolshop.dk'
    allowed_domains = ['coolshop.dk']
    start_urls = ('https://www.coolshop.dk/leget%C3%B8j/lego,lego/',)
    errors = []

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        total = int(hxs.select('//header[@id="search-header"]//span[@class="qty"]/text()').re(r'\((\d+)\)').pop())
        csrf_token = hxs.select('//form[@id="newsletterform"]//input[@name="csrfmiddlewaretoken"]/@value').extract()[0]
        new_relic_id = re.search(r'loader_config=\{xpid:"(.*?)"\}', response.body).group(1)

        headers = {
            'Host': 'www.coolshop.dk',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'X-NewRelic-ID': new_relic_id,
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'X-CSRFToken': csrf_token,
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': 'https://www.coolshop.dk/leget%C3%B8j/lego/',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache',
        }

        response.meta['ajax_headers'] = headers
        response.meta['current_start'] = 0
        response.meta['total'] = total

        for item in self.parse_products(response):
            yield item

    def parse_products(self, response):

        try:
            data = json.loads(response.body)
            hxs = HtmlXPathSelector(text=data['html'])
        except:
            hxs = HtmlXPathSelector(response)

        base_url = get_base_url(response)
        meta = response.meta.copy()
        if (int(meta['current_start']) + 30) < int(meta['total']):
            meta['current_start'] = int(meta['current_start']) + 30
            form_request = FormRequest(response.url,
                formdata={'start': str(meta['current_start'])},
                headers=meta['ajax_headers'],
                dont_filter=True,
                meta=meta,
                callback=self.parse_products)
            yield form_request

        products = hxs.select('//div[contains(@class,"productitem")]/a[1]/@href').extract()
        for url in products:
            yield Request(urljoin_rfc(base_url, url),
                          callback=self.parse_product,
                          meta={'dont_merge_cookies': True})

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        product_loader = ProductLoader(item=Product(), response=response)
        in_stock = hxs.select('//div[contains(@class, "product-stock")]/div/@data-stock').extract()
        if not in_stock:
            product_loader.add_value('stock', 0)
        elif 'in-stock' not in in_stock[0]:
            product_loader.add_value('stock', 0)
        identifier = map(unicode.strip,
            hxs.select('//div[@id="productAttributes"]/table//td[contains(text(), '
                       '"SKU")]/following-sibling::td/text()').extract())
        product_loader.add_value('identifier', identifier)
        image_url = hxs.select('//a[@rel="productImages" and @class="image"]/@href').extract()[-1]
        product_loader.add_value('image_url', urljoin_rfc(base_url, image_url))
        product_name = response.css('.product-title h1::text').extract_first()
        product_loader.add_value('name', product_name)
        sku = ''
        for match in re.finditer(r"([\d,\.]+)", product_name):
            if len(match.group()) > len(sku):
                sku = match.group()
        product_loader.add_value('sku', sku)
        url = response.url
        product_loader.add_value('url', urljoin_rfc(base_url, url))
        price = response.xpath('//meta[@property="product:price:amount"]/@content').extract_first()
        if price:
            product_loader.add_value('price', price)
            yield product_loader.load_item()
