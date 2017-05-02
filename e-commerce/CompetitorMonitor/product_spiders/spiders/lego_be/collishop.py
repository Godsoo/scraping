from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price_eu as extract_price
from scrapy.http import Request
import re
import json


class CollishopBeSpider(BaseSpider):
    name = 'lego_be-collishop.be'
    allowed_domains = ['collishop.be']
    start_urls = ('http://www.collishop.be/e/nl/cs/home',)

    def parse(self, response):
        yield Request('https://www.collishop.be/e/SearchDisplay?categoryId=&storeId=12501&catalogId=10001&langId=-11&sType=SimpleSearch&resultCatEntryType=2&showResultsPage=true&searchSource=Q&pageView=&beginIndex=0&pageSize=9999&searchTerm=lego#facet:&productBeginIndex:0&orderBy:&pageView:grid&minPrice:&maxPrice:&pageSize:&',
                      callback=self.parse2)
        # yield Request('http://www.collishop.be/e/nl/cs/CategoryResultsProductTilesView?paginationCounter=2&scrollableEmsName=&catalogId=10001&categoryId=&storeId=12501&langId=-11&containerName=SRCH&frameName=PRODUCTS&nodesPerPage=9999&pagesPerFetch=1&nodesPerFetch=9999&jspName=%2FSnippets%2FCatalog%2FCategoryDisplay%2FCategoryOnlySearchResultsProductTiles.jsp&viewName=CategoryResultsProductTilesView&biDirectional=false&flushAlways=false&viewAllFlag=&productTileType=2&widgetPaginationType=2&totalPages=8.0&totalDivs=8.0&itempropValue=&orderBy=&searchTermScope=&searchType=&filterTerm=&maxPrice=&showResultsPage=true&sType=SimpleSearch&metaData=&manufacturer=&resultCatEntryType=2&tileView=&searchTerm=lego&facet=&filterFacet=&originalSearchTerm=&sortValue=&beginIndex=0&divNo=2&pageCount=2&fromPagination=true',
        #               callback=self.parse2)

    def parse2(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        urls = hxs.select('//div[@class="product_name"]/a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        identifier = hxs.select('//span[@itemprop="SKU"]/text()').extract()
        if not identifier:
            urls = hxs.select('//*[@id="skuDisplayUrls"]/@value').extract()
            if not urls:
                return
            else:
                urls = json.loads(urls[0])
                for url in urls.itervalues():
                    yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)
                return

        product_loader = ProductLoader(item=Product(), selector=hxs)
        product_loader.add_value('identifier', identifier)
        name = hxs.select('//h1[@itemprop="name"]/text()').extract()[0]
        product_loader.add_value('name', name)

        sku = ''
        for match in re.finditer(r"([\d,\.]+)", name):
            if len(match.group()) > len(sku):
                sku = match.group()
        product_loader.add_value('sku', sku)

        image_url = hxs.select('//*[@id="productMainImage"]/@src').extract()
        if image_url:
            product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))

        price = hxs.select('//*[@id="productOffer"]/text()').extract()[0]
        price = extract_price(price)
        product_loader.add_value('price', price)

        product_loader.add_value('shipping_cost', 2.95)

        out_of_stock = hxs.select('//div[@class="stock unavailable"]').extract()
        if out_of_stock :
            product_loader.add_value('stock', 0)

        category = ''
        product_loader.add_value('category', category)
        product_loader.add_value('brand', 'Lego')

        product_loader.add_value('url', response.url)
        product = product_loader.load_item()
        yield product
