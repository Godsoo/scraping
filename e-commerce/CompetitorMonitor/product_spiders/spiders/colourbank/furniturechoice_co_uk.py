import re

from scrapy.selector import HtmlXPathSelector
from scrapy.spider import BaseSpider
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from urlparse import urljoin as urljoin_rfc
from scrapy.http import FormRequest
from w3lib.url import url_query_cleaner, url_query_parameter, add_or_replace_parameter
from product_spiders.utils import extract_price

from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader


class CBFurniturechoiceCoUkSpider(BaseSpider):
    name = 'colourbank-furniturechoice.co.uk'
    allowed_domains = ['furniturechoice.co.uk']
    start_urls = ['http://www.furniturechoice.co.uk/']
    parsed_products = []
    errors = []

    def retry(self, response, error="", retries=3):
        meta = response.meta.copy()
        meta['recache'] = True
        retry = int(meta.get('retry', 0))
        if 'redirect_urls' in meta and meta['redirect_urls']:
            url = meta['redirect_urls'].pop()
        else:
            url = response.request.url
        if retry < retries:
            retry += 1
            meta['retry'] = retry
            return Request(url, dont_filter=True, meta=meta, callback=response.request.callback)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        for url in hxs.select('//ul[@id="main-nav"]//a/@href').extract():
            url = url_query_cleaner(response.urljoin(url))
            yield Request(url, callback=self.parse_product_list)

    def parse_product_list(self, response):
        hxs = HtmlXPathSelector(response)

        categories = hxs.select('//li[@class="PANEL ALL"]//a/@href').extract()
        categories += hxs.select('//li[@class="PANEL BY-SIZE"]//a/@href').extract()
        categories += hxs.select('//li[@class="PANEL BY-TYPE"]//a/@href').extract()
        for url in categories:
            url = url_query_cleaner(response.urljoin(url))
            yield Request(url, callback=self.parse_product_list)

        products = hxs.select('//div[@id="pdList"]//a/@href').extract()
        products += hxs.select('//div[@class="product-tile"]//a/@href').extract()
        for url in products:
            pid = url.split('_')[-1]
            if pid not in self.parsed_products:
                self.parsed_products.append(pid)
                url = url_query_cleaner(response.urljoin(url))
                yield Request(url, callback=self.parse_product)

        product_variants = hxs.select('//div[@class="productVariantTypeOptions"]/a/@href').extract()
        for url in product_variants:
            self.log('productVariantTypeOptions! {}'.format(url))
            pid = url.split('_')[-1]
            if pid not in self.parsed_products:
                self.parsed_products.append(pid)
                url = url_query_cleaner(response.urljoin(url))
                yield Request(url, callback=self.parse_product)

        next_page = None
        cur_page = url_query_parameter(response.url, 'pi', None)
        if cur_page:
            # The spider is already crawling the pages, we just assing the current url
            # so we can increment the 'pi' argument
            next_page = response.url
        else:
            # First page of the product list, we extract the pagination url with regex
            next_page = re.findall('.get\( &quot;(.*)pi=', response.body)
            if next_page:
                next_page = response.urljoin(next_page[0])

        if (next_page and products != response.meta.get('products', [])) or (next_page and product_variants != response.meta.get('product_variants', [])):
            cur_page = url_query_parameter(next_page, 'pi', '1')
            url = add_or_replace_parameter(next_page, 'pi', str(int(cur_page) + 1))
            self.log('Goes to next page: ' + url)
            yield Request(url, callback=self.parse_product_list, meta={'products': products, 'product_variants': product_variants})

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        for url in hxs.select('//div[@class="product-tile"]//a/@href').extract():
            pid = url.split('_')[-1]
            if pid not in self.parsed_products:
                self.parsed_products.append(pid)
                yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)
        product_loader = ProductLoader(item=Product(), selector=hxs)
        product_loader.add_value('url', response.url)
        name = hxs.select('//h1/text()').extract()
        if not name:
            request = self.retry(response, "No name for product: " + response.url)
            if request:
                yield request
            return
        product_loader.add_value('name', name)
        category = hxs.select('//ol[@class="breadcrumbs"]//a/text()').extract()[1:]
        product_loader.add_value('category', category)
        img = hxs.select('//div[@class="item"]//img/@src').extract()
        if img:
            product_loader.add_value('image_url', urljoin_rfc(get_base_url(response), img.pop(0)))

        product = product_loader.load_item()
        options = hxs.select(u'//div[contains(@class, "MainProds")]/ol/li')
        if not options:
            options = hxs.select(u'//div[@class="SingColl"]/div[contains(@class, "Prod")]')
        if True:
            if not options or len(options) == 1:
                prod = Product(product)
                prod['sku'] = hxs.select('//div[@class="product-sku"]/text()').re('Product code: (\w+)').pop()
                prod['identifier'] = prod['sku']
                prod['price'] = extract_price(
                    hxs.select('//div[@class="price-current"]/text()').extract().pop())
                if prod['identifier']:
                    yield prod
            else:
                for opt in options:
                    prod = Product(product)
                    prod['name'] = opt.select(u'normalize-space(.//h2/text())').extract()[0]
                    prod['sku'] = \
                        opt.select(u'normalize-space(substring-after(.//div[@class="code"]/text(), ":"))').extract()[0]
                    prod['identifier'] = prod['sku']
                    prod['price'] = extract_price(opt.select(u'.//span[@class="Price"]/text()').extract()[0])
                    yield prod
