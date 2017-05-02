import itertools
from scrapy import Spider, Request
from scrapy.utils.url import add_or_replace_parameter
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
from product_spiders.utils import extract_price_eu


class MaisonsDuMonde(Spider):
    name = 'maisonsdumonde.com'
    allowed_domains = ['maisonsdumonde.com']
    start_urls = ['http://www.maisonsdumonde.com/FR/fr']

    def parse(self, response):
        categories = response.xpath('//nav[@id="primarynav"]//a/@href').extract()
        for url in categories:
            yield Request(response.urljoin(url), callback=self.parse_category)

    def parse_category(self, response):
        for url in response.xpath('//section[@id="results"]//a/@href').extract():
            yield Request(response.urljoin(url), callback=self.parse_product)

        page_size = 48
        current_page = int(response.meta.get('current_page', 0))  # The page starts in 0
        total_products = response.xpath('//span[@id="TQA_nb_products"]/text()').re(r'(\d+)')
        if not total_products:
            self.log('WARNING: Total products not found => %s' % response.url)
            return

        if ((current_page + 1) * page_size) < int(total_products[0]):
            next_page = current_page + 1
            yield Request(add_or_replace_parameter(response.url, 'page', str(next_page)),
                          meta={'current_page': next_page},
                          callback=self.parse_category)

    def parse_product(self, response):
        if not response.xpath('//div[@id="product"]'):
            return

        for url in response.xpath('//ul[@class="options-types"]//a/@href').extract():
            yield Request(response.urljoin(url), callback=self.parse_product)

        loader = ProductLoader(item=Product(), response=response)
        xpath = '//script/text()'
        pattern = "tc_vars\['%s'\] = '(.+)'"
        loader.add_xpath('identifier', xpath, re=pattern % 'product_id')
        loader.add_xpath('sku', xpath, re=pattern % 'product_id')
        loader.add_xpath('name', xpath, re=pattern % 'product_name')
        image_url = response.xpath(xpath).re(pattern % 'product_url_picture')
        if image_url:
            image_url = response.urljoin(image_url[0])
            loader.add_value('image_url', image_url)
        loader.add_xpath('url', xpath, re=pattern % 'product_url_page')
        loader.add_xpath('price', xpath, re=pattern % 'product_totalprice_ati')
        categories = response.xpath('//nav[@class="breadcrumb"]//span/text()').extract()
        loader.add_value('category', categories[1:-1])
        loader.add_value('stock', int(response.xpath(xpath).re(pattern % 'product_instock')[0] == 'Y'))
        product = loader.load_item()

        opt = True
        options = []
        for group in response.xpath('//div[@class="options-list"]/form/div'):
            for ul in group.select('./ul'):
                options.append(ul.select('./li'))
                try:
                    product['name'] += ' ' + ul.select('.//input[@checked]/../label/text()').extract()[0]
                except:
                    opt = False
            if group.select('./div'):
                if group.select('./div/ul'):
                    options.append(group.select('.//li'))
                    product['name'] += ' ' + group.select('.//input[@checked]/../label/text()').extract()[0]
                elif group.select('./div/select'):
                    option = {'name':group.select('./h2/text()').re('\d*\.(.+)')[0].strip()}
                    option['url_name'] = group.select('.//select/@name').extract()[0]
                    option['price'] = extract_price_eu(group.select('.//label/text()').extract()[0])
                    opts = []
                    for opt in group.select('.//select/option'):
                        d = option.copy()
                        d['selector'] = opt
                        opts.append(d)
                    options.append(opts)
                    product['name'] += ' ' + group.select('./h2/text()').re('\d*\.(.+)')[0].strip()
                    product['name'] += ' ' + group.select('.//option[@selected]/text()').extract()[0]
        if opt:
            yield product
        struct_id = response.xpath('//form[@id="formCombinationOptions"]/input[1]/@value').extract()
        if not struct_id:
            return
        struct_id = struct_id[0]
        struct_name = response.xpath('//form[@id="formCombinationOptions"]/input[1]/@name').extract()[0]
        url_pattern = 'http://www.maisonsdumonde.com/FR/fr/%s/productCombinationUpdate?%s=%s' %(struct_id, struct_name, struct_id)
        variants = itertools.product(*options)
        for variant in variants:
            item = Product(product)
            url = url_pattern
            head_id = ''
            for option in variant:
                if not type(option) is dict:
                    if option.select('.//@data-headref'):
                        head_id = option.select('.//@data-headref').extract()[0]
                    url += '&' + option.select('.//@name').extract()[0] + '=' + option.select('.//@value').extract()[0]
                    item['name'] += ' ' + option.select('.//label/text()').extract()[0]
                    item['identifier'] += '-' + option.select('.//input/@value').extract()[0]
                    price = option.select('.//span[@class="price"]/text()[preceding-sibling::br]').extract()
                    if price:
                        item['price'] += extract_price_eu(price[0])
                else:
                    url += '&' + option['url_name'] + '=' + option['selector'].select('.//@value').extract()[0]
                    item['name'] += ' ' + option['name'] + ' ' + option['selector'].select('./text()').extract()[0]
                    quantity = option['selector'].select('./@value').extract()[0]
                    item['identifier']  += '-' + quantity
                    item['price'] += option['price'] * int(quantity)
            if head_id:
                url += '&combinationProduct[head]=%s' %head_id
            yield Request(url, callback=self.parse_product)
