import re, json, itertools, sys

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price
from scrapy.http import Request
from scrapy.selector import HtmlXPathSelector
from scrapy.spider import BaseSpider


class SwivelukUkSpider(BaseSpider):

    name            = 'swiveluk_uk'
    allowed_domains = ['swiveluk.com']
    start_urls      = ('http://www.swiveluk.com/uk/',)


    def parse(self, response):

        hxs = HtmlXPathSelector(response)
        categories = hxs.select("//ul[@id='nav']//a[not(@class='level-top')]/@href").extract()

        for category in categories:
            yield Request(category, callback=self.parse_pagination)


    def parse_pagination(self, response):

        hxs = HtmlXPathSelector(response)

        products = hxs.select("//div[@class='category-products']//li[contains(@class,'productli item')]/@onclick").extract()
        for product in products:
            url = self.get_url(product)
            yield Request(url, callback=self.parse_product, dont_filter=True)


    def parse_product(self, response):

        hxs = HtmlXPathSelector(response)

        image_url    = hxs.select("//div[@class='product-image']//img[contains(@id,'image')]/@src").extract()[0]
        categories   = hxs.select("//ul[@itemprop='breadcrumb']//a/text()").extract()[1:]
        price        = ''.join(hxs.select('//span[@itemprop="price"]//text()').extract())
        price        = float(extract_price(price))
        brand        = ''.join(hxs.select("//a[@itemprop='brand']/span/text()").extract())
        sku          = hxs.select('//input[@name="product"]/@value').extract()[0]
        shipping     = 0

        product_name = ''.join(hxs.select("//h1[@itemprop='name']/text()").extract())
        if not product_name:
            product_name = ''.join(hxs.select("//ul[@itemprop='breadcrumb']//li[@class='product']//text()").extract())

        #== We are currently not using color options ==#

        options_groups = []
        options = hxs.select("//div[@id='product-options-wrapper']//dl/dt")
        options = [option for option in options if not 'colour' in option.extract().lower()]

        if options:
            try:
                for option in options:
                    option_ids = option.select("./following::dd[1]/div/ul/li/a/@onclick").extract()
                    if option_ids:
                        if 'attribute' in option_ids[0]:
                            option_ids = option.select("./following::dd[1]/div/ul/li/a/@onmouseover").extract()
                            option_ids = [re.findall(re.compile("(\d+)"), option_id)[0] for option_id in option_ids]
                        else:
                            option_ids = [re.findall(re.compile("\'(\d*)\'\); "), option_id)[0] for option_id in option_ids]

                        options_groups.append(option_ids)
                    else:
                        continue

                more_options = hxs.select("//select[contains(@name,'options')]/option[@value]/@value").extract()
                more_options = [more_option for more_option in more_options if more_option]
                options_groups.append(more_options)
                options_groups = [options_group for options_group in options_groups if  options_group]

                if options_groups:

                    #== DONT PANIC ==#
                    #== Options can be stored in several ways on the page ==#
                    option_values = {}
                    option_values_raw = re.search('new Product.Bundle\((.*)\);', response.body) #First way
                    option_values_raw = json.loads(option_values_raw.group(1)) if option_values_raw else None

                    if option_values_raw:
                        for products_set, product_set_value in option_values_raw['options'].iteritems():
                            for option, values in product_set_value['selections'].iteritems():
                                option_values[option] = values

                    option_values_raw = re.search('new Product.Config\((.*)\);', response.body) #Second way
                    option_values_raw = json.loads(option_values_raw.group(1)) if option_values_raw else None

                    if more_options:
                        more_options = re.search('Product.Options\((.*)\);', response.body) #These options don't affect price
                        more_options = json.loads(more_options.group(1)) if more_options else None

                    if option_values_raw:
                        for products_set, product_set_value in option_values_raw['attributes'].iteritems():
                            for values in product_set_value['options']:
                                option_values[values['id']] = values
                                option_values[values['id']]['priceValue'] = values['price']
                                option_values[values['id']]['name'] = values['label']


                    #== All possible combinations of options e.g.: Color1+Size1, Color2+Size1... ==#
                    all_combinations = list(itertools.product(*options_groups))
                    for combinations in all_combinations:
                        product_loader = ProductLoader(item=Product(), selector=hxs)
                        option_name    = product_name
                        option_price   = price
                        option_id      = sku
                        for combination in combinations:
                            #== sorry for long lines ==#
                            try:
                                tmp_name = hxs.select("//option[@value='{}']/text()".format(combination)).extract()[0].strip()
                            except:
                                tmp_name = option_values[combination]['name']

                            tmp_price    = option_values.get(combination)
                            tmp_price    = float(tmp_price['priceValue']) if tmp_price else 0

                            option_name  = option_name  + ' ' + tmp_name
                            option_price = option_price + tmp_price
                            option_id    = option_id    + combination

                        option_name = ' '.join(option_name.split()).replace("\n", "")
                        product_loader.add_value('image_url', image_url)
                        product_loader.add_value('shipping_cost', shipping)
                        product_loader.add_value('sku', sku)
                        product_loader.add_value('url', response.url)
                        for category in categories:
                            product_loader.add_value('category', category)
                        product_loader.add_value('name', option_name)
                        product_loader.add_value('brand', brand)
                        product_loader.add_value('identifier', option_id)
                        product_loader.add_value('price', option_price)

                        yield product_loader.load_item()

            except Exception as e:
                raise NameError(e)
                print 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)

        #== If no options found ==#
        else:
            product_loader = ProductLoader(item=Product(), selector=hxs)
            product_loader.add_value('image_url', image_url)
            product_loader.add_value('shipping_cost', shipping)
            product_loader.add_value('sku', sku)
            product_loader.add_value('url', response.url)
            for category in categories:
                product_loader.add_value('category', category)
            product_loader.add_value('name', product_name)
            product_loader.add_value('brand', brand)
            product_loader.add_value('identifier', sku)
            product_loader.add_value('price', price)

            yield product_loader.load_item()



    def get_url(self, product):

        url = product.replace('setLocation(\'', '').replace('\')', '')
        return url
