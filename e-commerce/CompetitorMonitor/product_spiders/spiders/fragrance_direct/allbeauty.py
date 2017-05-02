from decimal import Decimal
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
from product_spiders.utils import extract_price
from fragrance_direct_items import FragranceDirectMeta


def normalize_space(s):
    ''' Cleans up space/newline characters '''
    import re
    return re.sub(r'\s+', ' ', s.replace(u'\xa0', ' ').strip())

class AllbeautySpider(BaseSpider):
    name = 'fragrancedirect-allbeauty.com'
    allowed_domains = ['allbeauty.com']
    start_urls = ['http://www.allbeauty.com']
    cookies={'locale':'GBP%2C48%2C0%2CEN'}

    def _start_requests(self):
        yield FormRequest('http://www.allbeauty.com/ajax/setLocale.php', formdata={'currency':'GBP', 'country':'48', 'setLocale':'Save'}, cookies=self.cookies)
#        yield Request('http://www.allbeauty.com/cosmetics/max-factor-lipfinity-lipstick', callback=self.parse_product)

    def _parse(self, response):
        yield Request('http://www.allbeauty.com', callback=self.parse2)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        categories = hxs.select('//div[@id="categoryMenu"]//a/@href').extract()
        for category in categories:
            yield Request(urljoin_rfc(base_url, category),
                              callback=self.parse_category)

    # Can either a subcategory or product listing page
    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        for url in hxs.select('//div[@class="brands"]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_page, cookies=self.cookies)
            
    def parse_page(self, response):
        hxs = HtmlXPathSelector(response)

        # Try to find products
        for x in self.parse_product(response):
            yield x
        for url in hxs.select('//h3/a/@href').extract():
            yield Request(urljoin_rfc(response.url, url),
                              callback=self.parse_product, cookies=self.cookies)
            
        for page in hxs.select('//a[@class="pageNumber"]/@href').extract():
            yield Request(urljoin_rfc(response.url, page), callback=self.parse_page)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        if not hxs.select('//div[@class="productDetail"]'):
            return
        product_loader = ProductLoader(item=Product(), selector=hxs.select('//div[@class="productDetail"]'))
        product_loader.add_value('url', response.url)
        product_loader.add_xpath('brand', './div[@class="productDescription"]/h2/text()')
        product_loader.add_xpath('image_url', './/img[@class="productImage"]/@src')
        product_loader.add_xpath('category', './/p[@id="breadCrumbs"]/a[position()>1]/text()')
        p = product_loader.load_item()
        
        found = False
        for product in hxs.select('//div[@class="rangeTable"]/div[@class="rangeProduct"]'):
            found = True
            product_loader = ProductLoader(item=p, selector=product)
            product_loader.replace_xpath('identifier', './/input[@name="UC_recordId"]/@value')
            product_loader.replace_xpath('sku', './/input[@name="UC_recordId"]/@value')
            product_loader.add_xpath('name', './/div[@class="productName"]/*/text()')
            if product.select('.//input[@value="Buy"]'):
                product_loader.add_value('stock', '1')
            product_loader.add_xpath('price', './/span[@class="ourPrice"]/text()')
            item = product_loader.load_item()
            if item['price'] <= 19.99:
                item['shipping_cost'] = Decimal('1.95')
                item['price'] = item['price'] + item['shipping_cost']
            metadata = FragranceDirectMeta()
            metadata['promotion'] = ''.join(product.select('.//span[@class="productDiscount"]/text()').extract()).strip()
            if item.get('price'):
                metadata['price_exc_vat'] = Decimal(item['price']) / Decimal('1.2')
            item['metadata'] = metadata
            yield item
        if found:
            return
        
        product_loader.replace_xpath('sku', './div[@class="productDescription"]//input[@name="UC_recordId"]/@value')
        product_loader.replace_xpath('identifier', './div[@class="productDescription"]//input[@name="UC_recordId"]/@value')
        product_loader.add_xpath('name', './div[@class="productDescription"]/*[self::h3 or self::h4]/text()')
        if hxs.select('//div[@class="productDescription"]//input[@value="Buy"]'):
            product_loader.add_value('stock', '1')
        product_loader.add_xpath('price', './/span[@class="ourPrice"]/text()')
        item = product_loader.load_item()
        if item['price'] <= 19.99:
            item['shipping_cost'] = Decimal('1.95')
            item['price'] = item['price'] + item['shipping_cost']

        metadata = FragranceDirectMeta()
        metadata['promotion'] = ''.join(hxs.select('.//span[@class="productDiscount"]/text()').extract()).strip()
        if item.get('price'):
            metadata['price_exc_vat'] = Decimal(item['price']) / Decimal('1.2')
        item['metadata'] = metadata
        yield item
