import re
from decimal import Decimal

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


class BlacksSpider(BaseSpider):
    name = 'blacks-blacks.co.uk'
    allowed_domains = ['blacks.co.uk']
    start_urls = ['http://www.blacks.co.uk/mens/mens-clothing/jackets-coats/']


    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        meta = response.meta

        subcategories = hxs.select('//ul[@class="template_display_categories"]//a[@class="no-ajax"]/@href').extract()
        for url in subcategories:
            yield Request(urljoin_rfc(base_url, url[0]), meta=meta)

        next_page = hxs.select('//li[@class="paging_totals"]/a[contains(text(),"NEXT")]/@href').extract()
        if next_page:
            yield Request(urljoin_rfc(base_url, next_page[0]), meta=meta)

        products = hxs.select('//div[contains(@class,"productitem")]/h2/a/@href').extract()
        if products:
            category = hxs.select('//h1/span/text()').extract()[0]
            meta['category'] = category
            for url in products:
                yield Request(urljoin_rfc(base_url, url), callback=self.parse_product, meta=meta)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        base_url = get_base_url(response)

        try:
            product_id = hxs.select('//div[@class="details_code"]/strong/text()').re('#(.*)')[0]
        except:
            retry = int(response.meta.get('retry', 0))
            if retry < 10:
                retry += 1
                new_meta = response.meta.copy()
                new_meta['retry'] = retry
                yield Request(response.url, meta=new_meta, callback=self.parse_product, dont_filter=True)
            return

        name = hxs.select('//div[@class="template_main"]//h1/text()').extract()
        image_url = hxs.select('//img[@rel="v:photo"]/@src').extract()
        if image_url:
            image_url = urljoin_rfc(base_url, image_url[0])

        brand = hxs.select('//form/fieldset/div/h2/text()').extract()
        brand = brand[0].capitalize() if brand else ''
        price = hxs.select('//span[@class="details_price_now"]/span/text()').extract()
        if not price:
            price = hxs.select('//div[@class="details_price"]/p/span/text()').extract()
        price = price[0]

        product_loader = ProductLoader(item=Product(), selector=hxs)
        product_loader.add_value('name', name[0].strip())
        product_loader.add_value('url', response.url)
        product_loader.add_value('brand', brand)
        product_loader.add_value('identifier', product_id)
        product_loader.add_value('sku', product_id)
        if image_url:
            product_loader.add_value('image_url', image_url)
        product_loader.add_value('category', response.meta.get('category') or '')
        product_loader.add_value('price', price)
        shipping_cost = product_loader.get_output_value('price') <= Decimal(60.00)
        product_loader.add_value('shipping_cost', '3.99' if shipping_cost else '0.00')

        yield product_loader.load_item()
