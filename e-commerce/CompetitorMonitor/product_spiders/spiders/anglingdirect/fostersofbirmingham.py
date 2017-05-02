from scrapy import Spider, Request
from product_spiders.items import Product, ProductLoader


class FostersOfBirminghamSpider(Spider):
    name = 'fostersofbirmingham.co.uk'
    allowed_domains = ['www.fostersofbirmingham.co.uk']
    start_urls = ('http://www.fostersofbirmingham.co.uk/',)

    def parse(self, response):
        # categories
        categories = response.xpath('//div[@class="megaMenu"]//a/@href').extract()
        for url in categories:
            url = response.urljoin(url)
            yield Request(url)

        # pages
        next_page = response.xpath(u'//span[@class="pg"]//span[@class="n"]//a/@href').extract()
        if next_page:
            url = response.urljoin(next_page[0])
            yield Request(url)

        # products
        products = response.xpath(u'//h3[@class="ti"]/a/@href').extract()
        for url in products:
            url = response.urljoin(url)
            yield Request(url, callback=self.parse_product)


    def parse_product(self, response):
        category = response.xpath(u'//div[@id="mR"]/div[@class="bc"]/a/span/text()').extract()
        category = category[-1] if category else ''
        brand = response.xpath(u'//div[@id="mR"]//div[@class="man"]/img/@alt').extract()
        brand = brand[0] if brand else ''
        image_url = response.xpath(u'//div[@id="mR"]//a/img[contains(@id,"imgMain")]/@src').extract()
        image_url = response.urljoin(image_url[0] if image_url else '')
        id_prefix = response.url.split('/')[-1]
        sku = response.xpath(u'//div[@class="pn"]/text()')[0].extract().split(': ', 1)[1]
        identifier = id_prefix + ' - ' + sku

        multiple_prices = response.xpath(u'//table[@class="grpChld"]//tr[@class="r1"]')
        if not multiple_prices:
            product_loader = ProductLoader(item=Product(), response=response)
            product_loader.add_xpath('name', u'//div[@class="det"]/h1/text()')
            product_loader.add_value('url', response.url)
            product_loader.add_value('category', category)
            product_loader.add_value('brand', brand)
            product_loader.add_value('identifier', identifier)
            product_loader.add_value('sku', sku)
            product_loader.add_value('image_url', image_url)
            product_loader.add_xpath('price', u'//div[@class="addBsk"]/div[@class="pri"]/b/text()',
                                     re=u'\xa3(.*)')
            if not product_loader.get_output_value('price'):
                product_loader.add_xpath('price', u'//div[@class="addBsk"]/div[@class="pri"]/b/span/text()',
                                     re=u'\xa3(.*)')
            yield product_loader.load_item()
        else:
            i = 0
            for name_and_price in multiple_prices:
                product_loader = ProductLoader(item=Product(), selector=name_and_price)
                product_loader.add_xpath('name', u'./td[@class="c1"]/text()',
                                         re=u'.*?-[\xa0]*(.*)')
                product_loader.add_value('url', response.url)
                product_loader.add_value('category', category)
                product_loader.add_value('brand', brand)
                sku = name_and_price.css('.c1 b::text').extract_first()
                product_loader.add_value('identifier', id_prefix + ' - ' + sku)
                product_loader.add_value('sku', sku)
                product_loader.add_value('image_url', image_url)
                product_loader.add_xpath('price', u'./following-sibling::node()[1]/td[@class="c3"]/span/text()',
                                         re=u'\xa3(.*)')
                if not product_loader.get_output_value('price'):
                    product_loader.add_xpath('price', u'./following-sibling::tr[1]/td[@class="c3"]/span/text()',
                        re=u'\xa3(.*)')
                yield product_loader.load_item()
                i += 1
