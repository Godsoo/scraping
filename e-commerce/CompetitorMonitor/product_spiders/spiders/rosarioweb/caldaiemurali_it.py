from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoaderWithoutSpacesEU as ProductLoader
from product_spiders.utils import extract_price, extract_price_eu
from decimal import Decimal
from scrapy.utils.response import open_in_browser
from scrapy.exceptions import CloseSpider


class CaldaiemuraliItSpider(CrawlSpider):
    name = "caldaiemurali.it"
    allowed_domains = ["caldaiemurali.it"]
    start_urls = ('http://www.caldaiemurali.it',)
    
    rules = (Rule
             (LinkExtractor(restrict_xpaths=('//nav[@class="block-content"]',
                                             '//div[@class="pages"]'))
                ),
             Rule
             (LinkExtractor(restrict_xpaths='//h2[@class="product-name"]'),
              callback='parse_item'
                )
        )

    def _parse(self, response):
        yield Request('http://www.caldaiemurali.it/cucina-a-legna-in-acciaio-porcellanato-la-nordica-extraflame-mod-sovrana-vari-colori-6-5-kw.html', callback=self.parse_item)

    def parse_item(self, response):
        hxs = HtmlXPathSelector(response)

        name = hxs.select("//div[@class='product-name']/h1/text()").extract()

        if not name:
            self.log('No name on %s' %response.url)
            return

        # price = hxs.select('//*[@itemprop="price"]/text()').extract()[0]

        product_image = hxs.select('//*[@id="ma-zoom1"]/img/@src').extract()
        if product_image:
            product_image = urljoin_rfc(get_base_url(response), product_image[0])
        category = ''.join(hxs.select('//div[@class="breadcrumbs"]/ul/li[2]/a/text()').extract())

        shipping = hxs.select('//table[@id="product-attribute-specs-table"]'
                              '//th[@class="label" and contains(text(), "Spese Spedizione")]'
                              '/following-sibling::td/text()').extract()
        if not shipping:
            shipping = hxs.select('//table[@id="product-attribute-specs-table"]'
                              '//th[@class="label" and contains(text(), "Shipping Cost")]'
                              '/following-sibling::td/text()').extract()
        if shipping:
            shipping_cost = shipping[0].strip()
            if shipping_cost == 'Gratis':
                shipping_cost = '0.0'
            else:
                shipping_cost = extract_price_eu(shipping[0])
                if shipping_cost >= Decimal(1000):
                    shipping_cost = extract_price(shipping[0])
        else:
            shipping_cost = None

        brand = hxs.select('//table[@id="product-attribute-specs-table"]'
                           '//th[@class="label" and contains(text(), "Marca")]'
                           '/following-sibling::td/a/@title').extract()
        if not brand:
            brand = hxs.select('//table[@id="product-attribute-specs-table"]'
                               '//th[@class="label" and contains(text(), "Marca")]'
                               '/following-sibling::td/text()').extract()

        l = ProductLoader(item=Product(), response=response)
        identifier = response.xpath("//input[@type='hidden'][@name='product']/@value").extract()[0]
        price = response.xpath('//div[@class="product-shop"]//span[@itemprop="price"]/text()').extract()
        
        l.add_xpath('sku', 'normalize-space(substring-after(//li[contains(text(),"Codice:")]/text(), ":"))')
        
        l.add_value('url', response.url)
        
        l.add_value('image_url', product_image)
        l.add_value('category', category)
        if brand:
            l.add_value('brand', brand[0].strip())
        
        stock = response.xpath('//p[contains(@class, "availability")]')
        if stock.xpath('//@class[contains(., "instock") or contains(., "in-stock")]'):
            l.add_value('stock', 1)
        else:
            l.add_value('stock', 0)

        if shipping_cost is not None:
            l.add_value('shipping_cost', shipping_cost)
            
        if not price:
            price = response.xpath('//*[@id="product-price-{}"]//text()'.format(identifier)).re(r'[\d,.]+')
            if price:
                l.add_value('identifier', identifier)
                l.add_value('name', name)
                l.add_value('price', price[0])
                yield l.load_item()
                return
                
        if price and len(price) == 1:
            l.add_value('identifier', identifier)
            l.add_value('name', name)
            l.add_value('price', price[0])
            yield l.load_item()
            return
        
        table = response.xpath('//table[@id="super-product-table"]')
        if not table:
            self.log('No correct price found on %s' %response.url)
            self.log('Price is %s' %price)
            return
        
        item = l.load_item()
        
        for product in table.xpath('tbody/tr[td/input]'):
            loader = ProductLoader(item=Product(item), selector=product)
            loader.replace_xpath('name', 'td[1]/text()')
            loader.replace_xpath('identifier', 'td/div/span/@id', re='\d+')
            loader.replace_xpath('price', './/span[contains(@id, "product-price")]//text()', re='\S+')
            item = loader.load_item()
            yield item

            
            
            

        
