from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


class JohnLewisSpider(BaseSpider):
    name = 'johnlewis.com-tech'
    allowed_domains = ['johnlewis.com']
    start_urls = ['http://www.johnlewis.com/electricals/televisions/all-tvs/c800005013',
                  'http://www.johnlewis.com/blu-ray-dvd-home-cinema/view-all-cinema-systems/c8000078',
                  'http://www.johnlewis.com/blu-ray-dvd-home-cinema/blu-ray-players/c800004741',
                  'http://www.johnlewis.com/blu-ray-dvd-home-cinema/view-all-digital-recorders/c8000024486',
                  'http://www.johnlewis.com/freeview-freesat-smart-boxes/c600002645',
                  'http://www.johnlewis.com/electricals/tv-stands-26-accessories/3d-glasses-26-transmitters/c7000010649',
                  'http://www.johnlewis.com/electricals/cameras-26-camcorders/all-cameras/c800004002',
                  'http://www.johnlewis.com/electricals/audio/all-radios/view-all-radios/c800001842',
                  'http://www.johnlewis.com/electricals/audio/speaker-docks/c700008953',
                  'http://www.johnlewis.com/electricals/audio/micro-systems/c700001542',
                  'http://www.johnlewis.com/electricals/audio/wireless-music-players/c700003126',
                  'http://www.johnlewis.com/apple-ipods/c700001252',
                  'http://www.johnlewis.com/electricals/headphones/view-all-headphones/c80000660',
                  'http://www.johnlewis.com/ebook-readers/c7000010829',
                  'http://www.johnlewis.com/view-all-tablets/c8000021438',
                  'http://www.johnlewis.com/electricals/laptops-26-netbooks/laptops/c80000398',
                  'http://www.johnlewis.com/electricals/telephones/all-telephones/c700008777']

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
            yield Request(url, callback=self.parse_products_list)

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

        product_sku = hxs.select('//div[@id="prod-product-code"]/p/text()').extract()
        if not product_sku:
            product_sku = hxs.select('//*[@id="bundle-items"]/ul//li/div/p[2]/span/strong/text()').extract()
            if not product_sku:
                self.log("ERROR SKU not found")
                return
        else:
            loader.add_value('sku', product_sku[0].strip())
        product_id = hxs.select('//input[@type="hidden" and @name="/atg/store/order/purchase/CartFormHandler.productId"]/@value').extract()
        if not product_id:
            self.log("ERROR product_id not found, skipping this product: " + response.url)
            return
        else:
            try:
                product_sku_2 = hxs.select('//input[@type="hidden" and @class="hidden-sku"]/@value').extract()[0]
            except:
                product_sku_2 = ''
            loader.add_value('identifier', '%s%s' % (product_id[0],
                                                     '_' + product_sku_2 if product_sku_2 else ''))
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
