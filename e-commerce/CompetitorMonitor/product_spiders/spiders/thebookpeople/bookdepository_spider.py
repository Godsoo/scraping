import os
import re
import csv

from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.spider import BaseSpider

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from bookpeoplemeta import BookpeopleMeta

HERE = os.path.abspath(os.path.dirname(__file__))


class BookdepositorySpider(BaseSpider):
    name = 'thebookpeople-bookdepository.com'
    allowed_domains = ['bookdepository.com']
    start_urls = ['http://www.bookdepository.com/']
    rotate_agent = True
    download_delay = 10
    
    def parse(self, response):
        yield FormRequest('http://www.bookdepository.com/',
                          formdata={'selectCurrency': 'GBP'},
                          callback=self.parse_currency,
                          dont_filter=True)

    def parse_currency(self, response):
        with open(os.path.join(HERE, 'thebookpeople.co.uk_products.csv')) as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                search_url = 'http://www.bookdepository.com/search?searchTerm=%s'
                yield Request(search_url % row['sku'], callback=self.parse_product, meta={'cookiejar': i})

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        if hxs.select('//title[contains(text(), "Error")]'):
            tries = response.meta.get('tries', 1)
            if tries > 10:
                self.log('Blank page on ' + response.url)
                return
            self.log('Trying %d for %s' %(tries, response.url))
            yield Request(response.url, meta={'tries':tries+1}, dont_filter=True, callback=self.parse_product)
        urls = hxs.select('//div[@class="tab search"]//h3/a/@href').extract()
        if urls:
            for url in urls:
                yield FormRequest(url, callback=self.parse_product, meta=response.meta, formdata={'selectCurrency': 'GBP'})
            return
        url = response.url.split('?')[0]
        identifier = re.findall(r'/(\d+)$', url)
        if identifier:
            loader = ProductLoader(item=Product(), response=response)
            loader.add_value('identifier', identifier[0])
            loader.add_xpath('name', '//div[@class="item-info"]/h1/text()')
            price = hxs.select('//div[contains(@class, "item-price-wrap")]/span[@class="sale-price"]/text()').re(r'[\d,.]+')
            if not price:
                price = hxs.select('//div[@class="item-info-wrap"]/p[@class="list-price"]/text()').re(r'[\d,.]+')
            if not price:
                price = hxs.select('//div[@class="item-info-wrap"]/p[@class="price"]/text()').re(r'[\d,.]+')

            if price:
                loader.add_value('price', price)
            else:
                loader.add_value('price', '0.00')
            loader.add_value('sku', identifier[0])
            loader.add_value('url', response.url)
            categories = map(unicode.strip, hxs.select('//ol[@class="breadcrumb"]//a/text()').extract())
            loader.add_value('category', categories)
            loader.add_xpath('image_url', '//div[@class="item-img"]/img/@src')
            in_stock = hxs.select('//p[@class="green-text"]')
            if not in_stock:
                loader.add_value('stock', 0)
            item = loader.load_item()
            metadata = BookpeopleMeta()
            pre_order = hxs.select('//div[@class="btn-wrap"]/a[contains(@class, "add-to-basket")]/text()').extract()
            if pre_order and pre_order[0].strip() == 'Pre-order':
                metadata['pre_order'] = 'Yes'
            author = map(unicode.strip, hxs.select('//div[@class="author-info"]/a/text()').extract())
            if author:
                metadata['author'] = ','.join(author)
            format_ = hxs.select('//ul[@class="biblio-info"]/li/label[contains(text(), "Format")]/following-sibling::span/text()').extract()
            if format_:
                metadata['format'] = format_[0].split('|')[0].strip()
            publisher = filter(lambda d: d, map(unicode.strip,
                hxs.select('//ul[@class="biblio-info"]/li/label[contains(text(), "Publisher")]/following-sibling::span//text()').extract()))
            if publisher:
                metadata['publisher'] = publisher[0]
            published = filter(lambda d: d, map(unicode.strip,
                hxs.select('//ul[@class="biblio-info"]/li/label[contains(text(), "Publication date")]/following-sibling::span//text()').extract()))
            if published:
                metadata['published'] = published[0]
            item['metadata'] = metadata
            yield item
        else:
            self.log('NO PRODUCT FOUND: ' + response.url)
