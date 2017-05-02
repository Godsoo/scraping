from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items \
import Product, ProductLoaderWithNameStrip as ProductLoader


class SavorySpiceShopSpider(BaseSpider):
    name = 'savoryspiceshop.com'
    allowed_domains = ['savoryspiceshop.com']
    start_urls = ('http://www.savoryspiceshop.com/cart/full-list',)

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        pages_l = hxs.select('//div[@id="full-product-list"]'
                             '//div[contains(@class, "full-list-l")]'
                             '/div/a/@href').extract()
        pages_r = hxs.select('//div[@id="full-product-list"]'
                             '//div[contains(@class, "full-list-r")]'
                             '/div/a/@href').extract()
        products_urls = tuple(pages_l + pages_r)
        for p_url in products_urls:
            yield Request(urljoin_rfc(base_url, p_url),
                          callback=self.parse_product)

    def parse_product(self, response):
        def load_item(response, name, id, category, price, image):
                # Add values
                loader = ProductLoader(response=response, item=Product())
                loader.add_value('name', name)
                loader.add_value('identifier', id)
                loader.add_value('url', response.url)
                loader.add_value('category', category)
                loader.add_value('price', price)
                loader.add_value('image_url', image)

                return loader.load_item()

        hxs = HtmlXPathSelector(response)

        name = \
        hxs.select('//div[@class="info"]/h2/text()').extract().pop().strip()
        crumbs = hxs.select('//ul[@id="crumbs"]/li/a/text()')
        category = crumbs[len(crumbs) - 1].extract()
        image = \
        urljoin_rfc(get_base_url(response),
                    hxs.select('//*[@id="productImageThumbs"]//img')\
                    .select('@src').extract().pop().strip())

        subprds = hxs.select('//div[@class="purchaseInGroup"]/table/tr')

        for prd in subprds:
            first = prd.select('td[@class="first"]')
            firstandsec = prd.select('td[@class="firstAndSecond"]')
            type = ''
            size = ''
            if first:
                type = \
                prd.select('td[@class="type"]/p/text()').extract().pop().strip()
                size = \
                first.select('p/text()').extract().pop().strip()\
                .replace(' ', '')
            elif firstandsec:
                type_xp = firstandsec.select('p').re(r'(.*)<br>.')
                if type_xp:
                    type = type_xp.pop().strip()
                    size = \
                    firstandsec.select('p/span/text()').extract().pop().strip()\
                    .replace('(net', '').replace(')', '').replace(' ', '')
                else:
                    type = \
                    firstandsec.select('p/text()').extract().pop().strip()
            addcard_form = prd.select('td[@class="price"]/form')

            # First Id
            itemid = addcard_form.select('input[@name="ItemId"]')
            id = itemid.select('@value').extract().pop().strip() + '-' + \
            itemid.select('following-sibling::input').select('@name')\
            .extract().pop().strip()
            fullname = unicode(name + ' ' + type + ' ' + size).strip()
            try:
                price = addcard_form.select('p/text()').extract().pop().strip()
            except:
                sub_subprds = addcard_form.select('select/option')
                for sprd_op in sub_subprds:
                    price = sprd_op.select('text()').extract().pop().strip()
                    # Complete Id
                    sprd_id = id + ' ' + \
                    sprd_op.select('@value').extract().pop().strip()
                    yield load_item(response,
                                    fullname, sprd_id, category, price, image)
            else:
                yield load_item(response, fullname, id, category, price, image)
