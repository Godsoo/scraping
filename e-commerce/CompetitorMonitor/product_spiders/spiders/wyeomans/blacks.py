import re
from decimal import Decimal

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

class BlacksSpider(BaseSpider):
    name = 'wyeomans-blacks.co.uk'
    allowed_domains = ['blacks.co.uk']
    start_urls = ['http://www.blacks.co.uk']

    def start_requests(self):
        yield Request('http://www.blacks.co.uk', callback=self.parse_categories)

    def parse_categories(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = hxs.select('//div[@class="template_dropdown_pod"]//a')
        for category in categories:
            url = category.select('./@href').extract()
            if url:
                meta = response.meta
                category_name = category.select('./text()').extract()
                if not category_name:
                    category_name = category.select('./@class').extract()
                meta['category'] = re.sub(' {2,}', ' ', category_name[0].capitalize()) if category_name else ''
                yield Request(urljoin_rfc(base_url, url[0]), meta=meta)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        subcategories = hxs.select('//ul[@class="template_display_categories"]//a[@class="no-ajax"]/@href').extract()
        for url in subcategories:
            yield Request(urljoin_rfc(base_url, url[0]), meta=response.meta)

        next_page = hxs.select('//li[@class="paging_totals"]/a[contains(text(),"NEXT")]/@href').extract()
        if next_page:
            yield Request(urljoin_rfc(base_url, next_page[0]), meta=response.meta)

        products = hxs.select('//div[contains(@class,"productitem")]/h2/a/@href').extract()
        for url in products:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product, meta=response.meta)

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

        options = hxs.select('//div[@class="details_attributes"]//select[contains(@name,"details") and contains(@name,"other")]//option/@value').extract()
        for url in options:
            yield Request(urljoin_rfc(base_url, url), meta=response.meta, callback=self.parse_product)
        current_option = options = hxs.select('//div[@class="details_attributes"]//select[contains(@name,"details") and contains(@name,"other")]//option[@selected]/text()').extract()
        current_option = ' - {}'.format(current_option[0].strip()) if current_option else ''
        sizes = hxs.select('//select[contains(@name,"attributes")]/option')
        if sizes and len(sizes) > 1:
            for option in sizes[1:]:
                product_loader = ProductLoader(item=Product(), selector=hxs)
                size = option.select('./text()')[0].extract()
                size = size if 'one size' not in size.lower() else ''
                product_loader.add_value('name', u'{}{} {}'.format(name[0].strip(), current_option, size))
                product_loader.add_value('url', response.url)
                product_loader.add_value('brand', brand)
                product_loader.add_value('identifier', '{}.{}'.format(product_id, option.select('./@value')[0].extract()))
                product_loader.add_value('sku', product_id)
                if image_url:
                    product_loader.add_value('image_url', image_url)
                product_loader.add_value('category', response.meta.get('category') or '')
                product_loader.add_value('price', price)
                shipping_cost = product_loader.get_output_value('price') <= Decimal(60.00)
                product_loader.add_value('shipping_cost', '3.99' if shipping_cost else '0.00')
                yield product_loader.load_item()
        else:
            product_loader = ProductLoader(item=Product(), selector=hxs)
            product_loader.add_value('name', u'{} {}'.format(name[0].strip(), current_option))
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
