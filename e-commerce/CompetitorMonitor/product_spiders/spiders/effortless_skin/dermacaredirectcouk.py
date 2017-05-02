import re
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader
)

class DermaCareDirectSpider(BaseSpider):
    name = 'dermacaredirect.co.uk'
    allowed_domains = ['www.dermacaredirect.co.uk']
    start_urls = ('http://www.dermacaredirect.co.uk/catalog/seo_sitemap/category/',)
    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        
        categories = hxs.select('//ul[@class="sitemap"]/li/a/@href').extract()

        for category_url in categories:
            if(category_url == ''):
                continue
            # to get all the products in one shot we append 'limit=all'
            # this shows all products in a single page
            yield Request(urljoin_rfc(base_url, category_url), callback=self.parse_category)

        # pagination

        pages = hxs.select('(//div[@class="pages"])[1]//li[not(@class) or not(@class="current")]/a[not(@class) or (not(@title="Next") and not(@title="Previous")) ]/@href').extract()
        for page in pages:
            yield Request(urljoin_rfc(base_url, page), callback=self.parse)                        

    def parse_category(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        
        category = hxs.select('//div[@class="col-main"]//div[@class="page-title category-title"]//h1/text()').extract()
        if len(category) > 0:
            category = category.pop().strip()
        else:
            category = 'Unknown Category'

        products = hxs.select('//div[@class="category-products"]//a[@class="product-image"]/@href').extract()
        
        for product in products:
            request =  Request(urljoin_rfc(base_url, product), callback=self.parse_product)
            request.meta['category'] = category
            yield request
    
        # Pagination
        pages = hxs.select('(//div[@class="pages"])[1]//li[not(@class) or not(@class="current")]/a[not(@class) or (not(@title="Next") and not(@title="Previous")) ]/@href').extract()
        for page in pages:
            yield Request(urljoin_rfc(base_url, page), callback=self.parse_category)


    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        
        product_image = ""
        pimage_element = hxs.select('//div[@class="product-img-box"]//img/@src').extract()
        if (len(pimage_element)>0):
            product_image= pimage_element.pop().strip()
            
        category = response.meta['category']


        price_xpath = '(//div[@class="price-box"]/*[@class="special-price" or @class="regular-price"])[1]/span[@class="price"]/text()'
        price = hxs.select(price_xpath).extract()
        if len(price) > 0 :
            price = re.sub('[^\d\.]+', '', price.pop())
        else:
            price = '0.00'

        # availability = hxs.select('//div[@class="product-shop"]//div[@class="short"]//p[contains(@class, "availability")]//span[contains(text(), "In stock")]/text()').extract()

        product_name = hxs.select('//div[@class="product-name"]//h1/text()').extract()

        if len(product_name)<1:
            product_name = 'Unknown product'
        else:
            oncallprice = hxs.select('(//div[@class="product-shop" and contains(.//text(), "Call for purchase")])[1]')
            if oncallprice:
                product_name = product_name.pop().strip() + ' (Call for price)'
                price = '0.00'
            else:
                product_name = product_name.pop().strip()


        identifiers = hxs.select('//form[@id="review-form"]/@action').extract()        

        if len(identifiers) > 0:
            ihref = identifiers.pop()
            ifind = 'post/id/'
            if ifind in ihref:
                ifind_offset = ihref.find(ifind) + len(ifind)
                identifier = ihref[ifind_offset: ihref.find('/', ifind_offset)]
            else:
                # now build an identifier using url
                identifier =  re.sub('[^a-zA-Z0-9]', '', self.get_url_id(response.url))
        else:
            # now build an identifier
            identifier =  re.sub('[^a-zA-Z0-9]', '', self.get_url_id(response.url))

        loader = ProductLoader(response=response, item=Product())
        loader.add_value('url', urljoin_rfc(base_url, response.url))
        loader.add_value('name', product_name)
        loader.add_value('image_url', urljoin_rfc(base_url, product_image))    
        loader.add_value('price', price)
        loader.add_value('category', category)
        loader.add_value('identifier', identifier)
        if(hxs.select('//td//b/font/i[contains(., "Free Shipping")]')):
            loader.add_value('shipping_cost', 0)
        
        
        yield loader.load_item()

    def get_url_id(self, product_url):
        search_str = 'dermacaredirect.co.uk/'
        search_index = product_url.find(search_str)
        target_offset = search_index+len(search_str)
        # -5 is for stripping ending '.html' part
        target_str = product_url[target_offset:-5]

        return target_str
