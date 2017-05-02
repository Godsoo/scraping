'''
Ticket link: https://app.assembla.com/spaces/competitormonitor/tickets/5479
The spider searches the following on the currys.co.uk site:
Asus
Corsair
Creative
Elgato
Hyper X
Logitech
Maplin
MSI
Razer
Roccat
Seagate
'''

from scrapy.http import Request
from scrapy.spiders import Spider
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
from product_spiders.utils import extract_price


class Currys(Spider):
    name = 'maplin-currys'
    allowed_domains = ['currys.co.uk']
    
    to_search = ('Asus',
 'Corsair',
 'Creative',
 'Elgato',
 'Hyper X',
 'Logitech',
 'Maplin',
 'MSI',
 'Razer',
 'Roccat',
 'Seagate')
    url = 'http://www.currys.co.uk/gbuk/search-keywords/xx_xx_xx_xx_xx/%s/xx-criteria.html'
    
    def __init__(self, *args, **kwargs):
        super(Currys, self).__init__(*args, **kwargs)
        self.start_urls = (self.url % s for s in self.to_search)

    def parse(self, response):
        # products
        products = response.xpath('//article//a[@class="in"]/@href').extract()
        products += response.xpath('//article//a[div[@class="in"]]/@href').extract()
        for product in products:
            yield Request(
                product.strip(),
                callback=self.parse_product
            )

        # products next page
        for next_page in set(response.xpath("//a[@class='next']/@href").extract()):
            yield Request(
                next_page.strip()
            )

        is_product = response.xpath('//meta[@property="og:type"]/@content').extract()

        if is_product:
            for product in self.parse_product(response):
                yield product


    def parse_product(self, response):
        url = response.url
        l = ProductLoader(item=Product(), response=response)

        # name
        name_l = response.xpath("//div[contains(@class,'product-page')]//h1[@class='page-title nosp']//text()").extract()
        name = ' '.join([x.strip() for x in name_l if x.strip()])
        l.add_value('name', name)

        # price
        price = response.xpath("//meta[@property='og:price:amount']/@content").extract()
        price = extract_price("".join(price))
        l.add_value('price', price)

        # sku
        sku = response.xpath("//div[contains(@class,'product-page')]//meta[@itemprop='identifier']/@content").extract()
        if sku:
            sku = sku[0].split(":")[-1]
            l.add_value('sku', sku)

        # identifier
        identifier = response.url.split('-')[-2]
        l.add_value('identifier', identifier)

        # category
        l.add_xpath('category', "//div[@class='breadcrumb']//a[position() > 1]/span/text()")

        # product image
        l.add_xpath('image_url', "//meta[@property='og:image']/@content")
        # url
        l.add_value('url', url)
        # brand
        l.add_xpath('brand', "//span[@itemprop='brand']/text()")
        # stock
        if response.xpath("//div[contains(concat('', @class,''), 'oos')]") \
                or response.xpath("//li[@class='unavailable']/i[@class='dcg-icon-delivery']"):
            l.add_value('stock', 0)
        else:
            l.add_value('stock', 1)

        product = l.load_item()

        meta_data = response.xpath("//div[@class='prd-amounts']//strong[@class='offer']//text()").extract()
        product['metadata'] = {}
        if meta_data:
            product['metadata']['promotional_data'] = meta_data[0].strip()
        else:
            product['metadata']['promotional_data'] = ''
        yield product