import re
import json

# from scrapy.spider import BaseSpider
from scrapy.contrib.spiders import SitemapSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


class TwoTToysSpider(SitemapSpider):
    name = '2ttoys.nl'
    allowed_domains = ['2ttoys.nl']
    # start_urls = ['http://2ttoys.nl/']

    sitemap_urls = ['http://2ttoys.nl/sitemap.xml']
    sitemap_rules = [
        ('/', 'parse_product'),
    ]

    def start_requests(self):
#        yield Request('http://www.2ttoys.nl/contents/nl/p3144.html', callback=self.parse_product)
#        return

        yield Request(u'http://2ttoys.nl/contents/nl/load_index2.html',
                      callback=self.parse_categories)

        for request in list(super(TwoTToysSpider, self).start_requests()):
            yield request

    def parse_categories(self, response):
        categories = json.loads(re.search('arr=(.*);', response.body).group(1))[:-3]
        for category in categories:
            if u'lego' in category[1].lower():
                yield Request(u'http://2ttoys.nl/contents/nl/' + category[1])

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        categories = hxs.select('//div[@id="PageContainer1"]/div[@id="PageIntroduction-D2"]//a/@href').extract()
        categories += hxs.select(u'//div[@itemprop="description"]//a/@href').extract()
        categories += hxs.select('//div[@class="ProductContainer2"]//p[@align="center"]/a/@href').extract()

        for category in categories:
            if category.endswith('.png') or category.endswith('.jpg') or category.endswith('.bmp') or category.endswith('.gif'):
                continue
            yield Request(urljoin_rfc(get_base_url(response), category))

        for product in self.parse_product(response):
            yield product

        for page in hxs.select('//a[contains(@class, "NextPreviousLink")]/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), page))

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        category = hxs.select(u'//div[contains(@class,"Breadcrumbs")]/nobr//span/text()').extract()
        category = u' > '.join(category)

        if hxs.select('//div[@id="ProductContainer9"]'):
            return

        for product in hxs.select(u'//form[@name="productForm"]//div[@itemscope="itemscope"]'):
            loader = ProductLoader(item=Product(), selector=product)

            identifier = product.select(u'.//*[@itemprop="name"]/@id').re(u'ProductTitle-P(\d+)')
            if not identifier:
                identifier = product.select(u'.//meta[@itemprop="productID"]/@content').extract()
            if identifier:
                identifier = identifier[0]
            else:
                continue
            loader.add_value('identifier', identifier)
            sku = product.select(u'.//meta[@itemprop="productID"]/@content')[0].extract()
            sku = re.search(u'(\d+)', sku)
            if sku:
                sku = sku.group(1)
                loader.add_value('sku', sku)
            loader.add_value('url', response.url)
            name = ''.join(product.select(u'.//div[contains(@id,"ProductIntroduction-P")]//text()').extract()).strip()
            if not name or (name and not ('lego' in name.lower())):
                continue
            loader.add_value('name', name)
            price = product.select(u'.//meta[@itemprop="price"]/@content').extract()
            if price:
                price = price[0].strip().replace('.', '').replace(',', '.')
            else:
                price = '0.00'
            loader.add_value('price', price)
            loader.add_value('category', category)

            img = product.select('div/div//a[contains(@id, "ProductThumbnailImage")]/img/@src').extract()
            if not img:
                img = product.select(u'.//a[contains(@id,"ProductThumbnail")]/img/@src').extract()
            if img:
                loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))

            loader.add_value('brand', 'lego')
            yield loader.load_item()
