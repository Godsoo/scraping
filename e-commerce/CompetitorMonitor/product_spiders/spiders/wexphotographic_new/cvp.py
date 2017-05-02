"""
Wex Photographic New CVP spider
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4718
"""

import re
from scrapy import Spider, Request, Selector
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
from product_spiders.utils import extract_price2uk


def change_main_category(url):
    return url.replace('department', 'category')


class CVPSpider(Spider):
    name = 'wexphotographicnew-cvp'
    allowed_domains = ['cvp.com']
    start_urls = ['http://cvp.com/index.php?t=helpCentre/sitemap']

    def parse(self, response):
        cat_urls = response.xpath('//a[@class="sitemap_cat" and not(contains(@href, "/used")) '
                                  'and not(contains(@href, "/warranties"))]/@href').extract()
        for url in cat_urls:
            yield Request(response.urljoin(url), callback=self.parse_products)

    def parse_products(self, response):
        for url in response.css('.leftoption :contains("Filter by Manufacturers")').xpath('following-sibling::*//a/@href').extract():
            yield Request(response.urljoin(url), callback=self.parse_products)
        text = re.sub('Estimated *<', 'Estimated &lt;', response.body)
        selector = Selector(text=text)
        category = selector.css('.crumword').xpath('.//*[@itemprop="title"]/text()').extract()
        try:
            identifiers = selector.xpath('//script/text()').re('ecomm_prodid: *\[(.+)\]')[0].replace("'", '').split(',')
        except IndexError:
            return
        next_page_url = response.xpath('//div[@class="pagination"]/a[@class="next"]/@href').extract()
        if next_page_url:
            yield Request(response.urljoin(next_page_url[0]), callback=self.parse_products)
        for num, product in enumerate(selector.css('.grid')):
            loader = ProductLoader(item=Product(), selector=product)
            identifier = identifiers[num]
            loader.add_value('identifier', identifier)
            url = product.xpath('@href').extract_first()
            loader.add_value('url', response.urljoin(url))
            name = product.css('.gridname').xpath('text()').extract()
            loader.add_value('name', name)
            price = product.css('.gridPriceVat').xpath('text()').extract()
            if not price:
                price = 0
            loader.add_value('price', price)
            loader.add_value('sku', identifier)
            loader.add_value('category', category)
            image_url = product.css('.gridimage').xpath('.//@src').extract()
            loader.add_value('image_url', image_url)
            if price and loader.get_output_value('price') < 200:
                loader.add_value('shipping_cost', '4.99')
            if 'in stock' not in product.css('.pItemStock').xpath('text()').extract_first().strip().lower():
                loader.add_value('stock', 0)
            item = loader.load_item()
            if price:
                yield item
            else:
                yield Request(response.urljoin(url), self.parse_product, meta={'product': Product(item)})

    def parse_product(self, response):
        product = response.meta['product'].copy()
        price = response.css('.pdetails .pproductpriceVAT::text').extract_first()
        if price:
            product['price'] = extract_price2uk(price)
        yield product
