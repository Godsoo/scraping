from scrapy import Spider, Request
from product_spiders.lib.schema import SpiderSchema
from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader,
)


class AvenuedesjeuxSpider(Spider):
    name = 'legofrance-avenuedesjeux.com'
    allowed_domains = ['avenuedesjeux.com']
    start_urls = ('http://www.avenuedesjeux.com/s/lego?ordre=&np=0&limit=220&q=lego&mar=1',
                  'http://www.avenuedesjeux.com/s/lego?ordre=&np=0&limit=220&q=lego&mar=111',)

    def parse(self, response):
        product_urls = response.xpath('//a[@title="Voir le produit"]/@href').extract()
        for url in product_urls:
            yield Request(response.urljoin(url), callback=self.parse_product)

        pagination = response.xpath('//a[@class="pager"]/@href').extract()
        for page in pagination:
            yield Request(response.urljoin(page))

    def parse_product(self, response):
        schema = SpiderSchema(response)
        product_data = schema.get_product()
        breadcumbs_data = filter(lambda i: i.get('type') == 'http://data-vocabulary.org/Breadcrumb', schema.data['items'])[0]
        identifier = response.xpath(u'//div[contains(@class, "feature-detail")]//strong[contains(text(), "R\xe9f\xe9rence")]/following-sibling::span/text()').extract()[0].partition('-')[-1]
        l = ProductLoader(item=Product(), response=response)
        l.add_value('identifier', identifier)
        l.add_value('name', ' '.join(product_data['name'].split()))
        l.add_value('brand', 'Lego')
        l.add_value('category', breadcumbs_data['properties']['title'][-2])
        l.add_value('sku', identifier)
        l.add_value('url', response.url)
        l.add_value('price', product_data['offers']['properties']['price'])
        l.add_xpath('image_url', '//img[@itemprop="image"]/@src')
        if product_data['offers']['properties']['availability'] == 'http://schema.org/OutOfStock':
            l.add_value('stock', 0)
        yield l.load_item()
