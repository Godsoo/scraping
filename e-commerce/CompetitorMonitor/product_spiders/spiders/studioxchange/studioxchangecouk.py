import urlparse
from urlparse import urljoin

from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url

from product_spiders.items import Product, ProductLoader
from product_spiders.base_spiders.primary_spider import PrimarySpider

class StudioxchangeCoUk(PrimarySpider):
    name = 'studioxchange.co.uk'
    allowed_domains = ['studioxchange.co.uk', 'www.studioxchange.co.uk', 'shop.studioxchange.co.uk']
    start_urls = ('http://shop.studioxchange.co.uk/pindex.asp',)

    ids = []
    
    csv_file = 'studioxchange_crawl.csv'

    def parse(self, response):
        if not isinstance(response, HtmlResponse):
            return

        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        # products
        product_urls = hxs.select(u'//div[@id="content_area"]/table[1]/tr[2]/td[1]/table[2]//tr/td[3]/a[1]/@href').extract()

        for url in product_urls:
            yield Request(url, callback=self.parse_product)

        # next page
        nextPageLink = hxs.select('//div[@id="content_area"]/table[1]/tr[2]/td[1]/table[1]/tr[1]/td[1]/font[@style="font-weight:bold"]/following-sibling::a[1]/@href')
        if nextPageLink:
            yield Request(urljoin(base_url, nextPageLink[0].extract()), callback=self.parse)

    def parse_product(self, response):
        if not isinstance(response, HtmlResponse):
            return

        hxs = HtmlXPathSelector(response)

        product_loader = ProductLoader(response=response, item=Product())

        product_loader.add_xpath('name', u'//table[@id="v65-product-parent"]//font[@class="productnamecolorLARGE colors_productname"]/span[1]/text()')
        product_loader.add_value('url', response.url)

        price = hxs.select(u'//table[@id="v65-product-parent"]//font[@class="pricecolor colors_productprice"]//span[@itemprop="price"]/text()').extract()
        if not price:
            product_loader.add_value('price', "")
        else:
            product_loader.add_value('price', price[0])

        image_url = ''
        image = hxs.select('//img[@id="product_photo"]/@src')
        if image:
            image_url = image[0].extract()
            if image_url.startswith('//'):
                image_url = image_url.replace('//', 'http://')


        product_loader.add_value('image_url', image_url)

        category = ''
        cat = hxs.select('//table[@id="v65-product-parent"]//tr/td[@class="vCSS_breadcrumb_td"]//b/a[position()=last()]/text()')
        if cat:
            category = cat[0].extract().strip()

        product_loader.add_value('category', category)

        brand = hxs.select('//form[@id="vCSS_mainform"]/following-sibling::table//tr/td/b[contains(text(),"Browse for more products in the same category as this item")]/following-sibling::a[contains(text(),"Brands") and @title="Brands" and not(following-sibling::*[1][self::br])]/following-sibling::a[1]/text()')
        if brand:
            product_loader.add_value('brand', brand[0].extract().strip())


        productCode = hxs.select('//input[@name="ProductCode"]/@value').extract()
        if not productCode:
            url_product_code = hxs.select('//form[@name="MainForm"]/@action').extract()[0]
            parsed = urlparse.urlparse(url_product_code)
            productCode = urlparse.parse_qs(parsed.query)['ProductCode'][0]
        else:
            product_loader.add_value('sku', productCode[0].lower().strip())

        if not productCode:
            self.log("ERROR productCode not found")
        else:
            productCode = productCode[0].lower().strip()
            product_loader.add_value('identifier', productCode)

        btnAddToCart = hxs.select('//input[@name="btnaddtocart"]').extract()
        if btnAddToCart:
            # product in stock
            pass
        else:
            outOfStock = hxs.select('//span[contains(@style,"color:red") and contains(text(),"Out of Stock")]').extract()
            if outOfStock:
                product_loader.add_value('stock', 0)
            else:
                self.log("ERROR outOfStock not found")

        if productCode not in self.ids:
            self.ids.append(productCode)
            yield product_loader.load_item()
