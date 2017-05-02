import os
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from urlparse import urljoin as urljoin_rfc
from product_spiders.items import Product, ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))


class AnglingDirectSpider(BaseSpider):
    name = 'anglingdirect.co.uk'
    allowed_domains = ['www.anglingdirect.co.uk']
    start_urls = ('http://www.anglingdirect.co.uk/store/catalog/seo_sitemap/product/',)

    def __init__(self, *args, **kwargs):
        super(AnglingDirectSpider, self).__init__(*args, **kwargs)

    def parse(self, response):
        if not isinstance(response, HtmlResponse):
            return
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        # pages
        pages = hxs.select('//div[@class="pager"]//a/@href').extract()
        for url in pages:
            url = urljoin_rfc(base_url, url)
            yield Request(url)

        # products
        products = hxs.select('//ul[@class="sitemap"]//a/@href').extract()
        for url in products:
            url = urljoin_rfc(base_url, url)
            yield Request(url, callback=self.parse_product)

    def parse_product(self, response):
        if not isinstance(response, HtmlResponse):
            return

        hxs = HtmlXPathSelector(response)

        identifier = hxs.select('//input[@name="product"]/@value').extract()
        name = hxs.select('//div[@class="product-name"]/h1/text()').extract()
        if not identifier or not name:
            retry_count = int(response.meta.get('retry_count', '0'))
            retry_count += 1
            if retry_count < 10:
                yield Request(response.url, callback=self.parse_product, meta={'retry_count': retry_count})
            else:
                self.log('Warning! Maximum retry count reached: {}'.format(response.url))
            return
        identifier = identifier[0]
        name = name[0]
        image_url = hxs.select('//*[contains(@class, "product-image")]//*[@id="zoom1"]/img/@src').extract()
        if image_url and not image_url[0].strip().startswith('data:image'):
            image_url = urljoin_rfc(get_base_url(response), image_url[0])
        else:
            image_url = ''
        category = hxs.select(u'//div[contains(@class, "breadcrumbs")]//a/text()').extract()
        category = category[-1] if category else ''

        brand = hxs.select(u'//th[contains(text(),"Manufactured By")]/following-sibling::td/text()').extract()
        if not brand:
            brand = hxs.select('//div[@class="box-brand"]//img/@alt').extract()

        multiple_options = response.xpath('//table[starts-with(@id, "super-product-table")]')

        if multiple_options:
            try:
                no_options = multiple_options.select(u'.//td[position()=1]/text()')[0].extract()
            except:
                multiple_options = []
        else:
            no_options = ''

        if not multiple_options or no_options == 'No options of this product are available.':
            if hxs.select(u'//div[@class="title invstatus-out-stock-disc"]/text()'): # the item should be delisted
                self.log('Delisted item {}'.format(response.url))
                return
            if hxs.select(u'//div[contains(@class,"title invstatus-due-stock")]/text()'):
                stock = 0
            else:
                stock = hxs.select(u'//div[@class="title invstatus-in-stock" or @class="title invstatus-in-stock-disc"]/text()')
                stock = stock[0].re(u'(\d+)') if stock else []

            sku = hxs.select(u'//td[contains(text(),"Model")]/following-sibling::td/text()').extract()
            if not sku:
                sku = hxs.select('//th[@class="label" and contains(text(), "Manufacturer Product ID")]/following-sibling::td/text()').extract()
            if not sku:
                hxs.select('//th[@class="label" and contains(text(), "Model")]/following-sibling::td/text()').extract()
            product_loader = ProductLoader(item=Product(), response=response)
            product_loader.add_value('name', name)
            product_loader.add_value('url', response.url)
            product_loader.add_value('identifier', identifier)
            if sku:
                product_loader.add_value('sku', sku[0])
            product_loader.add_value('category', category)
            product_loader.add_value('stock', int(stock[0]) if stock else 0)
            product_loader.add_value('brand', brand)
            product_loader.add_value('image_url', image_url)
            price = hxs.select('//p[@class="special-price"]/span[@class="price"]/text()').extract()
            if not price:
                price = hxs.select('//span[@class="regular-price"]/span[@class="price"]/text()').extract()
            if price:
                price = price[0]
            else:
                price = '0'
            product_loader.add_value('price', price)
            yield product_loader.load_item()
        else:
            for option in multiple_options.select('//tbody//tr'):
                try:
                    option_id = option.select('.//div[@class="price-box"]//span[contains(@id, "product-price-")]/@id').re(r'product-price-(\w+)')[0]
                except:
                    continue

                if option.select(u'.//div[contains(@class,"invstatus-out-stock-disc")]/text()'):
                    self.log('Delisted item: {}'.format(response.url))
                    #continue

                if option.select(u'.//div[contains(@class,"invstatus-due-stock")]/text()') \
                    or option.select(u'.//p[contains(@class,"availability") and contains(@class, "out-of-stock")]'):
                        stock = 0
                else:
                    stock = option.select(u'.//div[contains(@class,"invstatus-in-stock")]/text()').re(u'(\d+)')

                option_identifier = identifier + '-' + option_id
                product_loader = ProductLoader(item=Product(), selector=option)
                option_name = option.select(u'./td[position()=1]/text()')[0].extract()
                product_loader.add_value('name', name + ' ' + option_name)
                product_loader.add_value('url', response.url)
                price = option.select(u'.//div[@class="price-box"]//span[contains(@id, "product-price-")]//text()').re(r'[\d.,]+')
                if not price:
                    price = option.select(u'.//div[@class="price-box"]/span[contains(@id, "product-price-")]/span/text()').extract()
                if not price:
                    price = option.select(u'.//*[contains(@id, "product-price-")]//text()').extract()
                product_loader.add_value('price', price)
                product_loader.add_value('identifier', option_identifier)
                product_loader.add_value('stock', int(stock[0]) if stock else 0)
                try:
                    option_sku = option.select(u'.//td[position()=1]/text()')[0].extract()
                    product_loader.add_value('sku', option_sku)
                except:
                    pass
                product_loader.add_value('brand', brand)
                product_loader.add_value('category', category)
                product_loader.add_value('image_url', image_url)
                yield product_loader.load_item()
