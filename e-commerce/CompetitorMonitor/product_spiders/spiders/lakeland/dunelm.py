from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.response import get_base_url
from urlparse import urljoin

from product_spiders.base_spiders import PrimarySpider
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader

import json, re

class LakelandAmazonSpider(PrimarySpider):
    name = 'dunelm.com'
    allowed_domains = ['dunelm.com']
    start_urls = ['http://www.dunelm.com']

    csv_file = 'lakeland_dunelm_as_prim.csv'

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        for url in hxs.select('//div[contains(@class, "mega-menu")]//a/@href').extract():
            yield Request(urljoin(base_url, url), callback=self.parse_category)

    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        for page in hxs.select('//link[@rel="next"]/@href').extract():
            yield Request(page, callback=self.parse_category)

        subcategories = hxs.select('//a[@class="search-cat__item"]/@href').extract()
        subcategories += hxs.select('//nav[@class="category__menu"]/a/@href').extract()
        for subcat in subcategories:
            yield Request(subcat, callback=self.parse_category)

        for url in hxs.select('//a[contains(@id, "ProductListProductLink")]/@href').extract():
            url = url.split('?')[0]
            yield Request(urljoin(base_url, url), callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        loader = ProductLoader(selector=hxs, item=Product())
        loader.add_value('url', response.url)
        loader.add_xpath('brand', './/dt[text()="Brand"]/following-sibling::dd[1]/text()')
        loader.add_xpath('category', './/div[contains(@class, "breadcrumbs")]//a/text()')

        if hxs.select('//article[@id="product"]'):
            image_url = hxs.select('.//div[@id="amplienceContent"]//img/@src').extract()
            loader.replace_value('image_url', urljoin(base_url, image_url[0]))
            options = hxs.select('//script[@type="text/javascript"]/text()[contains(., "productData")]').extract()
            for item in self.parse_options(hxs, base_url, loader, options):
                yield item

        for product in hxs.select('//article[@class="bdp-item"]'):
            image_url = product.select('.//a[contains(@id, "mainImage")]/img/@src').extract()[0]
            loader.replace_value('image_url', urljoin(base_url, image_url))
            options = product.select('./div/div[1]//script[@type="text/javascript"]/text()').extract()
            for item in self.parse_options(product, base_url, loader, options):
                yield item

    def parse_one_product(self, hxs, base_url, loader):
        if options:
            self.log('Options detected on %s' %loader.get_collected_values('url'))
        image_url = hxs.select('.//div[@id="amplienceContent"]//img/@src').extract()
        loader.add_value('image_url', urljoin(base_url, image_url[0]))
        loader.add_xpath('name', './/h1[@itemprop="name"]//text()')

        loader.add_xpath('identifier', './/article[@id="product"]/@data-product-id')
        loader.add_xpath('sku', './/article[@id="product"]/@data-product-id')

        if not hxs.select('.//div[contains(@id, "stock")]//text()[contains(.,"in-stock")]') and hxs.select('//span[contains(@id, "standardIcon")]/@class[.="icon availability unavailable"]'):
            loader.add_value('stock', 0)
        loader.add_xpath('price', './/strong[@id="fromPrice"]/text()')
        product = loader.load_item()
        if product['price'] < 49:
            product['shipping_cost'] = 3.49
        return product

    def parse_options(self, hxs, base_url, loader, options):
        regx = re.compile('productData(?!.*productData).*? =  ({.+})', re.S)
        options = options[0]
        options = json.loads(re.findall(regx, options)[0])
        for variant in options['skus']:
            loader.replace_value('identifier', variant['id'])
            loader.replace_value('sku', variant['id'])
            loader.replace_value('price', variant['price'])
            loader.replace_value('name', variant['name'].replace('&#034;', '"'))
            for attribute in variant['attributes']:
                if attribute['name'] == 'Colour':
                    colour = attribute['value']
            try:
                loader.replace_value('image_url', urljoin(base_url, options['colour'][colour]))
            except:
                pass
            product = Product(loader.load_item())
            if product['price'] < 49:
                product['shipping_cost'] = 3.49
            formdata = {'dataType':'json', 'quantity':'1', 'storeId':'10151',
                                        'productId':variant['identifier'], 'sku':variant['id']}
            #self.log('Url %s. Formdata %s' %(base_url, formdata))
            yield FormRequest('http://www.dunelm.com/webapp/wcs/stores/servlet/AjaxProductAvailabilityView',
                              dont_filter=True,
                              formdata=formdata,
                              meta={'product':product, 'tries':1}, callback=self.parse_stock)

    def parse_stock(self, response):
        tries = response.meta['tries']
        try:
            stock = json.loads(response.body)
            self.log('Success with %d tries' %tries)
        except:
            tries+=1
            if tries > 50:
                self.log('Gave up retrying stock status for %s' %response.request.headers['Referer'])
                yield response.meta['product']
                return
            self.log('Trying %d get stock status' %tries)
            yield response.request.replace(dont_filter=True,
                                                       meta={'product':response.meta['product'], 'tries':tries})
            return
        deliveries = ('expressAvailableClass', 'rocsAvailableClass', 'standardAvailableClass')
        product = response.meta['product']
        product['stock'] = 0
        for delivery in deliveries:
            if stock[delivery] == "available":
                del product['stock']
                break

        yield product

