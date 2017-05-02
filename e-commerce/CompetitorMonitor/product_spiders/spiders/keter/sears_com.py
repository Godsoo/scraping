import urllib
import logging
import re

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from scrapy import log

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from keteritems import KeterMeta, Review, ReviewLoader

brands = (
    'Keter',
    'Suncast',
    'Rubbermaid',
    'Lifetime',
    'Step 2',
    'Step2',
    'Sterilite',
)

brands_list_urls = [
    'http://www.sears.com/brand-lawn-garden/sbi-1020001',
    'http://www.sears.com/brand-automotive/sbi-1020005',
    'http://www.sears.com/brand-tools/sbi-1020000',
]

brands_filter_urls = [
    # 'http://www.sears.com/shc/s/SolrxSeeAllFilters?keywordSearch=false&vName=For+the+Home&filterName=Brand&catalogId=12605&previousSort=ORIGINAL_SORT_ORDER&viewItems=25&toSAFPage=true&storeId=10153&sName=All+Decorative+Storage&cName=Decorative+Storage',

    'http://www.sears.com/shc/s/SolrxSeeAllFilters?vName=For+the+Home&filterName=Brand&toSAFPage=true&cName=Decorative+Storage&keywordSearch=false&catalogId=12605&previousSort=ORIGINAL_SORT_ORDER&subCatView=true&viewItems=25&storeId=10153&sName=View+All',
    'http://www.sears.com/shc/s/SolrxSeeAllFilters?vName=For+the+Home&filterName=Brand&toSAFPage=true&cName=Serveware&keywordSearch=false&catalogId=12605&previousSort=ORIGINAL_SORT_ORDER&subCatView=true&viewItems=25&storeId=10153&sName=View+All',
    'http://www.sears.com/shc/s/SolrxSeeAllFilters?vName=For+the+Home&filterName=Brand&toSAFPage=true&cName=Kitchen+Storage&keywordSearch=false&catalogId=12605&previousSort=ORIGINAL_SORT_ORDER&filter=storeOrigin%7CSears&subCatView=true&viewItems=25&storeId=10153&sName=View+All',
    'http://www.sears.com/shc/s/SolrxSeeAllFilters?vName=Pet+Supplies&filterName=Brand&toSAFPage=true&cName=Dog+Supplies&keywordSearch=false&catalogId=12605&previousSort=ORIGINAL_SORT_ORDER&subCatView=true&viewItems=25&storeId=10153&sName=View+All',
    'http://www.sears.com/shc/s/SolrxSeeAllFilters?vName=Outdoor+Living&filterName=Brand&toSAFPage=true&cName=Patio+Furniture&keywordSearch=false&catalogId=12605&previousSort=ORIGINAL_SORT_ORDER&filter=storeOrigin%7CSears&viewItems=50&storeId=10153&sName=View+All',
    'http://www.sears.com/shc/s/SolrxSeeAllFilters?vName=For+the+Home&filterName=Brand&catalogId=12605&previousSort=ORIGINAL_SORT_ORDER&viewItems=25&toSAFPage=true&storeId=10153&sName=Food+Storage&cName=Kitchen+Storage',
    'http://www.sears.com/shc/s/SolrxSeeAllFilters?vName=For+the+Home&filterName=Brand&catalogId=12605&previousSort=ORIGINAL_SORT_ORDER&viewItems=25&toSAFPage=true&storeId=10153&sName=Shelf+%26+Drawer+Organization&cName=Kitchen+Storage',
    'http://www.sears.com/shc/s/SolrxSeeAllFilters?vName=For+the+Home&filterName=Brand&catalogId=12605&previousSort=ORIGINAL_SORT_ORDER&viewItems=25&toSAFPage=true&storeId=10153&sName=Kitchen+Trash+Cans&cName=Kitchen+Storage',
    'http://www.sears.com/shc/s/SolrxSeeAllFilters?vName=For+the+Home&filterName=Brand&catalogId=12605&previousSort=ORIGINAL_SORT_ORDER&viewItems=25&toSAFPage=true&storeId=10153&sName=Kitchen+Shelving&cName=Kitchen+Storage',
    'http://www.sears.com/shc/s/SolrxSeeAllFilters?vName=For+the+Home&filterName=Brand&catalogId=12605&previousSort=ORIGINAL_SORT_ORDER&viewItems=25&toSAFPage=true&storeId=10153&sName=Condiment+Sets&cName=Serveware',
    'http://www.sears.com/shc/s/SolrxSeeAllFilters?vName=Lawn+%26+Garden&filterName=Brand&catalogId=12605&previousSort=ORIGINAL_SORT_ORDER&viewItems=50&toSAFPage=true&storeId=10153&sName=Wheelbarrows+%26+Garden+Carts&cName=Outdoor+Tools+%26+Supplies',
    'http://www.sears.com/shc/s/SolrxSeeAllFilters?vName=Lawn+%26+Garden&filterName=Brand&catalogId=12605&previousSort=ORIGINAL_SORT_ORDER&viewItems=50&toSAFPage=true&storeId=10153&sName=Composters&cName=Outdoor+Tools+%26+Supplies',
    'http://www.sears.com/shc/s/SolrxSeeAllFilters?vName=Lawn+%26+Garden&filterName=Brand&catalogId=12605&previousSort=ORIGINAL_SORT_ORDER&viewItems=50&toSAFPage=true&storeId=10153&sName=Sprayers&cName=Outdoor+Tools+%26+Supplies',
    'http://www.sears.com/shc/s/SolrxSeeAllFilters?vName=Lawn+%26+Garden&filterName=Brand&catalogId=12605&previousSort=ORIGINAL_SORT_ORDER&viewItems=50&toSAFPage=true&storeId=10153&sName=Spreaders&cName=Outdoor+Tools+%26+Supplies',
    'http://www.sears.com/shc/s/SolrxSeeAllFilters?vName=Lawn+%26+Garden&filterName=Brand&catalogId=12605&previousSort=ORIGINAL_SORT_ORDER&viewItems=50&toSAFPage=true&storeId=10153&sName=Edging+%26+Landscaping+Materials&cName=Outdoor+Tools+%26+Supplies',
    'http://www.sears.com/shc/s/SolrxSeeAllFilters?vName=Lawn+%26+Garden&filterName=Brand&catalogId=12605&previousSort=ORIGINAL_SORT_ORDER&viewItems=50&toSAFPage=true&storeId=10153&sName=Planters&cName=Outdoor+Tools+%26+Supplies',
    'http://www.sears.com/shc/s/SolrxSeeAllFilters?vName=Lawn+%26+Garden&filterName=Brand&catalogId=12605&previousSort=ORIGINAL_SORT_ORDER&viewItems=50&toSAFPage=true&storeId=10153&sName=Rain+Barrels&cName=Watering%2C+Hoses+%26+Sprinklers',
    'http://www.sears.com/shc/s/SolrxSeeAllFilters?vName=Lawn+%26+Garden&filterName=Brand&catalogId=12605&previousSort=ORIGINAL_SORT_ORDER&viewItems=50&toSAFPage=true&storeId=10153&sName=Fertilizers+%26+Chemicals&cName=Outdoor+Tools+%26+Supplies',
    'http://www.sears.com/shc/s/SolrxSeeAllFilters?vName=Lawn+%26+Garden&filterName=Brand&catalogId=12605&previousSort=ORIGINAL_SORT_ORDER&viewItems=50&toSAFPage=true&storeId=10153&sName=Miscellaneous+Supplies&cName=Outdoor+Tools+%26+Supplies',
    'http://www.sears.com/shc/s/SolrxSeeAllFilters?keywordSearch=false&vName=Lawn+%26+Garden&filterName=Brand&catalogId=12605&previousSort=ORIGINAL_SORT_ORDER&viewItems=50&toSAFPage=true&storeId=10153&sName=Hand+Gardening+Tools&cName=Outdoor+Tools+%26+Supplies',
    'http://www.sears.com/shc/s/SolrxSeeAllFilters?keywordSearch=false&filterName=Brand&catalogId=12605&previousSort=ORIGINAL_SORT_ORDER&viewItems=50&toSAFPage=true&storeId=10153&levels=Appliances_Freezers+%26+Ice+Makers_Chest',
    'http://www.sears.com/shc/s/SolrxSeeAllFilters?keywordSearch=false&filterName=Brand&catalogId=12605&previousSort=ORIGINAL_SORT_ORDER&viewItems=50&toSAFPage=true&storeId=10153&levels=For+the+Home_Kitchen+Storage',
    'http://www.sears.com/shc/s/SolrxSeeAllFilters?keywordSearch=false&filterName=Brand&catalogId=12605&previousSort=ORIGINAL_SORT_ORDER&viewItems=50&toSAFPage=true&storeId=10153&levels=For+the+Home_Serveware',
    'http://www.sears.com/shc/s/SolrxSeeAllFilters?keywordSearch=false&filterName=Brand&catalogId=12605&previousSort=ORIGINAL_SORT_ORDER&viewItems=50&toSAFPage=true&storeId=10153&levels=Gifts_Giftable+Items',

    'http://www.sears.com/shc/s/SolrxSeeAllFilters?filterName=Brand&catalogId=12605&previousSort=ORIGINAL_SORT_ORDER&viewItems=50&toSAFPage=true&storeId=10153&levels=For+the+Home_Decorative+Storage_View+All',
    'http://www.sears.com/shc/s/SolrxSeeAllFilters?filterName=Brand&catalogId=12605&previousSort=ORIGINAL_SORT_ORDER&viewItems=50&toSAFPage=true&storeId=10153&levels=For+the+Home_Decorative+Storage',
    'http://www.sears.com/shc/s/SolrxSeeAllFilters?filterName=Brand&catalogId=12605&previousSort=ORIGINAL_SORT_ORDER&viewItems=50&toSAFPage=true&storeId=10153&levels=For+the+Home_Serveware',
    'http://www.sears.com/shc/s/SolrxSeeAllFilters?filterName=Brand&catalogId=12605&previousSort=ORIGINAL_SORT_ORDER&viewItems=50&toSAFPage=true&storeId=10153&levels=For+the+Home_Kitchen+Storage',
    'http://www.sears.com/shc/s/SolrxSeeAllFilters?filterName=Brand&catalogId=12605&previousSort=ORIGINAL_SORT_ORDER&viewItems=50&toSAFPage=true&storeId=10153&levels=Pet+Supplies_Dog+Supplies',
    'http://www.sears.com/shc/s/SolrxSeeAllFilters?filterName=Brand&catalogId=12605&previousSort=ORIGINAL_SORT_ORDER&viewItems=50&toSAFPage=true&storeId=10153&levels=Outdoor+Living_Patio+Furniture',
    'http://www.sears.com/shc/s/SolrxSeeAllFilters?filterName=Brand&catalogId=12605&previousSort=ORIGINAL_SORT_ORDER&viewItems=50&toSAFPage=true&storeId=10153&levels=For+the+Home_Kitchen+Storage_Food+Storage',
    'http://www.sears.com/shc/s/SolrxSeeAllFilters?filterName=Brand&catalogId=12605&previousSort=ORIGINAL_SORT_ORDER&viewItems=50&toSAFPage=true&storeId=10153&levels=For+the+Home_Kitchen+Storage_Shelf+%26+Drawer+Organization',
    'http://www.sears.com/shc/s/SolrxSeeAllFilters?filterName=Brand&catalogId=12605&previousSort=ORIGINAL_SORT_ORDER&viewItems=50&toSAFPage=true&storeId=10153&levels=For+the+Home_Kitchen+Storage_Kitchen+Trash+Cans',
    'http://www.sears.com/shc/s/SolrxSeeAllFilters?filterName=Brand&catalogId=12605&previousSort=ORIGINAL_SORT_ORDER&viewItems=50&toSAFPage=true&storeId=10153&levels=For+the+Home_Kitchen+Storage_Kitchen+Shelving',
    'http://www.sears.com/shc/s/SolrxSeeAllFilters?filterName=Brand&catalogId=12605&previousSort=ORIGINAL_SORT_ORDER&viewItems=50&toSAFPage=true&storeId=10153&levels=For+the+Home_Serveware_Condiment+Sets',
    'http://www.sears.com/shc/s/SolrxSeeAllFilters?filterName=Brand&catalogId=12605&previousSort=ORIGINAL_SORT_ORDER&viewItems=50&toSAFPage=true&storeId=10153&levels=Lawn+%26+Garden_Outdoor+Tools+%26+Supplies_Wheelbarrows+%26+Garden+Carts',
    'http://www.sears.com/shc/s/SolrxSeeAllFilters?filterName=Brand&catalogId=12605&previousSort=ORIGINAL_SORT_ORDER&viewItems=50&toSAFPage=true&storeId=10153&levels=Lawn+%26+Garden_Outdoor+Tools+%26+Supplies_Composters',
    'http://www.sears.com/shc/s/SolrxSeeAllFilters?filterName=Brand&catalogId=12605&previousSort=ORIGINAL_SORT_ORDER&viewItems=50&toSAFPage=true&storeId=10153&levels=Lawn+%26+Garden_Outdoor+Tools+%26+Supplies_Sprayers',
    'http://www.sears.com/shc/s/SolrxSeeAllFilters?filterName=Brand&catalogId=12605&previousSort=ORIGINAL_SORT_ORDER&viewItems=50&toSAFPage=true&storeId=10153&levels=Lawn+%26+Garden_Outdoor+Tools+%26+Supplies_Spreaders',
    'http://www.sears.com/shc/s/SolrxSeeAllFilters?filterName=Brand&catalogId=12605&previousSort=ORIGINAL_SORT_ORDER&viewItems=50&toSAFPage=true&storeId=10153&levels=Lawn+%26+Garden_Outdoor+Tools+%26+Supplies_Edging+%26+Landscaping+Materials',
    'http://www.sears.com/shc/s/SolrxSeeAllFilters?filterName=Brand&catalogId=12605&previousSort=ORIGINAL_SORT_ORDER&viewItems=50&toSAFPage=true&storeId=10153&levels=Lawn+%26+Garden_Outdoor+Tools+%26+Supplies_Planters',
    'http://www.sears.com/shc/s/SolrxSeeAllFilters?filterName=Brand&catalogId=12605&previousSort=ORIGINAL_SORT_ORDER&viewItems=50&toSAFPage=true&storeId=10153&levels=Lawn+%26+Garden_Watering%2C+Hoses+%26+Sprinklers_Rain+Barrels',
    'http://www.sears.com/shc/s/SolrxSeeAllFilters?filterName=Brand&catalogId=12605&previousSort=ORIGINAL_SORT_ORDER&viewItems=50&toSAFPage=true&storeId=10153&levels=Lawn+%26+Garden_Outdoor+Tools+%26+Supplies_Fertilizers+%26+Chemicals',
    'http://www.sears.com/shc/s/SolrxSeeAllFilters?filterName=Brand&catalogId=12605&previousSort=ORIGINAL_SORT_ORDER&viewItems=50&toSAFPage=true&storeId=10153&levels=Lawn+%26+Garden_Outdoor+Tools+%26+Supplies_Miscellaneous+Supplies',
    'http://www.sears.com/shc/s/SolrxSeeAllFilters?filterName=Brand&catalogId=12605&previousSort=ORIGINAL_SORT_ORDER&viewItems=50&toSAFPage=true&storeId=10153&levels=Lawn+%26+Garden_Outdoor+Tools+%26+Supplies_Hand+Gardening+Tools',
    'http://www.sears.com/shc/s/SolrxSeeAllFilters?filterName=Brand&catalogId=12605&previousSort=ORIGINAL_SORT_ORDER&viewItems=50&toSAFPage=true&storeId=10153&levels=Appliances_Freezers+%26+Ice+Makers_Chest',
    'http://www.sears.com/shc/s/SolrxSeeAllFilters?filterName=Brand&catalogId=12605&previousSort=ORIGINAL_SORT_ORDER&viewItems=50&toSAFPage=true&storeId=10153&levels=For+the+Home_Kitchen+Storage',
    'http://www.sears.com/shc/s/SolrxSeeAllFilters?filterName=Brand&catalogId=12605&previousSort=ORIGINAL_SORT_ORDER&viewItems=50&toSAFPage=true&storeId=10153&levels=For+the+Home_Serveware',
    'http://www.sears.com/shc/s/SolrxSeeAllFilters?filterName=Brand&catalogId=12605&previousSort=ORIGINAL_SORT_ORDER&viewItems=50&toSAFPage=true&storeId=10153&levels=Gifts_Giftable+Items'
]

subcategories_to_parse_brands_urls = [
    'http://www.sears.com/for-the-home-laundry-utility-storage/c-1232256273',
    'http://www.sears.com/for-the-home-food-prep-gadgets/c-1223045618',
    'http://www.sears.com/lawn-garden-sheds-outdoor-storage/c-1020209',
    'http://www.sears.com/office-products-office-supplies/c-1231471845',
    'http://www.sears.com/office-products-office-furniture-storage/c-1231471833',
    'http://www.sears.com/tools-home-hardware-vents/c-1221020474',
    'http://www.sears.com/tools-garage-organization-shelving/c-1022330',
    'http://www.sears.com/tools-kitchen/c-1029678',
    'http://www.sears.com/tools-home-hardware-vents/c-1221020474',
    'http://www.sears.com/tools-hand-tools/c-1020136',
    'http://www.sears.com/for-the-home-kitchen-utility-hardware/c-1223818912',
    'http://www.sears.com/for-the-home-tableware/c-1020053',
    'http://www.sears.com/furniture-mattresses-game-room-bar-furniture/c-1219225302',
    'http://www.sears.com/furniture-mattresses-dining-room-kitchen-furniture/c-1219225301',
    'http://www.sears.com/toys-games-pretend-play-dress-up/c-1020120',
    'http://www.sears.com/toys-games-outdoor-play/c-1020118',
    'http://www.sears.com/toys-games-ride-on-toys-safety/c-1020122',
    'http://www.sears.com/automotive-outdoor-shelter/c-1023619',
    'http://www.sears.com/fitness-sports-camping-hiking/c-1020249',
    'http://www.sears.com/appliances-freezers-ice-makers/c-1020019',
    'http://www.sears.com/tools-hand-tools/c-1020136',
    'http://www.sears.com/for-the-home-kitchen-storage-food-storage/b-1223580305',
    'http://www.sears.com/lawn-garden-sheds-outdoor-storage/c-1020209',
    'http://www.sears.com/lawn-garden-outdoor-tools-supplies/c-1024017',
    'http://www.sears.com/office-products-office-supplies/c-1231471845',
    'http://www.sears.com/lawn-garden-outdoor-tools-supplies/c-1024017',
    'http://www.sears.com/fitness-sports-camping-hiking/c-1020249',
    'http://www.sears.com/for-the-home-food-prep-gadgets/c-1223045618',
    'http://www.sears.com/sports-fan-shop-tailgating-outdoor/c-1036977',
    'http://www.sears.com/for-the-home-closet-storage/c-1232256270',
    'http://www.sears.com/for-the-home-kitchen-storage/c-1024440',
    'http://www.sears.com/food-grocery-cleaning-supplies/c-1030490',
    'http://www.sears.com/for-the-home-candles-home-fragrance/b-1223045427',
    'http://www.sears.com/office-products-office-furniture-storage/b-1231470618',
    'http://www.sears.com/for-the-home-kitchen-utility-hardware/b-1223818912'
]

products_to_parse = [
    'http://www.sears.com/for-the-home-kitchen-storage/b-1600000181',
    'http://www.sears.com/lawn-garden-outdoor-tools-supplies-composters/b-1035945'
]

categories_to_parse_brands_urls = [
    'http://www.sears.com/for-the-home/v-1020007',
]

search_url = 'http://www.sears.com/search=%(brand)s&%(brand)s?filter=Brand&keywordSearch=false&catalogId=12605&previousSort=ORIGINAL_SORT_ORDER&viewItems=50&storeId=10153'


class SearsComSpider(BaseSpider):
    name = 'sears.com'
    allowed_domains = ['sears.com']

    start_urls = (
        'http://sears.com',
    )

    _product_urls = []
    _product_ids = []

    def parse(self, request):
        for brand in brands:
            yield Request(search_url % {'brand': urllib.quote(brand)},
                          meta={'brand': brand}, callback=self.parse_product_list)

        # straight-forward search does not return all product of particular brand;
        # because of that we had to load products from some particular categories;
        # these categories have 'Search by Brand' link;
        # all 'brands' links are stored in brands_list_urls
        for brands_list_url in brands_list_urls:
            yield Request(brands_list_url, callback=self.parse_brands_list)

        # some of the brands lists from specific sub-categories
        for brands_filter_url in brands_filter_urls:
            yield Request(brands_filter_url, callback=self.parse_brands_filter)

        for url in categories_to_parse_brands_urls:
            yield Request(url, callback=self.parse_category)

        # some of categories
        for url in subcategories_to_parse_brands_urls:
            yield Request(url, callback=self.parse_subcategory)

        for url in products_to_parse:
            yield Request(url, callback=self.parse_product_list_full)
            yield Request(url, callback=self.parse_product_list_for_brands)

            # this XPath gets 'Shop by Brand' link for category page (in case it will be needed in future)
            # hxs.select("//div[@class='grid_col_1']//li[@class='parent'][strong[contains(text(),'Shop By Brand')]]/ul/li/a").extract()

    def parse_brands_list(self, response):
        hxs = HtmlXPathSelector(response)
        for brand in brands:
            for url in hxs.select("//dl[@class='brand_list']/dt/a[text()='%s']/@href" % brand).extract():
                url = urljoin_rfc(get_base_url(response), url)
                yield Request(url,
                              meta={'brand': brand}, callback=self.parse_brands_result)

    def parse_brands_filter(self, response):
        logging.error('Parsing brands list')
        hxs = HtmlXPathSelector(response)
        for brand in brands:
            logging.error("Brand: %s" % brand)
            logging.error("XPath: %s" % "//div[@id='filterOpt']/ul/li/a[span[contains(text(), '%s')]]/@href" % brand)
            urls = hxs.select("//div[@id='filterOpt']/ul/li/a[span[contains(text(), '%s')]]/@href" % brand).extract()
            urls += hxs.select(
                "//div[@id='filterOpt']/ul/li/a[span[contains(text(), '%s')]]/@href" % brand.upper()).extract()
            urls += hxs.select("//ul[@id='BrandOption']/li/a[contains(text(), '%s')]/@href" % brand).extract()
            for url in urls:
                url = urljoin_rfc(get_base_url(response), url)
                logging.error("Found url: %s" % url)
                yield Request(url,
                              meta={'brand': brand}, callback=self.parse_product_list)

    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)

        for url in hxs.select('//div[@class="shcCatNavItem"]//h3/a/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_subcategory)

    def parse_subcategory(self, response):
        hxs = HtmlXPathSelector(response)

        categories = [url for url in \
                      hxs.select('//div[@itemprop="significantLinks" and '
                                 'contains(@id, "FeaturedSubCats")]/ul//a/@href')
                      .extract() if url]
        categories += hxs.select("//dl[@id='categories_menu']/dd/a/@href").extract()
        categories += hxs.select("//dl[@id='categories_menu']/dd/h2/a/@href").extract()

        for url in categories:
            url = urljoin_rfc(get_base_url(response), url)

            yield Request(url, callback=self.parse_product_list_for_brands)

            yield Request(url, callback=self.parse_product_list_full)

        for r in self.parse_product_list_for_brands(response):
            yield r

        for r in self.parse_product_list_full(response):
            yield r

    def parse_brands_result(self, response):
        hxs = HtmlXPathSelector(response)

        links = hxs.select(u'//h4[@itemprop="name"]/a/@href').extract()
        for url in links:
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, meta=response.meta, callback=self.parse_product)

        links2 = hxs.select(u'//h4/a[@itemprop="name"]/@href').extract()
        for url in links2:
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, meta=response.meta, callback=self.parse_product)

        links3 = hxs.select(u'//h2[@itemprop="name"]/a/@href').extract()
        for url in links3:
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, meta=response.meta, callback=self.parse_product)

        categories = hxs.select("//dl[@id='categories_menu']/dd[position()<last()]/a/@href").extract()
        for url in categories:
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, meta=response.meta, callback=self.parse_brands_result)

        categories2 = hxs.select('//div[contains(@class, "item")]/h4/a/@href').extract()
        for url in categories2:
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, meta=response.meta, callback=self.parse_brands_result)

        if not categories and not categories2 and not links and not links2 and not links3:
            # single product page
            self.parse_product(response)

    def parse_product_list_for_brands(self, response):
        hxs = HtmlXPathSelector(response)

        brands_url = hxs.select('//ul[@id="BrandOption"]/div/a/@href').extract()
        if brands_url:
            url = urljoin_rfc(get_base_url(response), brands_url[0])
            logging.error("Brands url:")
            logging.error(url)
            yield Request(url, callback=self.parse_brands_filter)

        brand_filters = zip([b.strip().lower() for b in hxs.select('//ul[@id="BrandOption"]/li/a/text()').extract()],
                            hxs.select('//ul[@id="BrandOption"]/li/a/@href').extract())
        if brand_filters:
            for brand in brands:
                for brand_filter, url in brand_filters:
                    if brand.lower() in brand_filter:
                        url = urljoin_rfc(get_base_url(response), url)
                        yield Request(url,
                                      meta={'brand': brand},
                                      callback=self.parse_product_list)

    def parse_product_list(self, response):
        hxs = HtmlXPathSelector(response)

        links = hxs.select(u'//h2[@itemprop="name"]/a/@href').extract()
        for url in links:
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, meta=response.meta, callback=self.parse_product)

        next_url = hxs.select(u'//p[@id="nextPageResults"]/a/@href').extract()
        if next_url:
            url = urljoin_rfc(get_base_url(response), next_url[0])
            yield Request(url, meta=response.meta, callback=self.parse_product_list)

    def parse_product_list_full(self, response):
        hxs = HtmlXPathSelector(response)

        links = zip(hxs.select(u'//h2[@itemprop="name"]/a/text()').extract(),
                    hxs.select(u'//h2[@itemprop="name"]/a/@href').extract())

        brands_ = [b.lower() for b in brands]

        for name, url in links:
            possible_brand = name.split()[0].lower()
            if possible_brand in brands_:
                meta = response.meta.copy()
                meta['brand'] = possible_brand
                url = urljoin_rfc(get_base_url(response), url)
                yield Request(url, meta=meta, callback=self.parse_product)

        next_url = hxs.select(u'//p[@id="nextPageResults"]/a/@href').extract()
        if next_url:
            url = urljoin_rfc(get_base_url(response), next_url[0])
            yield Request(url, meta=response.meta, callback=self.parse_product_list)

    def parse_product(self, response):
        url_exists = True
        product_url = response.url.split('?')[0]
        if product_url not in self._product_urls:
            self._product_urls.append(product_url)
            url_exists = False

        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        try:
            seller_name = hxs.select('//p[@class="ffmentStoreName"]/text()').extract()
            if seller_name:
                seller_name = ' '.join(seller_name[0].split())
            if not seller_name:
                seller_name = hxs.select('//span[@id="vendorName2"]/a[@class="merchantNameLink"]/text()').extract()
                if seller_name:
                    seller_name = seller_name[0].strip()

            identifier = hxs.select('//*[@itemprop="productID"]/text()').extract()[0].strip()
            identifier = re.search(r'^(.*) ', identifier).groups()[0]
            if identifier in self._product_ids:
                if url_exists:
                    return
            else:
                self._product_ids.append(identifier)
            product_loader = ProductLoader(item=Product(), response=response)
            name = hxs.select(u'//h1/text()').extract()[0]
            name = ' '.join(name.split())
            product_loader.add_value('name', name)
            product_loader.add_value('dealer', seller_name)
            sku = hxs.select(u'//span[@itemprop="model"]/text()').extract()
            if not sku:
                sku = hxs.select(u'//input[@id="SinNumberforGH"]/@value').extract()
            product_loader.add_value('sku', sku[0])
            product_loader.add_value('identifier', identifier + '-' + seller_name)
            price = hxs.select(u'//span[@itemprop="price"]/text()').extract()
            if not price:
                price = hxs.select(u'//span[@class="regPrice"]/text()').extract()
            if not price:
                product_loader.add_value('price', '')
            else:
                product_loader.add_value('price', price[0])

            product_loader.add_value('url', response.url)
            brand = response.meta['brand'].strip().lower()
            product_loader.add_value('brand', brand)

            product = product_loader.load_item()
        except:
            if '?prdNo=' in base_url and not 'PDP_REDIRECT=false' in base_url:
                yield Request(base_url + '&PDP_REDIRECT=false',
                              meta=response.meta,
                              callback=self.parse_product)
        else:
            sellers = hxs.select('//div[@id="alsoAvailable"]/table[@id="vendorList"]/tbody/tr')
            if sellers:
                total_sellers = len(sellers)
                for seller in sellers:
                    price = seller.select('td/div[@itemprop="price"]/span/text()').extract()
                    if not price:
                        price = seller.select('td/table/tbody/tr/td[@class="vendorListPrice"]/text()').extract()
                    shipping = seller.select('td/table/tbody/tr/td/div/ul/li/span[@class="priceship"]/text()').extract()
                    shipping = shipping[0] if shipping else 0
                    try:
                        seller_name = seller.select('td/span[@id="vendorListNameSpan"]/a/strong/text()').extract()
                        if not seller_name:
                            seller_name = seller.select('td/span[@id="vendorName"]/a/text()').extract()
                        seller_name = seller_name[0].strip()
                    except:
                        sold_by_sears = seller.select('.//td[@id="product"]/text()').re(r'Sold By Sears')
                        if sold_by_sears:
                            seller_name = 'Sears'
                        else:
                            continue
                    '''
                    try:
                        identifier = seller.select('.//td[@class="vendorListCartButton"]//input/@info').extract()[0].split('^')[0]
                    except:
                        self.errors.append('WARNING: identifier error => %s' % response.url)
                        continue
                    '''
                    l = ProductLoader(item=Product(), response=response)
                    l.add_value('identifier', identifier + '-' + seller_name)
                    l.add_value('name', name)
                    l.add_value('brand', brand)
                    if sku:
                        l.add_value('sku', sku)
                    l.add_value('url', response.url)
                    l.add_value('price', price)
                    l.add_value('shipping_cost', shipping)
                    #l.add_value('image_url', image_url)
                    l.add_value('dealer', 'Sears - ' + seller_name if seller_name else '')
                    #if l.get_output_value('identifier') not in self.ids:
                    #    self.ids.append(l.get_output_value('identifier'))
                    product = l.load_item()

                    metadata = KeterMeta()
                    metadata['brand'] = response.meta['brand']
                    metadata['reviews'] = []
                    product['metadata'] = metadata
                    response.meta['product'] = product

                    n_reviews = hxs.select(u'//input[@id="total_pageCount"]/@value').extract()
                    if n_reviews:
                        n_reviews = int(n_reviews[0])
                        response.meta['partnumber'] = hxs.select(u'//input[@id="partnumber"]/@value').extract()[0]
                    else:
                        n_reviews = 0

                    response.meta['review_pages'] = n_reviews
                    response.meta['review_n'] = 1

                    for x in self.parse_review(response):
                        yield x
            else:
                metadata = KeterMeta()
                metadata['brand'] = response.meta['brand']
                metadata['reviews'] = []
                product['metadata'] = metadata
                response.meta['product'] = product

                n_reviews = hxs.select(u'//input[@id="total_pageCount"]/@value').extract()
                if n_reviews:
                    n_reviews = int(n_reviews[0])
                    response.meta['partnumber'] = hxs.select(u'//input[@id="partnumber"]/@value').extract()[0]
                else:
                    n_reviews = 0

                response.meta['review_pages'] = n_reviews
                response.meta['review_n'] = 1

                for x in self.parse_review(response):
                    yield x

    def parse_review(self, response):
        hxs = HtmlXPathSelector(response)
        product = response.meta['product']

        for r in hxs.select(u'//div[@class="previewContents"]'):
            loader = ReviewLoader(item=Review(), selector=r, date_format='%b %d , %Y')

            title = r.select(u'.//span[contains(@class,"pReviewHeadlineText")]/text()').extract()
            text = r.select(u'.//div[contains(@class,"pReviewThoughts")]//text()').extract()
            text = [t for t in text if '...' not in t]
            text = ''.join(text)
            if title:
                text = title[0].strip() + '\n' + text.strip()

            loader.add_value('full_text', text.strip())
            loader.add_xpath('date', u'.//div[@class="pReviewDate"]/text()[1]')
            rclass = r.select(u'.//div[contains(@class,"readStarsContainer")]/@class').extract()[0]
            rating = None
            for rclass in rclass.split():
                if rclass.startswith('star_'):
                    rating = rclass[5]
            loader.add_value('rating', rating)
            loader.add_value('url', response.url)
            product['metadata']['reviews'].append(loader.load_item())

        if response.meta['review_n'] >= response.meta['review_pages']:
            yield product
        else:
            response.meta['review_n'] += 1
            url = 'http://www.sears.com/shc/s/RatingsAndReviewsCmd?originSite=sears.com&targetId=%s&targetType=product&offset=%d&pagination=true&storeId=10153&callType=AJAX&methodType=GET' % (
                response.meta['partnumber'], response.meta['review_n'])
            yield Request(url, meta=response.meta, callback=self.parse_review)
