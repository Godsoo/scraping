import re

# scrapy includes
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

# spider includes
from product_spiders.items import Product, ProductLoader


# main class
class AeromaxSpider(BaseSpider):

    # setup
    name = "aeromax-pistoletpeinture.com" # Name must match the domain
    allowed_domains = ["aeromax-pistoletpeinture.com"]
    start_urls = ["http://www.aeromax-pistoletpeinture.com/advanced_search_result.php?keywords=+&x=119&y=28&categories_id=&inc_subcat=1&manufacturers_id=&pfrom=&pto=&dfrom=&dto=",]

    # main request
    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        # yield Request('http://www.aeromax-pistoletpeinture.com/sitemap.xml', callback=self.parse_sitemap)
        # items can be crawled using the sitemap, but most of the product pages are unavailable

        # get subcategories
        cat1urls = hxs.select('//div[@class="dropmenudiv_b"]/a/@href').extract()

        # iterate subcategories
        for cat1url in cat1urls:
            yield Request(urljoin_rfc(base_url, cat1url))

        cat2urls = hxs.select('//div[@class="infoBoxContents_categCell category_level_1"]/a/@href').extract()
        for cat2url in cat2urls:
            yield Request(urljoin_rfc(base_url, cat2url))

        # crawl next page
        onglet = hxs.select('//a[@title=" Page suivante "]/@href').extract()
        if onglet:
            # it always contains two and the "next" is always the second one
            nextpage = onglet[-1]  # onglet[1].select("./a/@href")

            # if there is a next page...
            if nextpage:
                yield Request(urljoin_rfc(base_url, nextpage), priority=10)

        # iterate products
        for product in self.parse_products(hxs, base_url):
            yield product

    def parse_sitemap(self, response):
        for url in re.findall('loc>(.*/product_info\.html)</loc', response.body):
            yield Request(url, callback=self.parse_product, meta={'dont_merge_cookies': True})

    # gather products
    def parse_products(self, hxs, base_url):
        products = hxs.select('//table[@class="productListing"]//tr')[1:]

        for product in products:
            product_loader = ProductLoader(Product(), product)

            # extract values
            urlAndNameNode = product.select('.//td[@class="productListing-data" and not(@align)]/a[text()]')
            name = urlAndNameNode.select('text()').extract()[0]
            url = urlAndNameNode.select("@href").extract()[0]
            price = product.select(
                './td[@class="productListing-data" and @align="right"]/span[@class="productSpecialPrice"]/text()'
            ).extract()
            if not price:
                price = product.select('./td[@class="productListing-data" and @align="right"]/text()').extract()
            price = price[0]
 
            image_url = product.select(
                './td[@class="productListing-data" and @align="center"]/a/img[@border="0" and @width="150"]/@src'
            ).extract()
            image_url = image_url[0] if image_url else ''

            identifier = product.select(
                './/td[@class="productListing-data" and @align="center"]/a[img[contains(@alt,"Acheter")]]/@href'
            ).re('products_id=(\d+)&?')

            # add values
            '''
            product_loader.add_value('name', name)
            product_loader.add_value('url', urljoin_rfc(base_url, url))
            product_loader.add_value('price', price)
            
            yield product_loader.load_item()
            '''
            yield Request(
                urljoin_rfc(base_url, url),
                callback=self.parse_category,
                meta={
                  'name': name,
                  'price': price,
                  'image_url': image_url,
                  'identifier': identifier[0] if identifier else None
                },
                priority=10
            )

    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)
        meta = response.meta
        category = hxs.select(u'//td[@class="main" and contains(text(), "cat\xe9gorie")]/a/text()').extract()
        l = ProductLoader(item=Product(), response=response)
        l.add_value('identifier', meta.get('identifier'))
        l.add_value('name', meta.get('name'))
        l.add_value('category', category)
        l.add_value('url', response.url)
        l.add_value('price', meta.get('price'))
        l.add_value('image_url', meta.get('image_url'))
        l.add_value('stock', 1)
        yield l.load_item()

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        meta = response.meta
        identifier = meta.get('identifier', None)
        if not identifier:
            identifier = re.search('/p(\d+)/', response.url).group(1)
        category = hxs.select(u'//td[@class="main" and contains(text(), "cat\xe9gorie")]/a/text()').extract()
        name = hxs.select('//td[@class="infoBoxContents1"]/h1/text()').extract()
        price = hxs.select('//td[@class="infoBoxContents1"]/span[@class="productSpecialPrice"]/text()').extract()
        if not price:
            price = hxs.select('//td[@class="infoBoxContents1" and @align="right"]/text()').extract()
        image_url = re.search('document\[\'product\d+\'\]\.src = \'(.*)\'', response.body)
        image_url = image_url.group(1) if image_url else None

        l = ProductLoader(item=Product(), response=response)
        l.add_value('identifier', identifier)
        l.add_value('name', name)
        l.add_value('category', category)
        l.add_value('url', response.url)
        l.add_value('price', price)
        l.add_value('image_url', image_url)
        l.add_value('stock', 1)
        yield l.load_item()   
