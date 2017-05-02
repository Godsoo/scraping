from product_spiders.base_spiders.primary_spider import PrimarySpider

from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

class DV247(PrimarySpider):
    name = 'dv247.com-studioxchange'
    allowed_domains = ['dv247.com', 'www.dv247.com']
    start_urls = ('http://www.dv247.com',)

    csv_file = 'dv247.com_products.csv'

    urls_ = []

    def parse_product(self, response):
        URL_BASE = 'http://www.dv247.com'

        hxs = HtmlXPathSelector(response)

        products = hxs.select('//div[@class="listItem clearfix"]')
        for p in products:
            name = ' '.join(p.select('.//a//text()').extract())
            url = p.select('.//a/@href')[0].extract()
            if url not in self.urls_:
                self.urls_.append(url)
                sku = url.split('--')[-1] if url.split('--') else ''
                identifier = sku
                url = urljoin_rfc(URL_BASE, url)
                category = ''.join(hxs.select('//div[@id="categoryHeader"]/h1/text()').extract()).strip()
                if not category:
                    category = ''.join(hxs.select('//select[@id="List_Filter_ListCategories"]/option[@selected]/text()').extract())
                    category = category.split(' (')[0] if category else ''

                brand = ''.join(p.select('div/ul/li/a/text()').extract()).strip()
                image_url = hxs.select('//img[contains(@src, "'+sku+'")]/@src').extract()
                image_url = urljoin_rfc(URL_BASE, image_url[0]) if image_url else ''

                price = p.select('.//li[@class="price"]/text()').re('\xa3(.*)')[0].replace(",", "")

                loader = ProductLoader(item=Product(), response=response)
                loader.add_value('url', url)
                loader.add_value('name', name)
                loader.add_value('sku', sku)
                loader.add_value('identifier', identifier)
                loader.add_value('price', price)
                loader.add_value('image_url', image_url)
                loader.add_value('category', category)
                loader.add_value('brand', brand)
                yield loader.load_item()

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        fields = ['__VIEWSTATE', '__EVENTVALIDATION', '__EVENTTARGET', '__EVENTARGUMENT', 'Search1$SearchPhrase']
        formdata = {}
        for field in fields:
            if hxs.select('//input[@id="' + field + '"]/@value').extract():
                formdata[field] = hxs.select('//input[@id="' + field + '"]/@value').extract()[0]
            else:
                formdata[field] = ''

        formdata['Localisation$Currency'] = 'GBP'

        r = FormRequest(response.url, formdata=formdata, callback=self.main_parse)
        yield r

    def main_parse(self, response):
        if not isinstance(response, HtmlResponse):
            return
        URL_BASE = 'http://www.dv247.com'
        # categories
        hxs = HtmlXPathSelector(response)
        # category_urls = hxs.select('//nav[@id="megamenu"]/ul/li/a/@href | \
        #                            //nav[@id="megamenu"]//li[@class="accessories threeCol"]//a/@href').extract()
        category_urls = hxs.select('//nav[@id="megamenu"]//ul[@class="sub"]/li/dl/dd/a/@href').extract()
        # the following category had to be added manually because the link is broken.
        category_urls.append('/computer-music-software/')
        for url in category_urls:
            if url == '#':
                continue
            url = urljoin_rfc(URL_BASE, url)
            r = Request(url)
            yield r

        # next page
        next_pages = hxs.select('//div[@class="listPaging"]')
        if next_pages:
            next_pages = next_pages[0].select('.//a[not(@class="selectedpage")]/@href').extract()
            for page in next_pages:
                url = urljoin_rfc(URL_BASE, page)
                r = Request(url)
                yield r

        # products
        for p in self.parse_product(response):
            yield p
