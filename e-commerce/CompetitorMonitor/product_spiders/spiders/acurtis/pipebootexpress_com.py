from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request

from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.markup import replace_tags

from product_spiders.items import Product, ProductLoader


class PipebootexpressComSpider(BaseSpider):
    name = 'pipebootexpress.com'
    allowed_domains = ['pipebootexpress.com']
    start_urls = (
        'http://pipebootexpress.com/',
        )

    download_delay = 2

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = hxs.select("//div[@id='dvWrapControl732']//a/@href").extract()
        for link in categories:
            url = urljoin_rfc(base_url, link)
            yield Request(url, callback=self.parse)

        sub_categories = hxs.select('//span[@class="CategoryProductNameLink"]/a/@href').extract()
        for link in sub_categories:
            url = urljoin_rfc(base_url, link)
            yield Request(url, callback=self.parse)

        items = hxs.select("//table[@class='ProductGroup']/tr[@class='ProductGroupItem'] |\
                            //table[@class='ProductGroup']/tr[@class='ProductGroupAlternatingItem']")
        for item in items:
            name = item.select("td[@id='tdProductGroupDisplayDescription']/div/font | \
                                td[@id='tdProductGroupDisplayAltDescription']/div/font").extract()
            if not name:
                print "%s - ERROR! NO NAME!" % response.url
                continue
            name = replace_tags(name[0])
            url = response.url
            price = item.select("td[@id='tdProductGroupDisplayPricing']//text() | \
                                 td[@id='tdProductGroupDisplayAltPricing']//text()").extract()
            if not price:
                print "%s - ERROR! NO PRICE!" % response.url
                continue
            price = price[0].split(',')[0]
            l = ProductLoader(item=Product(), response=response)
            identifier= item.select('td[contains(@id, "ItemNumber")]/input/@value').extract()[0]
            l.add_value('identifier', identifier)
            sku = item.select('td[contains(@id, "ItemNumber")]/span/text()').extract()[0]
            l.add_value('sku', sku)
            l.add_value('name', name)
            l.add_value('url', url)
            l.add_xpath('brand', '//div[@class="ProductDetailsManufacturerName"]/a/img/@alt')

            image_url = hxs.select('//div[@class="ProductDetailsPhoto"]/a/img/@src').extract()
            if image_url:
                l.add_value('image_url', urljoin_rfc(base_url, image_url[0]))

            category = hxs.select('//span[@id="lblCategoryTrail"]/a/text()').extract()[-1]
            l.add_value('category', category)
            l.add_value('price', price)
            in_stock = 'IN STOCK' in ''.join(item.select('td[contains(@id, "Availability")]/span/text()').extract()).upper()
            if not in_stock:
                l.add_value('stock', 0)
            yield l.load_item()
