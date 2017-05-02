import re
import demjson
import decimal
from urlparse import urljoin as urljoin_rfc

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.utils.response import get_base_url
from scrapy.http import Request, FormRequest
from scrapy.utils.url import url_query_parameter, add_or_replace_parameter
from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher

from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from scrapy import log


class BhsSpider(BaseSpider):
    name = 'made-bhs.co.uk'
    allowed_domains = ['bhs.co.uk', 'bhsfurniture.co.uk']
    start_urls = ('http://www.bhs.co.uk/', 'http://www.bhsfurniture.co.uk/')
    index = 0

    def __init__(self, *args, **kwargs):
        super(BhsSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.spider_idle, signals.spider_idle)

    def spider_idle(self, spider):
        if spider.name != self.name:
            return
        for r in self.start_requests():
            self.crawler.engine.crawl(r, self)

    def start_requests(self):
        if self.index >= len(self.start_urls):
            return
        url = self.start_urls[self.index]
        yield self.make_requests_from_url(url)
        self.index += 1

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        if 'bhsfurniture' in response.url:
            urls = hxs.select('//*[@id="menu"]//a/@href').extract()
            for url in urls:
                yield Request(urljoin_rfc(base_url, url), callback=self.parse_product_list2)
        else:
            urls = hxs.select('//*[@id="nav_catalog_menu"]/li[@class="category_471111"]//a/@href').extract()
            for url in urls:
                if 'bhsfurniture' not in url:
                    yield Request(urljoin_rfc(base_url, url), callback=self.parse_product_list)

    def parse_product_list(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        products = hxs.select('//*[@id="wrapper_page_content"]//ul[@class="product"]')
        for product in products:
            url = product.select('./li[1]/a/@href').extract()
            if url:
                url = url[0]
                discount = product.select('./li[contains(@class,"product_promo")]/img/@alt').re(r'(\d+)')
                if discount:
                    url = add_or_replace_parameter(url, 'qbDiscount', discount[0])
                yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)
        if not response.meta.get('all_pages_done', False):
            urls = hxs.select('//div[@class="pages"]//a/@href').extract()
            if urls:
                url = "http://www.bhs.co.uk/webapp/wcs/stores/servlet/CatalogNavigationSearchResultCmd"

                catId = response.xpath('//form[@id="form_mercado_filters"]/input[@name="categoryId"]/@value').extract()[0]
                parent_categoryId = response.xpath('//form[@id="form_mercado_filters"]/input[@name="parent_categoryId"]/@value').extract()[0]
                n_field = response.xpath('//select[@id="sel_sort_field"]/option[@selected="selected"]/@value').extract()[0]
                n_field = url_query_parameter(n_field, 'N').replace(' ', '+')

                dimSelected = "?N="+n_field+"&Ndr=100000&Nr=OR%28emailBackInStock%3AY%2CNOT%28product.inventory%3A0%29%29&siteId=%2F13077&sort_field=Relevance&No=0&Nrpp=9999&catId="+catId+"&parent_categoryId="+parent_categoryId

                formdata = {}
                formdata['langId'] = '-1'
                formdata['storeId'] = response.xpath('//input[@name="storeId"]/@value').extract()[0]
                formdata['isHash'] = 'false'
                formdata['dimSelected'] = dimSelected
                formdata['catalogId'] = response.xpath('//input[@name="catalogId"]/@value').extract()[0]
                yield FormRequest(url, dont_filter=True, formdata=formdata, callback=self.parse_product_list, meta={'all_pages_done': True})

    def parse_product_list2(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        urls = hxs.select('//*[@id="product-holder"]/dl//span[@class="mainProduct"]/a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product2)

    @staticmethod
    def parse_product(response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        discount = url_query_parameter(response.url, 'qbDiscount')

        match = re.search("var productData = (.*?)</script>", response.body, re.DOTALL | re.IGNORECASE)
        if match:
            result = match.group(1)
            prod_name = hxs.select('//*[@id="wrapper_page_content"]//h1/text()').extract()[0]
            sku = hxs.select('//*[@id="product_tab_1"]//li[@class="product_code"]/span/text()').extract()[0]
            image_url = hxs.select('//*[@id="product_view_full"]/@href').extract()
            category = hxs.select('//*[@id="nav_breadcrumb"]//a/span/text()').extract()[1:]
            product_identifier = hxs.select('//*[@id="productId"]/@value').extract()[0]
            options_prices = demjson.decode(result)
            options_prices = options_prices['items']
            options = hxs.select('//*[@id="product_size_full"]/option')[1:]
            for option, price in zip(options, options_prices):
                product_loader = ProductLoader(item=Product(), selector=hxs)
                name = option.select('./text()').extract()[0]
                identifier = option.select('./@value').extract()[0]
                product_loader.add_value('identifier', product_identifier + '_' + identifier)
                product_loader.add_value('name', prod_name + ' ' + name)
                product_loader.add_value('sku', sku)
                if image_url:
                    product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
                price = price['nowprice']
                price = extract_price(str(price))
                if discount:
                    price = round(price - decimal.Decimal(int(discount)/100.0) * price, 2)
                product_loader.add_value('price', price)
                product_loader.add_value('category', transform_category(product_loader.get_output_value('name'), category))
                product_loader.add_value('url', response.url)
                out_of_stock = option.select('./@disabled').extract()
                if out_of_stock:
                    product_loader.add_value('stock', 0)
                product = product_loader.load_item()
                yield product
        else:
            product_loader = ProductLoader(item=Product(), selector=hxs)
            name = hxs.select('//*[@id="wrapper_page_content"]//h1/text()').extract()
            if not name:
                return
            identifier = hxs.select('//*[@id="productId"]/@value').extract()
            if not identifier:
                return
            product_loader.add_value('identifier', identifier[0])
            product_loader.add_value('name', name[0])
            sku = hxs.select('//*[@id="product_tab_1"]//li[@class="product_code"]/span/text()').extract()[0]
            product_loader.add_value('sku', sku)
            image_url = hxs.select('//*[@id="product_view_full"]/@href').extract()
            if image_url:
                product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
            price = hxs.select('//ul[@class="product_summary"]/li[@class="product_price"]/span/text()').extract()[0]
            price = extract_price(price)
            if discount:
                price = round(price - decimal.Decimal(int(discount)/100.0) * price, 2)
            product_loader.add_value('price', price)
            category = hxs.select('//*[@id="nav_breadcrumb"]//a/span/text()').extract()[1:]
            product_loader.add_value('category', transform_category(product_loader.get_output_value('name'), category))
            product_loader.add_value('url', response.url)
            product = product_loader.load_item()
            yield product

    def parse_product2(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        prod_name = hxs.select('//*[@id="productTitle"]/text()').extract()
        if not prod_name:
            return
        prod_name = prod_name[0]
        sku = hxs.select('//*[@id="productCode"]/span/text()').extract()[0].replace('Product No: ', '')
        image_url = hxs.select('//*[@id="flyout"]/img/@src').extract()

        match = re.search(r"OptionsData =  new Array\(\);(.*?)//-->", response.body, re.DOTALL | re.IGNORECASE)
        if match:
            result = match.group(1)
            identifiers = re.findall(r'(?si)\["description"\] = "*(.*?)"*;', result)
            prices = re.findall(r'(?si)\["cost"\] = "*(.*?)"*;', result)
            sizes = re.findall(r'(?si)\["size"\] = "*(.*?)"*;', result)
            colours = re.findall(r'(?si)\["colour"\] = "*(.*?)"*;', result)
            stocks = re.findall(r'(?si)\["stocklevel"\] = "*(.*?)"*;', result)
            for identifier, price, size, colour, stock in zip(identifiers, prices, sizes, colours, stocks):
                product_loader = ProductLoader(item=Product(), selector=hxs)
                name = prod_name
                if colour.lower() != 'no colour':
                    name += ' ' + colour
                if size.lower() != 'no size':
                    name += ' ' + size
                product_loader.add_value('identifier', identifier)
                product_loader.add_value('name', name)
                product_loader.add_value('sku', sku)
                if image_url:
                    product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
                price = extract_price(price.replace('.0000', '.00'))
                product_loader.add_value('price', price)
                category = hxs.select('//*[@id="breadcrumb"]//a/text()').extract()[1:]
                product_loader.add_value('category', transform_category(product_loader.get_output_value('name'), category))
                product_loader.add_value('url', response.url)
                product_loader.add_value('shipping_cost', 35)
                if stock.strip() != '99999':
                    product_loader.add_value('stock', stock)
                product = product_loader.load_item()
                yield product

# original categories are lists, but we can't use lists as keys for dictionary
# to work around this we put joined category name as key to dict, joining by ' > '
# we also put lowercase category names to avoid issues with case
category_mapping = {
    'dining room > dining tables': ['Tables', 'Dining Tables'],
    'living room > coffee tables': ['Tables', 'Coffee Tables'],
    'living room > side tables and nests': ['Tables', 'Side Tables'],
    'office > desks': ['Tables', 'Desks'],
    'bedroom > bedside cabinets': ['Tables', 'Bedside Tables'],
    'living room > tv cabinets': ['Tables', 'TV Stands'],
    'bedroom > dressing tables': ['Tables', 'Dressing Tables'],
    'living room > console tables': ['Tables', 'Console Tables'],
    'living room > bookcases': ['Storage', 'Bookcases & Shelves'],
    'bedroom > wardrobes': ['Storage', 'Wardrobes'],
    'living room > sideboards': ['Storage', 'Sideboards'],
    'bedroom > chest of drawers': ['Storage', 'Chests of Drawers'],
    'home, lighting & furniture > floor lamps': ['Lighting', 'Floor Lamps'],
    'home, lighting & furniture > wall lights': ['Lighting', 'Wall Lights'],
    'home, lighting & furniture > ceiling lights': ['Lighting', 'Ceiling Lamps'],
    'home, lighting & furniture > table lamps': ['Lighting', 'Table Lamps'],
    'sofas & chairs > sofa beds': ['Bedroom', 'Sofa Bed'],
    'bedroom > pocket spring': ['Bedroom', 'Mattresses'],
    'bedroom > open spring': ['Bedroom', 'Mattresses'],
    'bedroom > memory foam': ['Bedroom', 'Mattresses'],
    'bedroom > latex': ['Bedroom', 'Mattresses'],
    'bedroom > pillow top': ['Bedroom', 'Mattresses'],
    'bedroom > all mattresses': ['Bedroom', 'Mattresses'],
    'home, lighting & furniture > cushions': ['Accessories', 'Cushions'],
    'home, lighting & furniture > bins': ['Accessories', 'Bins'],
    'home, lighting & furniture > towels': ['Bed & Bath', 'Bath Towels'],
    'home, lighting & furniture > sheets & pillowcases': ['Bed & Bath', 'Bed Sheets'],
    'home, lighting & furniture > bath mats & pedestal mats': ['Bed & Bath', 'Bath Mats'],
    'home, lighting & furniture > bedding sets': ['Bed & Bath', 'Bed Sets'],
    'dining room > sideboards': ['Storage', 'Sideboards'],
    'bedroom > mirrors': ['Accessories', 'Mirrors']
}

# some categories are mapped to several categories depending on work found in product name
special_category_mapping = {
    'dining room > dining tables': {
        'extending': ['Tables', 'Extending']
    },
    'home, lighting & furniture > mirrors, wall art & clocks': {
        'art': ['Accessories', 'Art'],
        'clock': ['Accessories', 'Clocks'],
        'mirror': ['Accessories', 'Mirrors']
    },
    'home, lighting & furniture > rugs, doormats & poufs': {
        'rug': ['Accessories', 'Rugs']
    }
}


def transform_category(product_name, category):
    """
    >>> transform_category('', ['LIVING ROOM', 'COFFEE TABLES'])
    ['Tables', 'Coffee Tables']
    >>> transform_category('', ['Dining Room', 'Dining Tables'])
    ['Tables', 'Dining Tables']
    >>> transform_category('Something extending', ['Dining Room', 'Dining Tables'])
    ['Tables', 'Extending']
    >>> transform_category('Art object', ['home, lighting & furniture', 'mirrors, wall art & clocks'])
    ['Accessories', 'Art']
    >>> transform_category('Wall clock', ['home, lighting & furniture', 'mirrors, wall art & clocks'])
    ['Accessories', 'Clocks']
    >>> transform_category('Small mirror', ['home, lighting & furniture', 'mirrors, wall art & clocks'])
    ['Accessories', 'Mirrors']
    """
    key_category = ' > '.join(category)
    # check for special categories
    special_cat_data = special_category_mapping.get(key_category.lower())
    if special_cat_data:
        for word in sorted(special_cat_data):
            if word in product_name.lower():
                return special_cat_data[word]
    new_cat = category_mapping.get(key_category.lower())
    if new_cat:
        return new_cat
    return category
