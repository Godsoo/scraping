from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


class JohnLewisSpider(BaseSpider):
    name = 'johnlewis.com-electricals'
    allowed_domains = ['johnlewis.com']
    start_urls = [
        "http://www.johnlewis.com/food-processors-mixers-blenders/food-processors/c80000545",
        "http://www.johnlewis.com/food-processors-mixers-blenders/food-mixers/c80000543",
        "http://www.johnlewis.com/food-processors-mixers-blenders/blenders/c80000525",
        "http://www.johnlewis.com/electricals/food-processors-mixers-blenders/hand-blenders/c8000019939",
        "http://www.johnlewis.com/food-processors-mixers-blenders/choppers-26-grinders/c80000527",
        "http://www.johnlewis.com/food-processors-mixers-blenders/juicers-26-presses/c80000538",
        "http://www.johnlewis.com/ice-cream-makers/c80000537",
        "http://www.johnlewis.com/electricals/coffee-machines/all-coffee-machines/c80000529",
        "http://www.johnlewis.com/electricals/coffee-machines/coffee-grinders/c80000528",
        "http://www.johnlewis.com/electricals/coffee-machines/kettles/c80000539",
        "http://www.johnlewis.com/electricals/toasters/c600001695",
        "http://www.johnlewis.com/electricals/cooking-appliances/slow-cookers/c80000547",
        "http://www.johnlewis.com/electricals/cooking-appliances/sandwich-makers/c80000548",
        "http://www.johnlewis.com/electricals/cooking-appliances/fryers/c80000534",
        "http://www.johnlewis.com/electricals/cooking-appliances/bread-makers/c80000526",
        "http://www.johnlewis.com/electricals/ironing/steam-irons-26-brushes/c80000518",
        "http://www.johnlewis.com/electricals/ironing/steam-generators/c800001959",
        "http://www.johnlewis.com/electricals/vacuum-cleaners/all-vacuum-cleaners/c800005069",
        "http://www.johnlewis.com/electricals/heaters-26-fans/fans/c80000488",
        "http://www.johnlewis.com/hair-care-shavers-dental/hair-dryers/c80000688",
        "http://www.johnlewis.com/hair-care-shavers-dental/hair-straighteners/c800001975",
        "http://www.johnlewis.com/hair-care-shavers-dental/hair-stylers/c800001974",
        "http://www.johnlewis.com/women%27s-hair-removal/c80000702",
        "http://www.johnlewis.com/gifts/for-him/men%27s-grooming/men%27s-shavers/c80000693",
        "http://www.johnlewis.com/electricals/kettles/c600001693"
    ]

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        categories = hxs.select('//*[@id="LHNCtl1_rptGp_ctl00_LHNGpCtl1_subnavac"]/ul/li/a/@href').extract()
        if categories:
            for category in categories:
                url = urljoin_rfc(get_base_url(response), category)
                self.log("categories found, parse_products " + url)
                yield Request(url, callback=self.parse_products_list)
        else:
            self.log("categories not found, parse_products")
            yield Request(response.url, dont_filter=True, callback=self.parse_products_list)

    def parse_products_list(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        products = hxs.select('//article')
        self.log("parse_products " + response.url)
        if products:
            self.log("products found: " + str(len(products)))
            for product in products:
                url = urljoin_rfc(base_url,
                                  product.select('.//a[@class="product-link"]/@href').extract().pop().strip())
                yield Request(
                    url=url,
                    callback=self.parse_products)
        next_page = hxs.select('//*[@class="next"]/a/@href').extract()
        if next_page:
            url = urljoin_rfc(get_base_url(response), next_page[0])
            yield Request(url, callback=self.parse_products)

    def parse_products(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        products_urls = hxs.select('//*[@id="prod-product-colour"]/ul//li//a/@href').extract()
        if products_urls:
            for url in products_urls:
                purl = urljoin_rfc(base_url, url)
                yield Request(
                    url=purl,
                    callback=self.parse_product)
        else:
            for p in self.parse_product(response):
                yield p

    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), response=response)
        name = hxs.select('//*[@id="prod-title"]//text()').extract()
        if not name:
            name = hxs.select('//*[@id="content"]//h1/text()').extract()
            if not name:
                self.log("ERROR name not found")
        else:
            name = " ".join(name[0].split())
            loader.add_value('name', name)
            loader.add_value('url', response.url)
        price = hxs.select('//*[@id="prod-add-to-basket"]/div[2]/div/ul/li/strong[2]//text()').extract()
        if not price:
            price = hxs.select('//*[@id="prod-add-to-basket"]/div[2]/div/ul/li/strong//text()').extract()
            if not price:
                price = hxs.select('//*[@id="prod-price"]/p/strong//text()').extract()
                if not price:
                    self.log("ERROR price not found")
        if price:
            price = " ".join(price[0].split())
            loader.add_value('price', price)
        product_code = hxs.select('//div[@id="prod-product-code"]/p/text()').extract()
        if not product_code:
            self.log("ERROR product_code not found")
        else:
            loader.add_value('identifier', product_code[0].strip())
        image = hxs.select('//*[@data-jl-overlay]/@href').extract()
        if not image:
            self.log("ERROR image not found")
        else:
            image = urljoin_rfc(base_url, image[0].strip())
            loader.add_value('image_url', image)
        brand = hxs.select('//div[@id="tabinfo-care-info" or @id="tabinfo-features"]//dl/dt[contains(text(),"Brand")]'
                           '/following-sibling::dd[1]/text()').extract()
        if not brand:
            self.log("ERROR brand not found")
        else:
            brand = " ".join(brand[0].split())
            loader.add_value('brand', brand.strip())
        category = hxs.select('(//div[@id="breadcrumbs"]/ol/li/a)[position()=last()]/text()').extract()
        if not category:
            self.log("ERROR category not found")
        else:
            loader.add_value('category', category[0].strip())
        product = loader.load_item()
        yield product