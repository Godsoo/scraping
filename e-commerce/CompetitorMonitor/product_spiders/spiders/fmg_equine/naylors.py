# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from scrapy.http import Request, FormRequest
import re, json



class NaylorsSpider(BaseSpider):

    name              = "naylors"
    allowed_domains   = ["naylors.com"]
    start_urls        = ["http://www.naylors.com"]
    base_url          = "http://www.naylors.com"


    def parse(self, response):

        hxs = HtmlXPathSelector(response=response)
        categories = hxs.select("//a[@class='col-title']/following::ul/li/a/@href").extract()

        for category in categories:

            link = self.base_url + category

            yield Request(url=link, callback=self.parse_top_category)


    def parse_top_category(self, response):

        hxs = HtmlXPathSelector(response=response)
        products = hxs.select("//div[@class='category-products']/ul/li")

        for product in products:

            name = product.select(".//h2[@class='product-name']/a/text()").extract()[0]
            url  = product.select(".//h2[@class='product-name']/a/@href").extract()[0]

            yield Request(url=url, meta={'name': name}, callback=self.parse_item)
        
        #== Look for the 'next page' button ==#
        try:
            next_page = hxs.select("//a[@class='next']/@href").extract()[0]
            yield Request(next_page, callback=self.parse_top_category)
        except:
            pass
        

        
    def parse_item(self, response):

        hxs  = HtmlXPathSelector(response)
        options = hxs.select("//fieldset[@id='product-options-wrapper']//option[@value]")

        for i in range(120,150):
            i = str(i)
            try:
                options = json.loads(re.findall(re.compile('new Product\.Config\((.+?)\);'), response.body)[0])['attributes'][i]['options']
            except:
                continue

        if not options:

            l = ProductLoader(item=Product(), response=response)

            try:
                price  = hxs.select("//div[@class='price-box']/meta[@itemprop='price']/@content").extract()[0].replace(',', '').replace('[', '').replace(']', '')
            except:
                try:
                    price  = hxs.select("//div[@class='price-box']//span[@class='price']/text()").extract()[0].strip()[1:].replace(',', '').replace('[', '').replace(']', '')
                except:
                    return

            price      = float(price)
            stock      = 1 if 'instock' in hxs.select("//link[@itemprop='availability']/@href").extract()[0].lower() else 0
            brand      = ''.join(hxs.select("//th[text()='Brand']/following::td[1]/text()").extract())
            sku        = hxs.select("//span[@itemprop='sku']/text()").extract()[0].strip()
            categories = hxs.select("//nav[@class='breadcrumbs']//a/text()").extract()[1:]
            image_url  = ''.join(hxs.select("//img[@id='image']/@src").extract())
            identifier = sku

            if not categories:
                breadcrumbs = hxs.select("//div[@class='block more-from']/ul")
                for breadcrumb in breadcrumbs:
                    categories = breadcrumb.select("./li")
                    if len(categories) == 3:
                        categories_tmp = []
                        for category in categories:
                            categories_tmp.append(category.select("./a/text()").extract()[0])
                        categories = categories_tmp
                        break

            l.add_value('name',          response.meta['name'])
            l.add_value('image_url',     image_url)
            l.add_value('url',           response.url)
            l.add_value('price',         price)
            l.add_value('stock',         stock)
            l.add_value('brand',         brand)
            l.add_value('identifier',    identifier)
            l.add_value('sku',           sku)

            for category in categories:
                l.add_value('category', category)

            yield l.load_item()

        else:
            for option in options:

                l = ProductLoader(item=Product(), response=response)

                option_id    = option['id']
                option_price = float(option['price'])
                option_name  = option['label']

                try:
                    price  = hxs.select("//div[@class='price-box']/meta[@itemprop='price']/@content").extract()[0].replace(',', '').replace('[', '').replace(']', '')
                except:
                    try:
                        price  = hxs.select("//div[@class='price-box']//span[@class='price']/text()").extract()[0].strip()[1:].replace(',', '').replace('[', '').replace(']', '')
                    except:
                        return

                price      = option_price+float(price) if not option_price == 0 else float(price)
                price      = round(price, 2)
                stock      = 1 if 'instock' in hxs.select("//link[@itemprop='availability']/@href").extract()[0].lower() else 0
                brand      = ''.join(hxs.select("//th[text()='Brand']/following::td[1]/text()").extract())
                sku        = hxs.select("//span[@itemprop='sku']/text()").extract()[0].strip() + '-' + str(option_id)
                categories = hxs.select("//nav[@class='breadcrumbs']//a/text()").extract()[1:]
                image_url  = ''.join(hxs.select("//img[@id='image']/@src").extract())
                identifier = sku

                if not categories:
                    breadcrumbs = hxs.select("//div[@class='block more-from']/ul")
                    for breadcrumb in breadcrumbs:
                        categories = breadcrumb.select("./li")
                        if len(categories) == 3:
                            categories_tmp = []
                            for category in categories:
                                categories_tmp.append(category.select("./a/text()").extract()[0])
                            categories = categories_tmp
                            break

                l.add_value('name',          response.meta['name'] + ' ' + option_name)
                l.add_value('image_url',     image_url)
                l.add_value('url',           response.url)
                l.add_value('price',         price)
                l.add_value('stock',         stock)
                l.add_value('brand',         brand)
                l.add_value('identifier',    identifier)
                l.add_value('sku',           sku)

                for category in categories:
                    l.add_value('category', category)

                yield l.load_item()