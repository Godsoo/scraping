import re
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from decimal import Decimal
from product_spiders.items \
import Product, ProductLoaderWithNameStrip as ProductLoader


class SpicebarnSpider(BaseSpider):
    name = 'spicebarn.com'
    allowed_domains = ['spicebarn.com', 'www.spicebarn.com' ]
    start_urls = ('http://www.spicebarn.com/',)
    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        xpath_str = '//table[@id="AutoNumber13"]//a'
        category_links = hxs.select(xpath_str)

        for category_link in category_links[1:14]:
            category = re.sub('\s+', ' ', category_link.select('.//text()').extract().pop().strip())
            if(category == ''):
                continue

            category_url = category_link.select("@href").extract().pop().strip()
            request = Request(urljoin_rfc(base_url, category_url),
                          callback=self.parse_category)
            # saving the category here as there is no way to fetch it from product page
            request.meta['category'] = category
            yield request

    def parse_category(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        product_pages = hxs.select('//table[@bordercolor="#C0C0C0"]//a/@href').extract()
        category = response.meta['category']
        for ppage in product_pages:
            request = Request(urljoin_rfc(base_url, ppage),
                          callback=self.parse_product_page)
            request.meta['category'] = category
            yield request

    def parse_product_page(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        category = response.meta['category']
        # fetching images. the website has an image of a flag of dimension 40x39.
        # Product image is usually larger
        product_image = ""
        pimage_element = hxs.select('//img[@width > 40 and @height > 39]/@src[1]').extract()
        if (len(pimage_element) > 0):
            product_image = pimage_element.pop().strip()

        product_url = response.url

        # Get all the forms containing button "Add To Cart"
        forms = hxs.select('//form[contains(@action, "cartmanager.net/cgi-bin/cart.cgi") and .//input[@type="submit" or @type="image" or @type="button"]]')

        products = []
        for form in forms:
            # Get all product information from cart form
            cart_input_elements = form.select('.//input[@type="hidden" and starts-with(@name, "AddItem")]/@value').extract()

            # If this information is not found we dont proceed
            if(len(cart_input_elements) > 0):
                cart_str = cart_input_elements.pop().strip()

                hidden_fields_xpath = ('.//input[starts-with(@name, "VAR") and '
                '( not(@type) or '
                '@type="hidden" or '
                '(@type="checkbox" and @checked) or '
                '(@type="radio" and @checked))]')

                # Get all the variables to replace information string
                hiddens = form.select(hidden_fields_xpath)


                # Replace all the variables with value in the product information string
                for hidden in hiddens:
                    var_name = hidden.select("@name").extract().pop().strip()
                    var_valu = hidden.select("@value").extract().pop().strip()
                    cart_str = cart_str.replace(var_name, var_valu)

                # Got the proper cart_string of following format
                # 'spicebarn|Soy Sauce Powder  5 Pounds|35.95|1|SoyPowP||prompt|5.2|Tax'
                # 'spicebarn|16 Ounce Pint Plastic Jar VAR000 1.25|VARQuantity|PSJ16||prompt|.24|Tax|||||'
                properties = dict([(item[1], cart_str.split("|")[item[0]])
                                   for item in ((0, 'brand'),
                                                (1, 'name'),
                                                (2, 'price'),
                                                (4, 'ident'),
                                                (7, 'size'))])

                m = re.findall(r'spicebarn\.com/+(.*?)\.html?', response.url, re.IGNORECASE)

                properties.update({'m': ''.join(m)})

                identifier = u'%(ident)s%(size)s%(m)s' % (properties)

                # Sometimes prices comes in '0.00 + 1.99' form.
                price = sum(map(Decimal, properties['price'].split('+')))
                product_name = properties['name'].strip()
                product_name = re.sub(r'\s<BR>.*', '', product_name, 0, re.IGNORECASE)
                if (not "OUT OF STOCK" in product_name.upper()):
                    products.append((product_name, price, identifier))


        # Build the product  and return it.
        for product in products:
            (product_name, price, identifier) = product
            loader = ProductLoader(response=response, item=Product())
            loader.add_value('url', urljoin_rfc(base_url, product_url))
            loader.add_value('name', product_name)
            loader.add_value('image_url', urljoin_rfc(base_url, product_image))
            loader.add_value('brand', 'Spice Barn')
            loader.add_value('price', price)
            loader.add_value('category', category)
            loader.add_value('identifier', identifier)
            if(hxs.select('//td//b/font/i[contains(., "Free Shipping")]')):
                loader.add_value('shipping_cost', 0)


            yield loader.load_item()
