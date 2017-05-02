from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from scrapy import log

from product_spiders.items import Product
from productloader import WindowsCleaningProductLoader as ProductLoader

from scrapy.http import FormRequest

class CWCSupplyUSA(BaseSpider):
    name = 'cwcsupplyusa.com'
    allowed_domains = ['cwcsupplyusa.com']
    start_urls = ('http://www.cwcsupplyusa.com',)

    def parse_product(self, response):
        if not isinstance(response, HtmlResponse):
            return

        base_url = get_base_url(response)
        # sub products
        hxs = HtmlXPathSelector(response)

        name = hxs.select('//div[@id="product-detail-div"]//select/@name').extract()
        subproducts = hxs.select('//div[@id="product-detail-div"]//select/option')
        if name and 'size' not in response.meta:
            subproducts = subproducts[1:]
            for subproduct in subproducts:
                request = FormRequest.from_response(response, formdata={name[0]: subproduct.select('./@value').extract()},
                                                    dont_click=True, callback=self.parse_product)
                request.meta['size'] = subproduct.select('./text()')[0].extract().strip()
                yield request
            return

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('url', response.url)
        
        name = hxs.select('//div[@id="product-detail-div"]/h1/text()').extract()[0].strip()
        if 'size' in response.meta:
            name += ' ' + response.meta['size']
        loader.add_value('name', name)

        price = hxs.select('//span[@class="prod-detail-sale-value"]/text()').extract()
        if not price:
            price = hxs.select('//span[@class="prod-detail-cost-value"]/text()')[0].extract()
        price = price if price else '0.00'
        loader.add_value('price', price)
        
        if not loader.get_output_value('price'):
            loader.add_value('stock', 0)
            
        sku = hxs.select('//*[@itemprop="mpn"]/text()').extract()
        if not sku:
            sku = hxs.select('//span[@class="prod-detail-part-value"]/text()').extract()
        if sku:
            sku = sku[0]
        
        product_id = hxs.select('//input[@type="hidden" and @class="productDetailsID"]/@value').extract()
        item_number = hxs.select('//span[@class="prod-detail-part-value"]/text()').extract()
        if not item_number:
            item_number = hxs.select('//*[@itemprop="mpn"]/text()').extract()
        if item_number and product_id:
            identifier = '%s.%s' % (product_id[0], item_number[0])
        else:
            log.msg('Identifier not found: [%s]' % response.url)
            return
        loader.add_value('sku', sku)
        loader.add_value('identifier', identifier)
        
        image_url = hxs.select('//a[@id="Zoomer"]//img/@src').extract()
        if image_url:
            loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
        
        brand = hxs.select('//*[@itemprop="manufacturer"]/text()').extract()
        if brand:
            loader.add_value('brand', brand[0])
            
        category = hxs.select('//div[contains(@id,"breadcrumb")]//a/text()').extract()
        if category:
            loader.add_value('category', category[-1])

        yield loader.load_item()


    def parse(self, response):
        URL_BASE = 'http://www.cwcsupplyusa.com'
        hxs = HtmlXPathSelector(response)
        # sub_categories
        sub_categories = hxs.select('//div[@class="category-list-item-head"]/h5/a/@href').extract()
        if sub_categories:
            for url in sub_categories:
                url = urljoin_rfc(URL_BASE, url)
                yield Request(url)
        else:
            # categories
            category_urls = hxs.select('//td[@class="module-body"]/ul[@class="module-list cat-nav"]//li/a/@href').extract()
            for url in category_urls:
                url = urljoin_rfc(URL_BASE, url)
                yield Request(url)

        # next page
        next_page = hxs.select('//a[@class="pager-link"]/@href').extract()
        if next_page:
            yield Request(next_page[0])

        # products
        product_links = hxs.select('//img[@src="/themes/default-1-1-1-1/images/buttons/cart_btn_view.gif"]/../@href')\
                           .extract()
        for product_link in product_links:
            product_link = urljoin_rfc(URL_BASE, product_link)
            yield Request(product_link, callback=self.parse_product)
