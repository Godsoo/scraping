from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.contrib.loader.processor import TakeFirst, Compose
from scrapy.utils.response import get_base_url
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

class HarrisSportsMailSpider(BaseSpider):
    name = 'harrissportsmail.com'
    allowed_domains = ['www.harrissportsmail.com', 'harrissportsmail.com']
    start_urls = ['http://www.harrissportsmail.com/SetProperty.aspx?languageiso=en&currencyiso=GBP&shippingcountryid=1903']

    def parse(self, response):
        yield Request('http://www.harrissportsmail.com/Sitemap.aspx',
                      callback=self.parse_categories)

    def parse_categories(self, response):
        hxs = HtmlXPathSelector(response)

        xpath = '//table[@class="child-links-table"]//a/@href'
        categories = hxs.select(xpath).extract()
        for category in categories:
            url = urljoin_rfc(get_base_url(response), category)
            yield Request(url, callback=self.parse_category)


    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)

        next_page = hxs.select('//div[@class="results-pager"]//a[contains(@title,"Next Page")]/@href').extract()
        if next_page:
            yield Request(urljoin_rfc(get_base_url(response), next_page[0]), callback=self.parse_category)

        products = hxs.select('//table[@id="ProductDataList"]//a[contains(@class, "model-link")]/@href').extract()
        for product in products:
            url = urljoin_rfc(get_base_url(response), product)
            yield Request(url.replace('/de/', '/en/'), callback=self.parse_product)



    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        image_url = hxs.select('//div[@id="DivModelImage"]//img/@src').extract()
        main_name = hxs.select('//h1/text()').extract()[0].strip()
        if not main_name:
            main_name = ' '.join(hxs.select('//span[@itemprop="name"]/text()').extract()).strip()

        category = hxs.select('//table[@class="history-menu-table"]//a[contains(@class, "history-menu-final-item")]/text()').extract()

        options = hxs.select('//table[@class="add-to-basket"]//tr[contains(@class, "item-row")]')
        for opt in options:
            opt_id = ''.join(opt.select('td[1]//text()').extract()).strip()
            if opt_id:
                opt_id = opt_id.strip()
                opt_name = opt.select('td[3]//text()').extract()[0].strip()
                opt_stock = opt.select('td[2]//text()').extract()[0].strip()
                opt_price = opt.select('td//span[@class="price-label"]/text()').extract()[0]
                # opt_id = opt.select('td[1]//text()').extract()[0].strip()
            else:
                opt_id = ''.join(opt.select('td[2]//text()').extract()).strip()
                if opt_id:
                    opt_id = opt_id.strip()

                    opt_name = opt.select('td[4]//text()').extract()[0].strip()
                    opt_stock = opt.select('td[3]//text()').extract()[0].strip()
                    opt_price = opt.select('td//span[@class="price-label"]/text()').extract()[0]

            if opt_id:
                loader = ProductLoader(item=Product(), selector=opt)
                loader.add_value('url', response.url)
                loader.add_value('name', main_name + ', ' + opt_name)
                if image_url:
                    loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))

                loader.add_value('price', opt_price)
                loader.add_value('category', category)
                loader.add_value('identifier', opt_id)
                loader.add_value('sku', opt_id)
                loader.add_xpath('brand', 'normalize-space(//a[@class="brand-image-link"]/@title)')
                if 'out of stock' in opt_stock.lower():
                    loader.add_value('stock', 0)

                yield loader.load_item()

    def parse_name(self, title):
        a = title.split('|')
        if(len(a) > 0):
            return a[0].strip()
        else:
            self.log("Can not parse name from title = ", title)
            return title
