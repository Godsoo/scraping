import re
import itertools

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.utils import extract_price

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

try:
    import json
except ImportError:
    import simplejson as json

import logging


class BestmaterialsSpider(BaseSpider):
    name = "bestmaterials"
    allowed_domains = ["bestmaterials.com"]
    start_urls = (
        'http://www.bestmaterials.com/',
        )
    manufacturers_urls = (
        'http://www.bestmaterials.com/SearchResult.aspx?Manufacturer=14',
        'http://www.bestmaterials.com/SearchResult.aspx?Manufacturer=54',
        'http://www.bestmaterials.com/SearchResult.aspx?Manufacturer=115',
        'http://www.bestmaterials.com/SearchResult.aspx?Manufacturer=104',
        )
    cat_1_url = 'http://www.bestmaterials.com/retrofit_pipe_flashing_boots.aspx'
    cat_2_url = 'http://www.bestmaterials.com/masterflash_sizes_and_materials.aspx'
    other_categories_urls = ['http://www.bestmaterials.com/Supports_stands.aspx',
                             'http://www.bestmaterials.com/pipe-clamp-strap-609.html',
                             'http://www.bestmaterials.com/SearchResult.aspx?KeyWords=support+pad',
                             'http://www.bestmaterials.com/SearchResult.aspx?categoryid=1176',
                             'http://www.bestmaterials.com/masterflash-rubber-pipe-flashings-683.html',
                             'http://www.bestmaterials.com/SearchResult.aspx?CategoryID=1445',
                             'http://www.bestmaterials.com/SearchResult.aspx?CategoryID=1348',
                             'http://www.bestmaterials.com/roof-drains-463.html']

    products_urls = (
        'http://www.bestmaterials.com/detail.aspx?ID=17345',
        'http://www.bestmaterials.com/detail.aspx?ID=17347',
        'http://www.bestmaterials.com/detail.aspx?ID=17348',
        'http://www.bestmaterials.com/detail.aspx?ID=17349',
        'http://www.bestmaterials.com/detail.aspx?ID=17271',
        'http://www.bestmaterials.com/detail.aspx?ID=17272',
        'http://www.bestmaterials.com/detail.aspx?ID=17273',
        'http://www.bestmaterials.com/detail.aspx?ID=17274',
        'http://www.bestmaterials.com/detail.aspx?ID=17275',
        )

    def parse(self, response):

        yield Request(self.cat_1_url, callback=self.parse_1_cat)
        yield Request(self.cat_2_url, callback=self.parse_2_cat)

        for url in self.other_categories_urls:
            yield Request(url, callback=self.parse_categories)

        for url in self.manufacturers_urls:
            yield Request(url, callback=self.parse_manufacturer)

        for url in self.products_urls:
           yield Request(url, callback=self.parse_item)


    def parse_categories(self, response):
        hxs = HtmlXPathSelector(response)
        categories = hxs.select('//td[@id="ContentCell"]//a[contains(@href, "CategoryID")]/@href')
        for url in categories:
            yield Request(url, callback=self.parse_categories)

        base_url = get_base_url(response)
        items = hxs.select('//a[contains(@id, "SearchTemplate13_DataGrid1") and contains(@id, "lnkProductName")]/@href').extract()
        if items:
            for item in items:
                yield Request(urljoin_rfc(base_url, item), callback=self.parse_item, meta={'brand':''})

            # pages
            content = hxs.select("//td[@id='ContentCell']/table/tr/td[@class='Content']")
            items = content.select("div[@align='right']/div/table[2]")
            next_page = items.select("tr[@class='Content']/td/a[contains(text(), 'Next')]/@href").extract()
            if next_page:
                m = re.search("doPostBack\('(.*?)','(.*?)'\)", next_page[-1])
                if m:
                    target = m.group(1)
                    target = target.replace('$', ':')
                    argument = m.group(2)

                    params = dict(zip(hxs.select('//form/input/@name').extract(), hxs.select('//form/input/@value').extract()))
                    params['__EVENTARGUMENT'] = argument
                    params['__EVENTTARGET'] = target

                    request = FormRequest(
                        url=response.url,
                        formdata=params,
                        callback=self.parse_categories,
                        dont_filter=True,
                    )
                    yield request
        
    def parse_1_cat(self, response):
        hxs = HtmlXPathSelector(response)
        content = hxs.select("//td[@id='ContentCell']/table/tr/td")
        items = content.select("div[@align='center']/center/table[@id='AutoNumber1']/*/tr/td[1]")
        items = items.select(".//a/@href").extract()
        for item in items:
            yield Request(item, callback=self.parse_item)

        items = content.select("div[@align='center']/center/table[@id='AutoNumber2']/tr/td[1]")
        items = items.select(".//a/@href").extract()
        for item in items:
            yield Request(item, callback=self.parse_item)

    def parse_2_cat(self, response):
        hxs = HtmlXPathSelector(response)
        content = hxs.select("//td[@id='ContentCell']/table/tr/td")
        items = content.select('//a[contains(@href, "http://www.bestmaterials.com/detail.aspx?ID=")]/@href').extract()
        for item in items:
            yield Request(item, callback=self.parse_item)

    def parse_manufacturer(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        items = hxs.select('//a[contains(@id, "SearchTemplate13_DataGrid1") and contains(@id, "lnkProductName")]/@href').extract()
        brand = hxs.select('//td[@class="ContentTableHeader"]/span/text()').extract()
        brand = brand[0] if brand else ''
        for item in items:
            yield Request(urljoin_rfc(base_url, item), callback=self.parse_item, meta={'brand':brand})

        # pages
        content = hxs.select("//td[@id='ContentCell']/table/tr/td[@class='Content']")
        items = content.select("div[@align='right']/div/table[2]")
        next_page = items.select("tr[@class='Content']/td/a[contains(text(), 'Next')]/@href").extract()
        if next_page:
            m = re.search("doPostBack\('(.*?)','(.*?)'\)", next_page[-1])
            if m:
                target = m.group(1)
                target = target.replace('$', ':')
                argument = m.group(2)

                params = dict(zip(hxs.select('//form/input/@name').extract(), hxs.select('//form/input/@value').extract()))
                params['__EVENTARGUMENT'] = argument
                params['__EVENTTARGET'] = target

                request = FormRequest(
                    url=response.url,
                    formdata=params,
                    callback=self.parse_manufacturer,
                    dont_filter=True,
                )
                yield request

    def parse_item(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        name = hxs.select("//tr[@id='ProductDetail11_trProductName']/td/text()").extract()
        if name:
            name = name[0].strip()
            url = response.url
            price = hxs.select("//tr[@id='ProductDetail11_trCustomPrice']/td/font/b/text()").extract()
            if not price:
                price = hxs.select("//tr[@id='ProductDetail11_trPrice']/td/text()").extract()

            l = ProductLoader(item=Product(), response=response)
            l.add_value('identifier', url.split('ID=')[-1])
            l.add_value('name', name)
            l.add_value('url', url)
            l.add_value('brand', response.meta.get('brand'))
            l.add_value('category', response.meta.get('brand'))
            sku = hxs.select('//tr[@id="ProductDetail11_trProductCode"]/td/text()').extract()[0]
            l.add_value('sku', sku)
            image_url = hxs.select('//table[@id="ProductDetail11_ProductImage"]//img/@src').extract()
            if image_url:
                l.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
            l.add_value('price', extract_price(price[0]))
            if not price:
                l.add_value('stock', 0)
            product = l.load_item()
            options = self.get_options(response)
            if options:
                identifier = product['identifier']
                price = product['price']
                for option in options:
                    product['identifier'] = identifier + option[0]
                    product['name'] = name + ' ' + option[1]
                    product['price'] = price + option[2]
                    yield product
            else:
                yield product
        else:
            # may be several products
            products = hxs.select("//table[@id='SearchTemplate13_DataGrid1']// \
                                     table[@id='SearchTemplate13_DataGrid1__ctl3_ProductInfoTable']")
            for product in products:
                url = product.select("//tr[@id='SearchTemplate13_DataGrid1__ctl3_ProductNameRow']/td/a/@href").extract()
                if url:
                    yield Request(urljoin_rfc(base_url, url[0]), callback=self.parse_item)

    def get_options(self, response):
        hxs = HtmlXPathSelector(response)
        options = []
        options_containers =  hxs.select('//select[@class="Content"]')

        combined_options = []
        for options_container in options_containers:
            element_options = []
            for option in options_container.select('option[@value!="-1"]'):
                option_id = option.select('@value').extract()[0]
                option_split = option.select('text()').extract()[0].split(' (Add')
                option_desc = option_split[0]
                if len(option_split)>1:
                    price = extract_price(option_split[1])
                else:
                    price = 0
                element_options.append((option_id, option_desc, price))
            combined_options.append(element_options)
            
        combined_options =  list(itertools.product(*combined_options))
        for combined_option in combined_options:
            name, price, option_id = '', 0, ''
            for option in combined_option:
                option_id = option_id + '-' + option[0]
                name = name + ' - ' + option[1]
                price = price + option[2]
            options.append((option_id, name, price))
        return options
