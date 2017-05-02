from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


class CDiscountSpider(BaseSpider):
    name = 'cdiscount.com_aivarsk'
    allowed_domains = ['cdiscount.com']

    start_urls = (
        u'http://www.cdiscount.com/maison/bricolage-outillage/l-11704.html',
        u'http://www.cdiscount.com/maison/bricolage-outillage/outillage-de-jardin/v-1170414-1170414.html',
        u'http://www.cdiscount.com/electromenager/aspirateur-nettoyeur-vapeur/v-11014-11014.html'
    )

    download_delay = 0.15
    randomize_download_delay = True

    RETRY_TIMES = 5

    def parse(self, response):
        if not isinstance(response, HtmlResponse):
            self.log('ERROR: BAD HtmlResponse!!! URL:{}'.format(response.url))
            return

        hxs = HtmlXPathSelector(response)

        # logic to find categories
        # find subcats for Outilage Jardin
        categories = hxs.select('//div[contains(@class,"bg_U15 menugroup") and contains(@alt,"Jardin") and contains(@alt,"Outillage")]//div[@class="jsGroup"]//ul[@class="tree"]//a/@href').extract()
        # find subcats for Aspirateurs
        categories += hxs.select('//div[contains(@class,"bg_U4 menugroup") and contains(@alt,"Entretien") and contains(@alt,"maison")]//div[@class="jsGroup"]//ul[@class="tree"]//a/@href').extract()

        for url in categories:
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url)

        totalproducts = hxs.select('//span[@class="SearchBig"]/text()').re(r'(\d+)')

        # pagination
        next_page = hxs.select(u'//ul[@class="PaginationButtons"]//a[contains(text(),"Suivant")]/@href').extract()
        if next_page and int(totalproducts[0]) <= 100000:
            if not 'filter_active' in response.meta:
                next_page = urljoin_rfc(get_base_url(response), next_page[0])
                yield Request(next_page,
                              meta={'next_page_retry': 1,
                                    'dont_redirect': True})
            else:
                next_page = hxs.select(u'//ul[@class="PaginationButtons"]//a[contains(text(),"Suivant")]')
                next_page_onclick_id = next_page.select('@id').extract()[-1] + '.OnClick'
                req = FormRequest.from_response(response, formname='PageForm', formdata={next_page_onclick_id: u'1'}, meta={'filter_active': True})
                req.dont_filter = True
                yield req

        if totalproducts and int(totalproducts[0]) > 100000 and not response.meta.get('filter_active'):
            filters = hxs.select('//div[@class="blocFilter" and contains(strong/text(), "Type de produit")]//input/@name').extract()
            req_base = FormRequest.from_response(response, formname='PageForm', meta={'filter_active': True},dont_click=True)
            for filter in filters:
                req = replace_formdata(req_base, formdata={filter: u'1'})
                req.dont_filter = True
                yield req

        products = hxs.select(u'//div[@id="productList"]//div[contains(@class,"plProductView")]')
        if products:
            for product in products:
                product_loader = ProductLoader(item=Product(), selector=product)
                product_loader.add_xpath('url', './/a[contains(@class,"plPrName")]/@href')
                product_loader.add_xpath('name', './/a[contains(@class,"plPrName")]/text()')
                product_loader.add_xpath('category', '//div[@class="productListTitle"]/h1/text()')
                product_loader.add_xpath('image_url', './/div[contains(@class, "plProductImg")]//img/@data-src')
                product_loader.add_xpath('sku', './@data-sku')
                product_loader.add_xpath('identifier', './/input[contains(@name, "ProductPostedForm.ProductId")]/@value')
                price = product.select(u'.//div[contains(@class,"priceContainer")]/div[contains(@class,"priceM")]/text()').extract()
                if price:
                    decimals = product.select(u'//div[contains(@class,"priceContainer")]/div[contains(@class,"priceM")]/sup/text()').re(u'(\d+)')
                    if decimals:
                        price = price[0] + '.' + decimals[0]
                product_loader.add_value('price', price)
                product_loader.add_value('stock', 1)
                if product_loader.get_output_value('name') and product_loader.get_output_value('price'):
                    identifier = product_loader.get_output_value('identifier')
                    if identifier and identifier.strip():
                        yield product_loader.load_item()
                    else:
                        self.log('PRODUCT WITH NO IDENTIFIER => %s' % response.url)
        else:
            # this site is buggy (it returns no products when we traverse thru the pages at random rate)
            # so this is a kind of retry code
            if 'next_page_retry' in response.meta:
                self.log('ERROR - NO PRODUCTS FOUND, retrying...')
                count = response.meta['next_page_retry']
                if count < self.RETRY_TIMES:
                    self.log('ERROR - NO PRODUCTS FOUND, retry #{} url: {}'.format(count, response.url))
                    if not 'filter_active' in response.meta:
                        yield Request(response.url,
                                      meta={'next_page_retry': count + 1,
                                            'dont_redirect': True},
                                      dont_filter=True
                                      )
                    else:
                        # TODO: FormRequest?
                        pass
                else:
                    self.log('ERROR - NO PRODUCTS FOUND, retry limit reached, giving up, url: {}'.format(response.url))

def replace_formdata(req, formdata):
    '''
        Code like this causes HTML to be parsed over and over again
        req = FormRequest.from_response(response, formname='PageForm', formdata={filter: u'1'}, meta={'filter_active': True})
        This function performs Request.replace() with additional handling of formdata
    '''
    import urllib
    import urlparse
    seq = urlparse.parse_qs(req.body).iteritems()
    values = [(k, v) for k, vs in seq for v in (vs if hasattr(vs, '__iter__') else [vs]) if k not in formdata]
    values.extend(formdata.iteritems())
    return req.replace(body=urllib.urlencode(values, doseq=1))

