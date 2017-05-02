import os

from scrapy.http import Request, FormRequest
from scrapy.selector import HtmlXPathSelector
from scrapy.spider import BaseSpider
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


HERE = os.path.abspath(os.path.dirname(__file__))


class JohnLewisSpider(BaseSpider):

    name = 'legouk-johnlewis.com'
    allowed_domains = ['johnlewis.com']
    start_urls = ["http://www.johnlewis.com/brand/view-all/lego/_/N-1z140g1"]


    def start_requests(self):
        country_url = "http://www.johnlewis.com/store/international/ajax/changeCountryAjaxRequest.jsp"
        formdata = {'country': 'GB',
                    'sourceUrl': 'http://www.johnlewis.com/',
                    'switchToggle': 'Change Country Overlay'}
        yield FormRequest(country_url, formdata=formdata, callback=self.parse_country)


    def parse_country(self, response):
        yield Request(self.start_urls[0], callback=self.parse)


    def parse(self, response):

        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        products = hxs.select("//div[@class='products']/div/article//a[@class='product-link'][1]/@href").extract()
        products = list(set(products))
        for url in products:
            yield Request(urljoin_rfc(base_url, url), self.parse_product)

        try:
            next_page = hxs.select('//li[@class="next"]//a[not(@href="#")]/@href').extract()[0]
            next_page = next_page.replace('brand/lego', 'brand/view-all/lego')
            yield Request(url=urljoin_rfc(base_url, next_page))
        except Exception as e:
            pass



    def parse_product(self, response):

        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        name = hxs.select('normalize-space(//*[@itemprop="name"]/text())').extract()[0]
        brand = 'Lego'

        try:
            image_url = urljoin_rfc(base_url,
                                    hxs.select('//div[@id="prod-media-player"]'
                                               '//img/@src').extract()[0].strip())
        except IndexError:
            image_url = ''

        options = hxs.select('//div[@id="prod-multi-product-types"]')

        if options:
            products = options.select('.//div[@class="product-type"]')
            for product in products:
                opt_name = product.select('.//h3/text()').extract()[0].strip()
                try:
                    stock = product.select('//div[contains(@class, "mod-stock-availability")]'
                                           '//p/strong/text()').re(r'\d+')[0]
                except IndexError:
                    stock = 0

                loader = ProductLoader(item=Product(), selector=product)
                sku = hxs.select(u'//div[@id="prod-info-tab"]//dl/dt[contains(text(),"Model name")]/following-sibling::dd/text()').extract()
                if not sku:
                    sku = hxs.select(u'//div[@id="prod-info-tab"]//dl/dt[contains(text(),"Model Number")]/following-sibling::dd/text()').extract()
                if sku:
                    loader.add_value('sku', sku[0].strip())
                loader.add_xpath('identifier', './/div[contains(@class, "mod-product-code")]/p/text()')
                loader.add_value('name', '%s %s' % (name, opt_name))
                loader.add_xpath('category', '//div[@id="breadcrumbs"]//li[@class="last"]/a/text()')
                loader.add_value('image_url', image_url)
                loader.add_value('brand', brand)
                loader.add_value('url', response.url)
                loader.add_xpath('price', './/p[@class="price"]/strong/text()')
                loader.add_value('stock', stock)
                yield loader.load_item()

        else:
            price = ''.join(hxs.select('//ul/li/strong[@class="price"]/text()').extract()).strip()
            if not price:
                price = ''.join(hxs.select('//span[@class="now-price"]/text()').extract()).strip()
                if not price:
                    price = ''.join(hxs.select('//div[@id="prod-price"]//strong/text()').extract()).strip()

            try:
                stock = hxs.select('//div[contains(@class, "mod-stock-availability")]'
                                   '//p/strong/text()').re(r'\d+')[0]
            except IndexError:
                stock = 0

            loader = ProductLoader(item=Product(), response=response)
            sku = hxs.select(u'//div[@id="prod-info-tab"]//dl/dt[contains(text(),"Model name")]/following-sibling::dd/text()').extract()
            if not sku:
                sku = hxs.select(u'//div[@id="prod-info-tab"]//dl/dt[contains(text(),"Model Number")]/following-sibling::dd/text()').extract()
            if sku:
                loader.add_value('sku', sku[0].strip())
            loader.add_xpath('identifier', '//div[@id="prod-product-code"]/p/text()')
            loader.add_value('name', name)
            loader.add_xpath('category', '//div[@id="breadcrumbs"]//li[@class="last"]/a/text()')
            loader.add_value('image_url', image_url)
            loader.add_value('brand', brand)
            loader.add_value('url', response.url)
            loader.add_value('price', price)
            loader.add_value('stock', stock)

            item = loader.load_item()

            if item.get('identifier'):
                yield item
