import re
import os

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from product_spiders.items import Product, ProductLoaderWithNameStrip\
                             as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))


class PlumbNationSpider(BaseSpider):

    name = 'tapoutlet-plumbnation.co.uk'
    allowed_domains = ['www.plumbnation.co.uk', 'plumbnation.co.uk']
    start_urls = ('http://www.plumbnation.co.uk/', 'http://www.plumbnation.co.uk/shop-by-brand.php')

    errors = []

    def parse(self, response):
        if not isinstance(response, HtmlResponse):
            return
        hxs = HtmlXPathSelector(response)

        urls = hxs.select('//ul[@class="navVertical"]/li/a/@href').extract()
        for url in urls:
            url = urljoin_rfc(get_base_url(response), url)
            request = Request(url, callback=self.parse_product_list)
            yield request

    def parse_product_list(self, response):
        if not isinstance(response, HtmlResponse):
            return
        hxs = HtmlXPathSelector(response)
        cat_urls = hxs.select('//ul[contains(@class, "categories")]/li//a/@href').extract()
        for url in cat_urls:
            url = urljoin_rfc(get_base_url(response), url)
            request = Request(url, callback=self.parse_product_list)
            yield request

        brands = hxs.select('//div[@class="manufacturers"]/ul/li/ul/li/a')
        for brand in brands:
            url = urljoin_rfc(get_base_url(response), brand.select('@href').extract()[0])
            brand_name = brand.select('text()').extract()[0]
            request = Request(url, callback=self.parse_brand, meta={'brand':brand_name})
            yield request

    def parse_brand(self, response):
        hxs = HtmlXPathSelector(response)

        meta = response.meta

        prod_urls = hxs.select('//ul[contains(@class, "products")]/li//span[contains(@class, "name")]/a/@href').extract()
        for url in prod_urls:
            url = urljoin_rfc(get_base_url(response), url)
            request = Request(url, callback=self.parse_product, meta=meta)
            yield request

        urls = hxs.select('//div[@class="pagination"]//ul[@class="navHorizontal"]/li/a/@href').extract()
        for url in urls:
            url = urljoin_rfc(get_base_url(response), url)
            request = Request(url, callback=self.parse_brand, meta=meta)
            yield request

    def parse_product(self, response):
        if not isinstance(response, HtmlResponse):
            return
        hxs = HtmlXPathSelector(response)
        meta = response.meta

        category = hxs.select('//span[@itemprop="title"]/text()').extract()[-1]
        try:
            image_url = hxs.select('//div[@id="productMainImage"]/a/img/@src').extract()[0]
        except:
            image_url = None
        brand = meta.get('brand')


        prod_name = [p for p in hxs.select('//div[@id="productSpecification"]/div/table/tr[1]/td[2]/text()').extract() if p.strip()]
        if prod_name:
            mpn = ''.join(hxs.select('//*[@id="productSpecification"]/div/table/tr[td/text()="Manufacturer Code"]/td[@class="productAttributeValue"]/text()').extract())
            url = response.url
            url = urljoin_rfc(get_base_url(response), url)

            pprice = hxs.select('//div[@id="productPriceInformation"]//span[@class="productPrice"][1]/text()').extract()
            if pprice:
                price = pprice[0]
            else:
                self.errors.append('WARNING: No price in %s' % response.url)
                return

            loader = ProductLoader(item=Product(), selector=hxs)
            if image_url:
                loader.add_value('image_url', image_url)
            loader.add_value('category', category)
            if brand:
                loader.add_value('brand', brand)
            loader.add_value('url', url)
            loader.add_value('name', prod_name[0])
            identifier = hxs.select('//div[@id="productSpecification"]/div/table/tr[2]/td[2]/text()').extract()
            sku = ''.join(hxs.select('//tr[td/text()="Manufacturer Code"]/td[@class="productAttributeValue"]/text()').extract())
            if identifier:
                loader.add_value('sku', sku.replace(' ', ''))
                loader.add_value('identifier', identifier[0])

            loader.add_value('price', price)

            yield loader.load_item()
        else:
            # several productSpecification
            prods = hxs.select('//div[@id="productMultiples"]//li[contains(@class, "multipleProduct")]')
            for prod in prods:
                try:
                    mpn = prod.select('.//td[contains(@class, "productAttributeName") and contains(text(), '
                                      '"Mfr Code")]/following-sibling::td[contains(@class, "productAttributeValue")]'
                                      '/text()').extract()[0].strip()
                except:
                    mpn = ''
                url = prod.select('.//div[contains(@class, "productPriceInformation")]/a/@href').extract()
                url = urljoin_rfc(get_base_url(response), url[0])
                if url:
                    loader = ProductLoader(item=Product(), selector=hxs)
                    loader.add_value('url', url)

                    name = prod.select('.//div[contains(@class, "productPriceInformation")]/a/text()').extract()
                    if name:
                        if not mpn in name[0]:
                            loader.add_value('name', ' '.join((name[0], mpn)))
                        else:
                            loader.add_value('name', name[0])
                        # loader.add_value('name', name[0])

                    identifier = prod.select('.//td[contains(@class, "productAttributeName") and contains(text(), '
                                             '"Product Code")]/following-sibling::td[contains(@class, "productAttributeValue")]'
                                             '/text()').extract()
                    if identifier:
                        match = re.search('(\d+)', identifier[0])
                        identifier = match.group(1)
                        if mpn:
                            loader.add_value('sku', mpn.replace(' ', ''))
                        loader.add_value('identifier', identifier)
                        loader.add_value('image_url', image_url)
                        loader.add_value('category', category)
                        loader.add_value('brand', brand)

                    pprice = prod.select('.//p/span[@class="productPrice"]/text()').extract()
                    if pprice:
                        loader.add_value('price', pprice[0])
                    else:
                        self.errors.append('WARNING: No price in %s' % response.url)

                    yield loader.load_item()
