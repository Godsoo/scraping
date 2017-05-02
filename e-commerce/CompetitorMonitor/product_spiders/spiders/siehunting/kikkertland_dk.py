# -*- coding: utf-8 -*-


from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.utils.response import get_base_url
from scrapy.http import Request

from product_spiders.items import ProductLoader, Product

import urlparse
import re

__author__ = 'Theophile R. <rotoudjimaye.theo@gmail.com>'


def xpath_select(hxs, selector):
    parts = selector.replace('//tbody', '/tbody').split('/tbody')
    if len(parts) == 1:
        return hxs.select(selector)
    current = hxs.select(parts[0])
    for s in parts[1:]:
        temp = current.select("./tbody")
        if temp:
            current = temp
        current = current.select("."+s)
    return current



class SpiderTemplate(BaseSpider):
    NAVIGATION = ['//a/@href']
    PRODUCT_BOX = []

    PRICE_RE = re.compile("\d+\.?\d*")

    THOUSAND_SEP = ","
    DECIMAL_SEP = "."
    PRODUCT_URL_EXCLUDE = ()
    NAV_URL_EXCLUDE = ()

    PRODUCT_BOX_XOR = False
    CHECK_PRODUCT_NAME = True
    CHECK_PRICE_IN_PRODUCT_PAGE = False
    
    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        self.visited_urls = set()
        self.product_links = set()
        self.product_names = set()

        for url in self.navigate(hxs, base_url):
            if url in self.product_links: continue
            if url not in self.visited_urls:
                self.visited_urls.add(url)
                yield Request(url, callback=self.parse_products)

    def get_base_url(self, response):
        try:
            return get_base_url(response)
        except: return

    def preprocess_link(self, href):
        return href

    def skip_navigation(self, url):
        for item in self.NAV_URL_EXCLUDE:
            if item in url:
                return True
        return False

    def navigate(self, hxs, base_url):
        links = set()
        for xpath in self.NAVIGATION:
            for href in xpath_select(hxs, xpath).extract():
                url = urlparse.urljoin(base_url, self.preprocess_link(href))
                if url not in self.visited_urls and not self.skip_navigation(url):
                    links.add(url)
        return links

    def keep_product(self, product):
        for item in self.PRODUCT_URL_EXCLUDE:
            if item in product['url']:
                return False
        if self.CHECK_PRODUCT_NAME:
            if product['name'] in self.product_names:
                return False
        return True

    def parse_products(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = self.get_base_url(response)
        if not base_url:
            return

        for xpath, box_spec in self.PRODUCT_BOX:
            product_hxs = xpath_select(hxs, xpath) if xpath and xpath != "." else [hxs]
            found = False
            for product_box in product_hxs:
                found = True
                product_name = xpath_select(product_box, box_spec['name']).extract() if not callable(box_spec['name']) else [box_spec['name'](hxs)]

                if not product_name: continue

                product_link = xpath_select(product_box, box_spec['url']) if box_spec.get('url') else None
                name, url = " ".join([n.strip(' \r\n') for n in product_name if n.strip(' \r\n')]), urlparse.urljoin(base_url, product_link.extract()[0]) if product_link else response.url

                if url in self.product_links: continue

                product_loader = ProductLoader(item=Product(), selector=product_box)

                product_loader.add_value('name', name)
                product_loader.add_value('url', url)

                for price_xpath in box_spec['price']:
                    price = None
                    if callable(price_xpath):
                        try:
                            extracted = str(price_xpath(hxs, name)).strip()
                            price = self.PRICE_RE.findall(extracted.replace(self.THOUSAND_SEP, "").replace(self.DECIMAL_SEP, "."))[0]
                        except: pass
                    else:
                        product_price = xpath_select(product_box, price_xpath)
                        matches = [self.PRICE_RE.findall(e.strip().replace(self.THOUSAND_SEP, "").replace(self.DECIMAL_SEP, ".")) for e in product_price.extract()] if product_price else []
                        for match in matches:
                            if match:
                                price = match[0]
                                break

                    if price:
                        product_loader.add_value('price', price)
                        break

                product = product_loader.load_item()

                if not 'price' in product:
                    product['price'] = None

                product_page = product['url'] == response.url
                if self.keep_product(product):
                    if not product['price'] and not product_page and self.CHECK_PRICE_IN_PRODUCT_PAGE:
                        yield Request(url=product['url'], callback=self.parse_products)
                    else:
                        self.product_links.add(product['url'])
                        self.product_names.add(product['name'])
                        yield product
            #
            if found and self.PRODUCT_BOX_XOR: break

        for url in self.navigate(hxs, base_url):
            if url in self.product_links: continue
            if url not in self.visited_urls:
                self.visited_urls.add(url)
                yield Request(url, callback=self.parse_products)


class KikkertlandSpider(SpiderTemplate):
    name = "kikkertland.dk"
    allowed_domains = ["kikkertland.dk"]
    start_urls = ["http://www.kikkertland.dk/"]

    THOUSAND_SEP = "."
    DECIMAL_SEP = ","

    PRODUCT_BOX_XOR = True

    NAV_URL_EXCLUDE = ('.jpg', '.avi', '.pdf', '.gif', 'action=buy_now', 'checkout_shipping.php', '/account.php', '/account_newsletters.php', '/account_history.php', '/address_book.php', '/account_edit.php')

    NAVIGATION = ['//div[@id="categoryContainer"]//a/@href', '//a[@class="pageResults"]/@href', '//a/@href']
    PRODUCT_BOX = [#('//table[@class="productListing"]//tbody//tr', {'url': './td[2]//a/@href', 'name': './td[2]//a/b/text()', 'price': ['.//span[@class="productSpecialPrice"]/text()', './/div[@class="listPrice"]/text()']}),
                   ('//table[@class="productListing"]//tr[@class="productListing-even"]', {'url': './td[2]//a/@href', 'name': './td[2]//a/b/text()', 'price': ['.//span[@class="productSpecialPrice"]/text()', './/div[@class="listPrice"]/text()']}),
                   ('//table[@class="productListing"]//tr[@class="productListing-odd"]', {'url': './td[2]//a/@href', 'name': './td[2]//a/b/text()', 'price': ['.//span[@class="productSpecialPrice"]/text()', './/div[@class="listPrice"]/text()']}),
                   ('.', {'name': '//div[@id="productInfo"]/div/h1/text()', 'price': ['//div[@id="productInfo"]/div[2]/div[@class="productDescriptionContainer"]/div[3]/table/tbody/tr[2]/td[2]/span[@class="productSpecialPrice"]', '//div[@id="productInfo"]/div[2]/div[@class="productDescriptionContainer"]/div[3]/table/tbody/tr/td[2]/text()', ]}),
    ]