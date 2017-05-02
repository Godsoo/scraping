'''
Ticket link: https://app.assembla.com/spaces/competitormonitor/tickets/5135
The spider isn't finished in the part of parsing options
'''

from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from scrapy.http import FormRequest
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader


class HarveyNorman(CrawlSpider):
    name = 'expertireland-harveynorman'
    allowed_domains = ['harveynorman.ie']
    start_urls = ['http://www.harveynorman.ie/']
    
    categories = LinkExtractor(restrict_css='.nav-item-level-2')
    products = LinkExtractor(restrict_css='.product-title')
    
    rules = (
        Rule(categories),
        Rule(products, callback='parse_product')
        )
    
    def parse_product(self, response):
        loader = ProductLoader(Product(), response=response)
        identifier = response.xpath('//input[contains(@name, "product_id")]/@value').extract_first()
        loader.add_value('identifier', identifier)
        loader.add_value('url', response.url)
        loader.add_css('name', '.product-header h1::text')
        loader.add_css('price', '.price-num::text', re='[\d.,]+')
        loader.add_xpath('sku', '//script/text()', re='"sku": *"(.+)"')
        loader.add_css('category', 'ul.nav-breadcrumbs a::text')
        loader.add_css('image_url', 'img.pict::attr(src)')
        loader.add_xpath('brand', '//th[contains(.//text(), "Brand")]/following-sibling::td/text()')       
        item = loader.load_item()
        
        attributes = response.xpath('//div[@id="opt_%s"]/div[not(contains(., "Product Care"))]' %identifier)
        if not attributes:
            yield item
            return
        
        variants = dict()
        for attribute in attributes:
            pass

        formdata = {'result_ids': 'product_name_update_%(id)s,product_images_%(id)s_update,price_update_%(id)s,old_price_update_%(id)s,product_options_update_%(id)s,advanced_options_update_%(id)s,qty_update_%(id)s,add_to_cart_update_%(id)s,flexirent_block,finance_pricing_block' %{'id': identifier}}
        
        parameters = {
            'additional_info[detailed_params]': '1',
            'additional_info[features_display_on]': 'C',
            'additional_info[get_detailed]': '1',
            'additional_info[get_discounts]': '1',
            'additional_info[get_for_one_product]': '1',
            'additional_info[get_icon]': '1',
            'additional_info[get_options]': '1',
            'additional_info[get_taxed_prices]': '1',
            'additional_info[info_type]': 'D',
            'appearance[but_role]': 'action',
            'appearance[details_page]': '1',
            'appearance[separate_buttons]': '1',
            'appearance[show_add_to_cart]': '1',
            'appearance[show_old_price]': '1',
            'appearance[show_price]': '1',
            'appearance[show_price_values]': '1',
            'appearance[show_product_options]': '1',
            'appearance[show_qty]': '1',
            'changed_option[%s]' %identifier: '4407',
            'dispatch': 'products.options',
            'product_data[%s][amount]' %identifier: '1',
            'product_data[%s][product_options][4407]' %identifier: '%s' %option_id}


        request = FormRequest.from_response(
            response,
            formname='product_form_%s' %identifier,
            callback=self.parse_option)
            
