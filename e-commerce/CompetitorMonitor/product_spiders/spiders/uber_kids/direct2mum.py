"""
Uber Kids account
Direct2Mum spider
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4845
"""


from scrapy import Spider, Request
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
from scrapy.utils.url import add_or_replace_parameter


class Direct2Mum(Spider):
    name = 'uberkids-direct2mum'
    allowed_domains = ['direct2mum.co.uk']
    start_urls = ['https://www.direct2mum.co.uk/Products?IncludeUnableToOrder=False&SortBy=BestSelling&PageSize=1000&PageNumber=1']

    def parse(self, response):
        product_urls = response.xpath('//div[@id="productItems"]/div[contains(@class, '
                                      '"productGridArea")]/div[contains(@class, "gridPricing")]/a/@href')\
                               .extract()
        for url in product_urls:
            yield Request(response.urljoin(url), callback=self.parse_product)

        if product_urls:
            next_page = int(response.meta.get('page_no', 1)) + 1
            url = add_or_replace_parameter(response.url, 'PageNumber', str(next_page))
            yield Request(url, meta={'page_no': next_page})

    def parse_product(self, response):
        for url in response.css('.facet-nav a::attr(href)').extract():
            yield Request(response.urljoin(url), self.parse_product)

        xpath = '//meta[@property="%s"]/@content'
        loader = ProductLoader(item=Product(), response=response)
        loader.add_xpath('identifier', xpath %'product:retailer_part_no')
        loader.add_xpath('url', '//link[@rel="canonical"]/@href')
        loader.add_xpath('name', xpath %'og:title')
        #loader.add_xpath('name', xpath %'product:color')
        loader.add_xpath('price', xpath %'product:price:amount')
        loader.add_xpath('sku', xpath %'product:retailer_part_no')
        category = response.xpath('//ul[@itemprop="breadcrumb"]//a/text()').extract()
        category.remove('Home')
        category.remove('Products')
        category.pop(-1)
        loader.add_value('category', category[-3:])
        loader.add_xpath('image_url', xpath %'og:image')
        loader.add_xpath('brand', xpath %'product:brand')
        if loader.get_output_value('price') < 50:
            loader.add_value('shipping_cost', '3.99')

        item = loader.load_item()
        if item.get('identifier'):
            yield item
