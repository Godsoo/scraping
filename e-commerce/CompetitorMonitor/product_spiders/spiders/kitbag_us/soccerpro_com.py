"""
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4976

The spider crawls Soccer apparel category
Collects all options.
"""
import scrapy
import csv
import os
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from kitbagitems import KitBagMeta
from product_spiders.utils import extract_price
import itertools

HERE = os.path.abspath(os.path.dirname(__file__))

def extract_option_price(option):
    parts = option.split('(Add $')
    if len(parts) < 2:
        return option, 0
    else:
        return parts[0].strip(), extract_price(parts[1].replace(')', ''))


class SoccerproSpider(scrapy.Spider):
    name = 'kitbag-soccerpro.com'
    allowed_domains = ['soccerpro.com']
    start_urls = ('http://www.soccerpro.com/GetGuidedNavigationPageContent.asp?cID=0&scID=2192&mID=-1&SortBy=pricedesc&GdPageSize=100&gnsPvar=&gnsPatt=&gnsBrnd=&gnsPrge=&gnsScat=&gnsRev=&gnsScTree=&pgID=1',)
    teams = {}
    shipping_cost= None
    free_shipping_over = None

    def __init__(self, *args, **kwargs):
        super(SoccerproSpider, self).__init__(*args, **kwargs)

        teams_file = os.path.join(HERE, 'teams.csv')
        with open(teams_file) as f:
            reader = csv.DictReader(f)
            for row in reader:
                team = row['Merret Department'].strip().upper()
                player_name = row['HERO NAME'].strip()
                number = row['HERO NUMBER'].strip()
                if self.teams.get(team):
                    if player_name != 'N/A':
                        self.teams[team][player_name + number] = {'name': player_name,
                                                                  'number': number}
                else:
                    if player_name != 'N/A':
                        self.teams[team] = {player_name + number: {'name': player_name,
                                                                   'number': number}}

    def start_requests(self):
        yield scrapy.Request('http://www.soccerpro.com/store_policies/', callback=self.parse_shipping)

    def parse_shipping(self, response):
        shipping_cost, free_shipping_over = response.xpath(u'//span[contains(text(),"FREE ECONOMY SHIPPING FOR ORDERS OVER $65.00")]/text()')\
                                                     .re(u'\((.*?) for orders less than (.*)\)')
        self.shipping_cost = extract_price(shipping_cost)
        self.free_shipping_over = extract_price(free_shipping_over)
        for url in self.start_urls:
            yield scrapy.Request(url)

    def parse(self, response):
        products = response.xpath('//table[@class="getproductdisplay-innertable"]//td[@class="name-cell"]/a/@href').extract()
        for url in products:
            yield scrapy.Request(response.urljoin(url), callback=self.parse_product)

        for url in response.xpath(
                '//div[@class="pagingtopsectiondiv"]//span[@class="PagingNumbers"]/a/@href').extract():
            url = url.replace("Javascript:fnGetGuidedNavPaging('", '').replace("', '", '')
            yield scrapy.Request(response.urljoin(url), callback=self.parse)

    def parse_product(self, response):
        url = 'http://www.soccerpro.com/Product-Ajax.asp?FormAction=format5grouppageselect&CustomerId=0&IsMobile=false&'
        var_id = response.xpath('//*[@id="hidVariantIdList"]/@value').extract_first()
        group_id = response.xpath('//*[@id="hidProductGroupId"]/@value').extract_first()
        url += 'ProductGroupId={}&VariantIDList={}'.format(group_id, var_id)
        category = response.xpath('//div[@itemprop="breadcrumb"]/a//text()').extract()
        category = [item.replace('>', '').strip() for item in category]
        name = response.xpath('//h1[@class="productgrouppage_name"]/text()').extract_first()

        options_containers = response.xpath('//div[@class="prodpageoptionvalue"]/div/select')
        combined_options = []
        for options_container in options_containers:
            element_options = []
            for option in options_container.xpath('./option[@value!=""]'):
                option_id = option.xpath('./@value').extract_first()
                option_name = option.xpath('./text()').extract_first()
                element_options.append((option_id, option_name))
            combined_options.append(element_options)

        if len(options_containers) > 1:
            combined_options = list(itertools.product(*combined_options))
            for combined_option in combined_options:
                option_name = ''
                option_id = ''
                url_add = ''
                for idx, option in enumerate(combined_option, start=1):
                    option_name += ' ' + option[1]
                    option_id += '_' + option[0]
                    url_add += '&VaraiantID_{}={}'.format(idx,option[0])
                yield scrapy.Request(url + url_add,
                                     callback=self.parse_product_option,
                                     meta={'url': response.url,
                                           'option_name': option_name,
                                           'option_id': option_id,
                                           'category': category,
                                           'name': name,
                                           'size': option[1]})
        else:
            for option in combined_options[0]:
                yield scrapy.Request(url + '&VaraiantID_1={}'.format(option[0]),
                                     callback=self.parse_product_option,
                                     meta={'url': response.url,
                                           'option_name': option[1],
                                           'option_id': option[0],
                                           'category': category,
                                           'name': name,
                                           'size': option[1]})

    def parse_product_option(self, response):
        if "The item is not currently available." in response.body:
            return
        option_name = response.meta.get('option_name')
        option_id = response.meta.get('option_id')
        category = response.meta.get('category')
        name = response.meta.get('name')
        url = response.meta.get('url')
        sku = response.xpath('//span[@itemprop="productID"]/text()').extract_first()
        name += ' ' + option_name
        price = response.xpath('//input[@name="ActProdPrice"]/@value').extract_first()
        price = extract_price(price)
        image_url = response.xpath('//*[@id="main_img"]/@src').extract_first()
        brand = response.xpath('//input[@name="ProdMfgName"]/@value').extract_first()
        out_of_stock = response.xpath('//div[@class="outofstockdiv itemgroup-outofstock"]').extract_first()
        identifier = response.xpath('//input[@name="ProdID"]/@value').extract_first()
        identifier += '_' + option_id

        options_containers = response.xpath('//div[@class="prodpageoptionvalue"]/select')
        combined_options = []
        for options_container in options_containers:
            element_options = []
            for option in options_container.xpath('./option[@value!=""]'):
                option_id = option.xpath('./@value').extract_first()
                option_name = option.xpath('./text()').extract_first()
                option_name, option_price = extract_option_price(option_name)
                element_options.append((option_id, option_name, option_price))
            combined_options.append(element_options)

        if len(options_containers) > 1:
            combined_options = list(itertools.product(*combined_options))
            for combined_option in combined_options:
                o_name, o_price, o_option_id = name, price, identifier
                for option in combined_option:
                    o_option_id = o_option_id + '_' + option[0]
                    if 'do not add' not in option[1].lower():
                        o_name = o_name + ' ' + option[1]
                        o_price = o_price + option[2]
                loader = ProductLoader(item=Product(), response=response)
                loader.add_value('name', o_name)
                loader.add_value('identifier', o_option_id)
                loader.add_value('sku', sku)
                loader.add_value('category', category)
                loader.add_value('url', url)
                loader.add_value('image_url', response.urljoin(image_url))
                loader.add_value('price', o_price)
                loader.add_value('brand', brand)
                if out_of_stock:
                    loader.add_value('stock', 0)
                if o_price < self.free_shipping_over:
                    loader.add_value('shipping_cost', self.shipping_cost)
                option_item = loader.load_item()
                metadata = KitBagMeta()
                metadata['size'] = response.meta['size']
                player_found = False
                for team, players in self.teams.iteritems():
                    for player_id, player in players.iteritems():
                        product_name = option_item['name'].upper()
                        player_name = player['name'].decode('utf')
                        if player_name.upper() in product_name or product_name.split()[0] == player_name.upper():
                            metadata['player'] = player_name
                            metadata['number'] = player['number']
                            player_found = True
                            break
                    if player_found:
                        break
                option_item['metadata'] = metadata
                yield option_item
        else:
            o_name, o_price, o_option_id = name, price, identifier
            if combined_options:
                for option in combined_options[0]:
                    o_option_id = identifier + '_' + option[0]
                    if 'do not add' not in option[1].lower():
                        o_name = name + ' ' + option[1]
                        o_price = price + option[2]
                    loader = ProductLoader(item=Product(), response=response)
                    loader.add_value('name', o_name)
                    loader.add_value('identifier', o_option_id)
                    loader.add_value('sku', sku)
                    loader.add_value('category', category)
                    loader.add_value('url', url)
                    loader.add_value('image_url', response.urljoin(image_url))
                    loader.add_value('price', o_price)
                    loader.add_value('brand', brand)
                    if out_of_stock:
                        loader.add_value('stock', 0)
                    if o_price < self.free_shipping_over:
                        loader.add_value('shipping_cost', self.shipping_cost)
                    option_item = loader.load_item()
                    metadata = KitBagMeta()
                    metadata['size'] = response.meta['size']
                    player_found = False
                    for team, players in self.teams.iteritems():
                        for player_id, player in players.iteritems():
                            product_name = option_item['name'].upper()
                            player_name = player['name'].decode('utf')
                            if player_name.upper() in product_name or product_name.split()[0] == player_name.upper():
                                metadata['player'] = player_name
                                metadata['number'] = player['number']
                                player_found = True
                                break
                        if player_found:
                            break
                    option_item['metadata'] = metadata
                    yield option_item
            else:
                loader = ProductLoader(item=Product(), response=response)
                loader.add_value('name', o_name)
                loader.add_value('identifier', o_option_id)
                loader.add_value('sku', sku)
                loader.add_value('category', category)
                loader.add_value('url', url)
                loader.add_value('image_url', response.urljoin(image_url))
                loader.add_value('price', o_price)
                loader.add_value('brand', brand)
                if out_of_stock:
                    loader.add_value('stock', 0)
                if o_price < self.free_shipping_over:
                    loader.add_value('shipping_cost', self.shipping_cost)
                option_item = loader.load_item()
                metadata = KitBagMeta()
                metadata['size'] = response.meta['size']
                player_found = False
                for team, players in self.teams.iteritems():
                    for player_id, player in players.iteritems():
                        product_name = option_item['name'].upper()
                        player_name = player['name'].decode('utf')
                        if player_name.upper() in product_name or product_name.split()[0] == player_name.upper():
                            metadata['player'] = player_name
                            metadata['number'] = player['number']
                            break
                    if player_found:
                        break
                option_item['metadata'] = metadata
                yield option_item

