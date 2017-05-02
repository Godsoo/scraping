
try:
    from scrapy.spiders import Spider as BaseSpider
except ImportError:
    from scrapy.spider import BaseSpider

from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc, add_or_replace_parameter

from product_spiders.items import Product
from bablas_item import ProductLoader


class FirstClassWatchesSpider(BaseSpider):
    name = 'firstclasswatches.co.uk'
    allowed_domains = ['firstclasswatches.co.uk']
    download_delay = 0.1

    def start_requests(self):
        yield Request('http://www.firstclasswatches.co.uk/allbrands.php?currency_override=1',
                      meta={'dont_merge_cookies': True})
        yield Request('http://www.firstclasswatches.co.uk/sale-watches.html', meta={'dont_merge_cookies': True})

    def parse(self, response):
        base_url = get_base_url(response)

        brand_urls = set(response.xpath(u'//div[@id="allbrands"]//a/@href').extract())
        for url in brand_urls:
            url = add_or_replace_parameter(urljoin_rfc(base_url, url), 'sort_by', 'default')
            url = add_or_replace_parameter(url, 'per_page', '180')
            url = add_or_replace_parameter(url, 'show_stock', 'y')
            yield Request(url, meta={'dont_merge_cookies': True})

        categories = response.xpath('//div[@id="category_feature"]//a/@href').extract()
        for url in categories:
            yield Request(urljoin_rfc(base_url, url))

        product_urls = response.xpath(u'//a[@class="listingproduct"]/@href').extract()
        for url in product_urls:
            url = add_or_replace_parameter(urljoin_rfc(base_url, url), 'currency_override', '1')
            yield Request(url, callback=self.parse_product, meta={'dont_merge_cookies': True})

        next_page = response.xpath(u'//div[@class="next"]/a/@href').extract()
        if next_page:
            url = add_or_replace_parameter(urljoin_rfc(base_url, next_page[0]), 'sort_by', 'default')
            url = add_or_replace_parameter(url, 'per_page', '180')
            url = add_or_replace_parameter(url, 'show_stock', 'y')
            yield Request(url, meta={'dont_merge_cookies': True})

    def parse_product(self, response):
        loader = ProductLoader(item=Product(), response=response)

        sku = response.xpath(u'//meta[@itemprop="mpn"]/@content').extract()[0].strip()
        identifier = response.xpath('//meta[@itemprop="sku"]/@content').extract()[0]

        category = response.xpath('//div[@id="breadcrumbs"]/span/a/span/text()').extract()
        category = category[-1].strip() if category else ''

        stock = None
        stock_text = response.xpath("//span[@class='availability']/text()").extract()
        if stock_text:
            stock_text = stock_text[0]
            if 'outofstock' in stock_text.lower():
                stock = 0
            elif 'Discontinued' in stock_text.title():
                return

        loader.add_value('identifier', identifier)
        loader.add_xpath('name', u'//h1[@itemprop="name"]/text()')
        brand = response.xpath(u'//div[@id="brandlogo"]/a/@title').extract()
        brand = brand[0].strip() if brand else ''
        loader.add_value('brand', brand)
        loader.add_value('category', category)
        loader.add_value('sku', sku)
        loader.add_value('stock', stock)
        loader.add_value('url', response.url)
        price = response.xpath(u'//div[@class="nosto_product"]//span[@class="price"]/text()').extract()
        price = price[0] if price else '0.00'
        loader.add_value('price', price)
        image = response.xpath('//div[@id="imgpreload"]/img/@src').extract()
        image = urljoin_rfc(get_base_url(response), image[0]) if image else ''
        loader.add_value('image_url', image)
        yield loader.load_item()
