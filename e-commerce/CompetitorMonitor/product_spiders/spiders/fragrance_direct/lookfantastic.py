from decimal import Decimal

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from fragrance_direct_items import FragranceDirectMeta

def normalize_space(s):
    ''' Cleans up space/newline characters '''
    import re
    return re.sub(r'\s+', ' ', s.replace(u'\xa0', ' ').strip())

class LookFantasticSpider(BaseSpider):
    name = 'fragrancedirect-lookfantastic.com'
    allowed_domains = ['lookfantastic.com']
    start_urls = ['http://www.lookfantastic.com']
    user_agent = "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:38.0) Gecko/20100101 Firefox/38.0"

    def parse(self, response):
        yield Request('http://www.lookfantastic.com/lfint/home.dept?locover=true&switchcurrency=GBP', callback=self.parse2)

    def parse2(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        categories = response.xpath('//nav//a/@href').extract()
        for category in categories:
            yield Request(urljoin_rfc(base_url, category),
                          callback=self.parse_page)

    # Can either a subcategory or product listing page
    def parse_page(self, response):
        hxs = HtmlXPathSelector(response)

        # Try to find products
        products = response.css('div#divSearchResults div.item p.product-name a::attr(href)').extract()
        if products:
            category = ' > '.join(hxs.select('//div[@class="breadcrumbs"]/ul/li[position()>3]/a/text()').extract())
            for url in products:
                yield Request(urljoin_rfc(response.url, url),
                              callback=self.parse_product,
                              meta={'category': category})

            for next_page in response.css('.pagination_pageNumber::attr(href)').extract():
                yield Request(response.urljoin(next_page), callback=self.parse_page)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        try:
            name = hxs.select(u'//*[@itemprop="name"]/text()').extract()[0].strip()
        except:
            open('/tmp/lookfantastic', 'w').write(response.body)
            response.meta['retries'] = response.meta.get('retries', 0) + 1
            if response.meta['retries'] > 10:
                self.log('Giving up on url [%s]' % (response.url))
                raise
            yield Request(response.url, meta=response.meta, dont_filter=True)
            return
        product_loader = ProductLoader(item=Product(), response=response)
        product_loader.add_value('identifier', response.url.split('/')[-1].split('.')[0])
        product_loader.add_value('url', response.url)
        product_loader.add_value('name', name)
        product_loader.add_xpath('brand', u'(//meta[@itemprop="brand"]/@content)[1]')
        product_loader.add_css('price', '.product-price .price ::text')
        product_loader.add_value('sku', response.url.split('/')[-1].split('.')[0])
        product_loader.add_value('category', response.meta.get('category'))
        img = hxs.select(u'//a/img[@class="product-img"]/@src').extract()
        if img:
            product_loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))
        if hxs.select('//p[@class="availability" and contains(text(),"In stock")]'):
            product_loader.add_value('stock', '1')
        if hxs.select('//p[@class="free-delivery"]'):
            product_loader.add_value('shipping_cost', '0')

        item = product_loader.load_item()
        metadata = FragranceDirectMeta()
        metadata['promotion'] = normalize_space(' '.join(hxs.select('//p[contains(@class, "yousave")]//text()|//h3[@class="offer-buy-x-delivery-discount"]//text()').extract()))
        if item.get('price'):
            metadata['price_exc_vat'] = Decimal(item['price']) / Decimal('1.2')
        item['metadata'] = metadata

        yield item
