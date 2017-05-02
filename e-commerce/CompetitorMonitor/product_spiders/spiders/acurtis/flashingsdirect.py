from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest

from product_spiders.items import Product, ProductLoader

import json

json_api_url = "http://www.flashingsdirect.com/remote.php"
json_api_request_args = {
    'action': 'add',
    'currency_id': '',
    'product_id': '',
    'qty[]': '',
    'variation_id': '',
    'w': 'getProductAttributeDetails'
}

class Options(object):
    def __init__(self, selects):
        self.data = {}
        self.create_data_array(selects)
        self.selects_count = len(self.data)

    def gen(self, items=None):
        if items is None:
            items = []
        # Generator returns [("opt1", (1, "title1")), ("opt2", (2, "title2"))]    [("opt1", (1, "title1")), ("opt2", (3, "title3"))]
        index = len(items)
        if not len(self.data):
            return
        if index >= len(self.data):
            yield items
            return
        option_name, options = self.data.items()[index]
        for name, val in options.items():
            for item in self.gen(items + [(option_name, (name, val))]):
                yield item

    def create_data_array(self, selects):
        for select in selects:
            name = select.select("@name").extract()[0]
            self.data[name] = {}
            for option in select.select('option'):
                option_name = option.select("text()").extract()[0]
                option_value = option.select("@value").extract()[0]
                if option_value:
                    self.data[name][option_value] = option_name


class FlashingsdirectSpider(BaseSpider):
    name = "flashingsdirect"
    allowed_domains = ["flashingsdirect.com"]
    start_urls = (
            'http://www.flashingsdirect.com/categories/Pipe-Flashings/All-Pipe-Flashings/',
        )

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        categories = hxs.select('//ul[@class="category-list"]/li/a/@href').extract()
        for category in categories:
            yield Request(category)

        sub_categories = hxs.select('//div[@class="SubCategoryListGrid"]/ul/li/a/@href').extract()
        for sub_category in sub_categories:
            yield Request(sub_category)

        items = hxs.select("//div[@id='CategoryContent']//ul/li")
        if items:
            category = hxs.select('//div[@id="CategoryBreadcrumb"]//li/a/text()').extract()
            category = category[0] if category else ''
            for item in items:
                for url in item.select("//strong//a/@href").extract():
                    yield Request(url, callback=self.parse_item, meta={'category':category})

    def parse_item(self, response):
        hxs = HtmlXPathSelector(response)
        image_url = hxs.select('//div[@class="ProductThumbImage"]/a/@href').extract()
        image_url = image_url[0] if image_url else ''
        brand = hxs.select('//h4[@class="BrandName"]/a/text()').extract()
        brand = brand[0] if brand else ''
        items = hxs.select("//div[@id='ProductDetails']/div[@class='BlockContent']")
        for item in items:
            title = item.select('.//div[@class="ProductDetailsGrid"]//h1/text()').extract()[0]
            url = response.url
            product_id = item.select(
                ".//input[@type='hidden' and @name='product_id']/@value").extract()[0]
            select_el = item.select(
                ".//div[@class='productOptionViewSelect']/select")
            options = list(Options(select_el).gen())
            if options:
                field_name = select_el.select("@name").extract()[0]
                for option in options:
                    options_dict = {x[0]: x[1][0] for x in option}
                    item_options = json_api_request_args.copy()
                    item_options.update(options_dict)
                    item_options['product_id'] = product_id

                    new_item_name = title + " " + " ".join([x[1][1] for x in option])
                    request = FormRequest(
                        url=json_api_url,
                        formdata=item_options,
                        callback=self._parse_item_json
                    )
                    request.meta['item_name'] = new_item_name
                    request.meta['item_url'] = url
                    request.meta['subtype_id'] = "-".join([x[1][0] for x in option])
                    request.meta['product_id'] = product_id
                    request.meta['image_url'] = image_url
                    request.meta['brand'] = brand
                    request.meta['category'] = response.meta.get('category')
                    yield request
            else:
                l = ProductLoader(item=Product(), response=response)
                l.add_value('identifier', product_id)
                l.add_value('name', title)
                l.add_value('url', url)
                l.add_value('image_url', image_url)
                l.add_value('category', response.meta.get('category'))
                l.add_value('brand', brand)
                l.add_xpath('price', '//div[contains(@class, "PriceRow")]/div/span/text()')
                yield l.load_item()
                


    def _parse_item_json(self, response):
        item_name = response.request.meta['item_name']
        product_id = response.request.meta['product_id']
        item_name = response.request.meta['item_name']
        item_url = response.request.meta['item_url']
        image_url = response.request.meta['image_url']
        category = response.request.meta['category']
        brand = response.request.meta['brand']
        subtype_id = response.request.meta['subtype_id']
        data = json.loads(response.body)
        price = data['details']['unformattedPrice']

        l = ProductLoader(item=Product(), response=response)
        l.add_value('identifier', product_id + '-' + subtype_id)
        l.add_value('name', item_name)
        l.add_value('url', item_url)
        l.add_value('image_url', image_url)
        l.add_value('category', category)
        l.add_value('brand', brand)
        l.add_value('price', price)
        return l.load_item()
