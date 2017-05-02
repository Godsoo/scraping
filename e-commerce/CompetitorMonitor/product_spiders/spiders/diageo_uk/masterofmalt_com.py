from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price

# from product_spiders.base_spiders.prodcache import ProductCacheSpider

class MasterofmaltComSpider(BaseSpider):
    name = 'masterofmalt.com'
    allowed_domains = ['masterofmalt.com']
    start_urls = ('http://www.masterofmalt.com/',)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        formdata = dict(zip(hxs.select('//form[@id="AspNetForm"]//input/@name').extract(),
                            hxs.select('//form[@id="AspNetForm"]//input/@value').extract()))
        formaction = hxs.select('//form[@id="AspNetForm"]/@action').extract()[0]

        # Set currency
        formdata['ctl00$ucCart$ddl_Currency'] = '-1'

        new_req = FormRequest(urljoin_rfc(get_base_url(response), formaction),
                              formdata=formdata,
                              dont_filter=True,
                              callback=self.parse_urls)

        yield new_req

    def parse_urls(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        # parse categories
        urls = hxs.select('//div[@class="menuContainer"]//a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_categories)

    def parse_categories(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        urls = hxs.select('//div[@class="leftColumnBot" '
                          'or @class="rightColumnTop" '
                          'or @class="promotions_linkList" '
                          'or @class="leftColumnBotToc"]//a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product_list)

    def parse_product_list(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        # parse pagination
        urls = hxs.select('//a[@class="pageNum"]/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product_list)
        # parse products
        products = hxs.select('//div[@class="boxBgr productBoxWide"]')
        for product in products:
            product_loader = ProductLoader(item=Product(), selector=product)
            product_name = product.select('.//div[@class="ctrl_PBW_Mid_Title"]/a/text()').extract()[0]
            image_url = product.select('.//div[@class="ctrl_PBW_Img"]//img/@src').extract()[0]
            # product_loader.add_value('image_url', urljoin_rfc(base_url, image_url))
            product_loader.add_value('name', product_name)
            url = product.select('.//div[@class="ctrl_PBW_Mid_Title"]/a/@href').extract()[0]
            product_loader.add_value('url', url)
            identifier = product.select('.//div[contains(@id,"_addtobasket")]').re('(\d+)')
            # treat as delisted
            if product.select('.//div[contains(@class,"bbDiscontinued")]'):
                continue

            if identifier:
                if identifier in ('6466',): continue
                product_loader.add_value('identifier', identifier[0])
            product_loader.add_value('sku', '')
            brand = product.select('.//div[@class="ctrl_PBW_Mid_Distil"]/a/text()').extract()
            if brand:
                product_loader.add_value('brand', brand[0])
            price = ''.join(product.select('.//div[@class="ctrl_PBW_Buy_Price"]/text()').extract())
            product_loader.add_value('price', extract_price(price))
            category = hxs.select('//div[@class="breadCrumb"]//span[@itemprop="title"]/text()').extract()
            if len(category) > 1:
                product_loader.add_value('category', category[1])
            if product.select('.//div[contains(@id,"_addtobasket")]'):
                product_loader.add_value('stock', 1)
            else:
                product_loader.add_value('stock', 0)
            product_loader.add_value('shipping_cost', 4.89)
            # Multiple products on the same page
            yield Request(url, callback=self.parse_product, meta={'product':product_loader.load_item()}, dont_filter=True)
            # multiple products on the same product page, fetch_product can't handle it
            # yield self.fetch_product(Request(url, callback=self.parse_product), product_loader.load_item())

    def parse_product(self, response):
        # Product identifier can be found only on product page for out of stock products
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        item = Product(response.meta.get('product', Product()))
        if not item.get('identifier'):
            identifier = hxs.select('.//div[contains(@id,"StockMessage_")]').re('(\d+)')
            if not identifier:
                identifier = hxs.select('//script[contains(text(), "getRecentlyViewed")]').re("getRecentlyViewed\(([0-9]+)\)")
            item['identifier'] = identifier[0]
            if identifier[0] in ('6466',): return
        image_url = hxs.select('//div[@class="productPageLeft"]//img[@itemprop="image"]/@src').extract()
        if image_url:
            item['image_url'] = urljoin_rfc(base_url, image_url[0])
        yield item
