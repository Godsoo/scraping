import ast

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from scrapy.http.cookies import CookieJar

from scrapy import log

from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader


class BudgetGolfSpider(BaseSpider):
    name = "budgetgolf.com"
    allowed_domains = ["www.budgetgolf.com", ]
    start_urls = ["http://www.budgetgolf.com/"]

    # cookie_jar = 0
    ignore_urls = []

    download_delay = 0.1

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        # Dive in categories
        # cats = hxs.select("//ul[@id='top_menu']/li/a")[1:-1]
        cats = response.css('div.xm-sub-menu a')
        for cat in cats:
            # cat_name = cat.select(".//span/text()").extract()[0]
            cat_name = cat.select(".//text()").extract()[0]
            cat_url = cat.select(".//@href").extract()[0]
            yield Request(
                url=urljoin_rfc(base_url, cat_url),
                meta={"cat_name": cat_name},
                callback=self.parse_cat)

        # AJAX search shoes
        request = FormRequest(url='http://www.budgetgolf.com/shoes_search.php',
                              formdata={u'mode': u'get_products',
                                        u'objects_per_page': u'45',
                                        u'page': u'1'},
                              meta={'cat_name': 'Golf Footwear'},
                              callback=self.parse_cat)
        yield request

    def parse_cat(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        
        search_url = response.xpath('//script/text()').re_first('var refine_filters_server_search_script.*?"(.+)"')
        if search_url:
            yield Request(response.urljoin(search_url), 
                          self.parse_cat,
                          meta=response.meta)

        subcats = response.xpath('//div[@class="no_child_subcats_list"]//a/@href').extract()
        subcats += response.css('div.subcats_list a::attr(href)').extract()
        if subcats:
            for subcat in subcats:
                yield Request(
                    url=urljoin_rfc(base_url, subcat),
                    meta=response.meta,
                    callback=self.parse_cat)

                # AJAX?
                if (
                                    '-' in subcat and
                                    'http' not in subcat and
                                '?' not in subcat and
                            '=' not in subcat
                ):
                    url = urljoin_rfc(base_url,
                                      subcat.replace('-', '_')
                                      .replace('/', '') + '_search.php')

                    request = FormRequest(url=url,
                                          formdata={u'mode': u'get_products',
                                                    u'objects_per_page': u'45',
                                                    u'page': u'1'},
                                          meta=response.meta,
                                          callback=self.parse_cat)
                    yield request

        next_page = response.css('a.right-arrow::attr(href)').extract()

        if not next_page or (next_page and not next_page[0]):
            try:
                next_page = int(response.css('a.right-arrow::attr(onclick)').re(r"\('(\d+)'")[0])

                request = FormRequest(url=response.url,
                                      formdata={u'mode': u'get_products',
                                                u'objects_per_page': u'45',
                                                u'page': unicode(next_page)},
                                      meta=response.meta,
                                      callback=self.parse_cat,
                                      dont_filter=True)
                yield request
            except:
                pass
            else:
                next_page = None
        if next_page:

            url1 = urljoin_rfc(base_url, next_page[0])

            yield Request(
                url=url1,
                meta=response.meta,
                callback=self.parse_cat)

        products = response.css('div#pr_list a::attr(href)').extract()
        
        for product in products:
            # self.cookie_jar += 1
            meta = response.meta.copy()
            meta['dont_merge_cookies'] = True
            # meta['cookiejar'] = self.cookie_jar
            yield Request(
                url=urljoin_rfc(base_url, product),
                meta=meta,
                callback=self.parse_product)

    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        if 'cat_name' in response.meta:
            cat_name = response.meta["cat_name"]
        else:
            cat_name = response.meta['item']['category']


        # Fill up the Product model fields
        url = response.url
        name = response.css('div.pr_title::text').extract()
        price = response.xpath("//span[@class='price-value']/span"
                           "/span[@id='product_price']/text()").extract()
        if not price:
            price = hxs.select("//div[@class='pr_page_price']"
                               "/span[@class='map_price_value']/span/text()").extract()
        if not price:
            price = hxs.select("//div[@class='pr_page_price']"
                               "//span[@class='map_price_value']/span/text()").extract()
        if not price:
            price = hxs.select('//*[@id="product_price"]/text()').extract()
        if not price:
            price = response.meta.get('price')

        product_id = hxs.select('//input[@id="productid"]/@value').extract()
        if not product_id:
            self.log("ERROR product_id not found")
            return
        
        try:
            sku = hxs.select("//div[@class='creviews-rating']/text()"
            ).extract()[0].split(" ")[1]
        except:
            sku = hxs.select('//*[@id="product_code"]/text()').extract()[0]


        category = cat_name
        image_url = hxs.select("//div[@class='pr_img_holder']//img/@src"
        ).extract()
        if not image_url:
            image_url = hxs.select('//img[@id="product_thumbnail"]/@src').extract()
        brand = hxs.select(
            "//div[@class='location_bg_p2']/table/tr/td[3]/a/text()"
        ).extract()
        if brand == cat_name:
            brand = ''

        stock = response.xpath('//script/text()').re_first("'productStock': '(\d+)'")

        # l.add_value("identifier", product_id[0])

        variants = []
        variants_rel = {}
        variants_descs = {}

        p = response.xpath("//script[contains(text(),'var price')]").extract()
        if p:
            p = p[0].split("\n")

            for variant in p:
                if 'variant' in variant and 'new Image' in variant:
                    size_code = variant.split('variants[')[-1].split(']')[0]
                    variants.append({'code':size_code, 'details': ast.literal_eval(variant.split(' = ')[-1].split(';')[0].replace(',new Image()', ''))[0]})

            for variant in p:
                if '[1]' in variant:
                    variants_rel[variant.split('[')[1].split(']')[0]] = variant.split('=')[-1].split(';')[0].strip()

            for variant in p:
                if 'names[' in variant:
                    variants_descs[variant.split('[')[-1].split(']')[0]] = variant.split('= "')[-1].split('";')[0].strip()


            for product_variant in variants:
                l = ProductLoader(response=response, item=Product())
                #size_code = size_code.get(product_variant.get('code'))
                #size_desc = size_descs.get(size_code)
                l.add_value("identifier", product_id[0] + '-' + product_variant.get('code'))
                l.add_value('url', url)
                l.add_value('name', name[0] + ' ' +  variants_descs[variants_rel[product_variant['code']]])
                l.add_value('price', product_variant.get('details')[0])
                l.add_value('sku', product_variant.get('details')[-2])
                l.add_value('category', category)
                l.add_value('image_url', image_url)
                l.add_value('brand', brand)
                l.add_value('stock', product_variant.get('details')[1])
                if product_variant.get('details')[0] < 125:
                    shipping_cost = 7.99
                else:
                    shipping_cost = 0
                l.add_value('shipping_cost', shipping_cost)
                yield l.load_item()
        else:
            if price:
                l = ProductLoader(response=response, item=Product())
                l.add_value("identifier", product_id[0])
                l.add_value('url', url)
                l.add_value('name', name)
                l.add_value('price', price)
                l.add_value('sku', sku)
                # l.add_value('metadata', metadata)
                l.add_value('category', category)
                l.add_value('image_url', image_url)
                l.add_value('brand', brand)
                if stock:
                    l.add_value('stock', stock)

                if price < 125:
                    shipping_cost = 7.99
                else:
                    shipping_cost = 0
                l.add_value('shipping_cost', shipping_cost)
                yield l.load_item()

                # shipping_url = "http://www.budgetgolf.com/shipping_calculator.php"
                # # mode:shipping
                # # productid:36244
                # # s_country:US
                # # s_city:New York
                # # s_zipcode:10001
                # # s_state:NY
                #
                # request = FormRequest(url=shipping_url,
                #                       formdata={u'mode': u'shipping',
                #                                 u'productid': unicode(product_id[0]),
                #                                 u's_country': u'US',
                #                                 u's_city':u'New York',
                #                                 u's_zipcode':u'10001',
                #                                 u's_state':u'NY'
                #                                 },
                #                       meta={"loader": l},
                #                       callback=self.parse_shipping)
                # yield request
            elif url not in self.ignore_urls and product_id:
                meta = response.meta.copy()
                cookiejar = response.meta.setdefault('cookie_jar', CookieJar())
                cookiejar.extract_cookies(response, response.request)
                meta['url'] = url
                meta['dont_merge_cookies'] = True
                meta['cookie_jar'] = cookiejar

                req = FormRequest(url='http://www.budgetgolf.com/cart.php',
                                  formdata={'mode': 'add',
                                            'amount': '1',
                                            'productid': unicode(product_id[0])
                                            },
                                  callback=self.go_checkout,
                                  meta=meta,
                                  dont_filter=True)
                cookiejar.add_cookie_header(req)
                yield req

    def parse_shipping(self, response):

        hxs = HtmlXPathSelector(response)
        loader = response.meta['loader']

        shipping = hxs.select('(//body/div/span[@class="currency"])[position()=1]/text()').extract()
        if not shipping:
            self.log("ERROR shipping not found")
        else:
            loader.add_value("shipping_cost", shipping[0].strip())

        product = loader.load_item()

        yield product

    def go_checkout(self, response):
        meta = response.meta.copy()
        cookiejar = response.meta.setdefault('cookie_jar', CookieJar())
        cookiejar.extract_cookies(response, response.request)
        meta['dont_merge_cookies'] = True
        meta['cookie_jar'] = cookiejar
        req = Request(url='http://www.budgetgolf.com/cart.php?mode=checkout',
                      callback=self.parse_price,
                      meta=response.meta,
                      dont_filter=True)
        cookiejar.add_cookie_header(req)
        yield req

    def parse_price(self, response):
        hxs = HtmlXPathSelector(response)
        price = hxs.select('//tr[@id="cart-contents-box"]'
                           '//span[@class="currency"]/text()').extract()
        if price:
            self.ignore_urls.append(response.meta['url'])
            meta = response.meta.copy()
            meta['price'] = price[0]
            del(meta['cookie_jar'])
            yield Request(response.meta['url'],
                          callback=self.parse_product,
                          meta=meta,
                          dont_filter=True)

    # def got_to_checkout(self, response):
    #
    #     self.log("got_to_checkout " + response.url)
    #
    #     print str(response.meta)
    #     yield Request("http://www.budgetgolf.com/cart.php", dont_filter=True, callback=self.parse_basket_product, meta=response.meta)
    #
    # def parse_basket_product(self, response):
    #
    #     self.log("parse_basket_product " + response.url)
    #
    #     hxs = HtmlXPathSelector(response)
    #     name = hxs.select('//a[@class="product-cart-title"]/text()').extract()
    #     url = hxs.select('//a[@class="product-cart-title"]/@href').extract()
    #     price = hxs.select('//span[@class="price"]/span/text()').extract()
    #     if not response.meta.get('delete_product', False):
    #         log.msg("Product on the basket: " + name[0])
    #         l = ProductLoader(response=response, item=Product())
    #         l.add_value('url', url)
    #         l.add_value('name', name[0])
    #         l.add_value('price', price)
    #         l.add_value('sku', response.meta['sku'])
    #         l.add_value('category', response.meta['category'])
    #         l.add_value('image_url', response.meta['image_url'])
    #         l.add_value('brand', response.meta['brand'])
    #         # l.add_value('shipping_cost', shipping_cost)
    #         yield l.load_item()
    #         delete_url = hxs.select('//a[@class="simple-button simple-delete-button"]/@href').extract()
    #         yield Request(urljoin_rfc(get_base_url(response), delete_url[0]), dont_filter=True, callback=self.parse_basket_product, meta={"delete_product":True})
    #
