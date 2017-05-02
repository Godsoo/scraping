from product_spiders.base_spiders.primary_spider import PrimarySpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from urlparse import urljoin as urljoin_rfc
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


class DV247(PrimarySpider):
    name = 'dv247.com'
    allowed_domains = ['dv247.com', 'www.dv247.com']
    start_urls = ('http://www.dv247.com',)
    csv_file = 'dv247_com_crawl.csv'
    _formdata = {'__VIEWSTATE': '/wEPDwULLTEzNDc4NzE5MDQPZBYEAgEPZBYEAgIPFgQeBG5hbWUFC2Rlc2NyaXB0aW9uHgdjb250ZW50BWxCdXkgVm9jYWwgTWljcm9waG9uZXMgZnJvbSBhIGh1Z2Ugc2VsZWN0aW9uIG9mIG11c2ljIGFuZCBwcm8tYXVkaW8gZXF1aXBtZW50LiBTaG9wIG9ubGluZSB3aXRoIERWMjQ3LmNvbSAuLi5kAgMPFgQfAAUIa2V5d29yZHMfAQURVm9jYWwgTWljcm9waG9uZXNkAgUPZBYIAgQPZBYEZg8QZA8WA2YCAQICFgMQBQXCo0dCUAUDR0JQZxAFBuKCrEVVUgUDRVVSZxAFBCRVU0QFA1VTRGcWAQIBZAIBDxAPFgQeDURhdGFUZXh0RmllbGQFDExhbmd1YWdlQ29kZR4ORGF0YVZhbHVlRmllbGQFDExhbmd1YWdlQ29kZWQPFghmAgECAgIDAgQCBQIGAgcWCBAFB0VuZ2xpc2gFAmVuZxAFCEZyYW5jYWlzBQJmcmcQBQdEZXV0c2NoBQJkZWcQBQdFc3Bhbm9sBQJlc2cQBQpQb3J0dWd1ZXNlBQJwdGcQBQhJdGFsaWFubwUCaXRnEAUKTmVkZXJsYW5kcwUCbmxnEAUFU3VvbWkFAmZpZxYBZmQCCQ8WAh4JaW5uZXJodG1sBRZDdXJyZW5jeSBzZXQgdG8gRVVSLi4uZAIND2QWAgIEDw8WAh4HVmlzaWJsZWhkFgYCAQ8QD2QWAh4Jb25rZXlkb3duBT5mblRyYXBLRChkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgnTGlzdDFfRmlsdGVyX0ZpbHRlcicpLGV2ZW50KWQWAGQCAw8QD2QWAh8GBT5mblRyYXBLRChkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgnTGlzdDFfRmlsdGVyX0ZpbHRlcicpLGV2ZW50KWQWAGQCBQ8PZBYCHwYFPmZuVHJhcEtEKGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCdMaXN0MV9GaWx0ZXJfRmlsdGVyJyksZXZlbnQpZAIOD2QWAgIED2QWBgIBDxAPZBYCHwYFPWZuVHJhcEtEKGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCdMaXN0X0ZpbHRlcl9GaWx0ZXInKSxldmVudCkQFQIOQWxsIGNh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Y3RsMDAkTXlJdGVtcyRjdGwxMCRBbHAPFCsAAmQFBTE3ODk0ZAUeX19Db250cm9sc1JlcXVpcmVQb3N0QmFja0tleV9fFi4FHUxpc3QxJGN0bDAwJE15SXRlbXMkY3RsMDEkQWxwBR1MaXN0MSRjdGwwMCRNeUl0ZW1zJGN0bDAyJEFscAUdTGlzdDEkY3RsMDAkTXlJdGVtcyRjdGwwMyRBbHAFHUxpc3QxJGN0bDAwJE15SXRlbXMkY3RsMDQkQWxwBR1MaXN0MSRjdGwwMCRNeUl0ZW1zJGN0bDA1JEFscAUdTGlzdDEkY3RsMDAkTXlJdGVtcyRjdGwwNiRBbHAFHUxpc3QxJGN0bDAwJE15SXRlbXMkY3RsMDckQWxwBR1MaXN0MSRjdGwwMCRNeUl0ZW1zJGN0bDA4JEFscAUdTGlzdDEkY3RsMDAkTXlJdGVtcyRjdGwwOSRBbHAFHUxpc3QxJGN0bDAwJE15SXRlbXMkY3RsMTAkQWxwBR1MaXN0MSRjdGwwMCRNeUl0ZW1zJGN0bDExJEFscAUdTGlzdDEkY3RsMDAkTXlJdGVtcyRjdGwxMiRBbHAFHUxpc3QxJGN0bDAwJE15SXRlbXMkY3RsMTMkQWxwBR1MaXN0MSRjdGwwMCRNeUl0ZW1zJGN0bDE0JEFscAUdTGlzdDEkY3RsMDAkTXlJdGVtcyRjdGwxNSRBbHAFHUxpc3QxJGN0bDAwJE15SXRlbXMkY3RsMTYkQWxwBRxMaXN0JGN0bDAwJE15SXRlbXMkY3RsMDEkQWx0BRxMaXN0JGN0bDAwJE15SXRlbXMkY3RsMDIkQWx0BRxMaXN0JGN0bDAwJE15SXRlbXMkY3RsMDMkQWx0BRxMaXN0JGN0bDAwJE15SXRlbXMkY3RsMDQkQWx0BRxMaXN0JGN0bDAwJE15SXRlbXMkY3RsMDUkQWx0BRxMaXN0JGN0bDAwJE15SXRlbXMkY3RsMDYkQWx0BRxMaXN0JGN0bDAwJE15SXRlbXMkY3RsMDckQWx0BRxMaXN0JGN0bDAwJE15SXRlbXMkY3RsMDgkQWx0BRxMaXN0JGN0bDAwJE15SXRlbXMkY3RsMDkkQWx0BRxMaXN0JGN0bDAwJE15SXRlbXMkY3RsMTAkQWx0BRxMaXN0JGN0bDAwJE15SXRlbXMkY3RsMTEkQWx0BRxMaXN0JGN0bDAwJE15SXRlbXMkY3RsMTIkQWx0BRxMaXN0JGN0bDAwJE15SXRlbXMkY3RsMTMkQWx0BRxMaXN0JGN0bDAwJE15SXRlbXMkY3RsMTQkQWx0BRxMaXN0JGN0bDAwJE15SXRlbXMkY3RsMTUkQWx0BRxMaXN0JGN0bDAwJE15SXRlbXMkY3RsMTYkQWx0BRxMaXN0JGN0bDAwJE15SXRlbXMkY3RsMTckQWx0BRxMaXN0JGN0bDAwJE15SXRlbXMkY3RsMTgkQWx0BRxMaXN0JGN0bDAwJE15SXRlbXMkY3RsMTkkQWx0BRxMaXN0JGN0bDAwJE15SXRlbXMkY3RsMjAkQWx0BRxMaXN0JGN0bDAwJE15SXRlbXMkY3RsMjEkQWx0BRxMaXN0JGN0bDAwJE15SXRlbXMkY3RsMjIkQWx0BRxMaXN0JGN0bDAwJE15SXRlbXMkY3RsMjMkQWx0BRxMaXN0JGN0bDAwJE15SXRlbXMkY3RsMjQkQWx0BRxMaXN0JGN0bDAwJE15SXRlbXMkY3RsMjUkQWx0BRxMaXN0JGN0bDAwJE15SXRlbXMkY3RsMjYkQWx0BRxMaXN0JGN0bDAwJE15SXRlbXMkY3RsMjckQWx0BRxMaXN0JGN0bDAwJE15SXRlbXMkY3RsMjgkQWx0BRxMaXN0JGN0bDAwJE15SXRlbXMkY3RsMjkkQWx0BRxMaXN0JGN0bDAwJE15SXRlbXMkY3RsMzAkQWx0BRxMaXN0JGN0bDAwJE15SXRlbXMkY3RsMTUkQWx0DxQrAAJkBQYyNTgwMjJkBRxMaXN0JGN0bDAwJE15SXRlbXMkY3RsMTIkQWx0DxQrAAJkBQYyMzIzOTRkBR1MaXN0MSRjdGwwMCRNeUl0ZW1zJGN0bDExJEFscA8UKwACZAUFMjYzNzJkBRxMaXN0JGN0bDAwJE15SXRlbXMkY3RsMjckQWx0DxQrAAJkBQUzMDM3MWQFHExpc3QkY3RsMDAkTXlJdGVtcyRjdGwwMyRBbHQPFCsAAmQFBjI1NzQxNGQFHUxpc3QxJGN0bDAwJE15SXRlbXMkY3RsMTIkQWxwDxQrAAJkBQUxNDg1OGQFHExpc3QkY3RsMDAkTXlJdGVtcyRjdGwxMCRBbHQPFCsAAmQFBjEzODI2NWQFHExpc3QkY3RsMDAkTXlJdGVtcyRjdGwzMCRBbHQPFCsAAmQFBTg0OTQxZAUcTGlzdCRjdGwwMCRNeUl0ZW1zJGN0bDAyJEFsdA8UKwACZAUGMjY0NjM4ZAUdTGlzdDEkY3RsMDAkTXlJdGVtcyRjdGwwMSRBbHAPFCsAAmQFBjI1NzAzOGQFHExpc3QkY3RsMDAkTXlJdGVtcyRjdGwyNSRBbHQPFCsAAmQFBjI5NzgxOGQFHExpc3QkY3RsMDAkTXlJdGVtcyRjdGwxNCRBbHQPFCsAAmQFBTE1MDE0ZAUcTGlzdCRjdGwwMCRNeUl0ZW1zJGN0bDIyJEFsdA8UKwACZAUGMTMyMjYxZAUdTGlzdDEkY3RsMDAkTXlJdGVtcyRjdGwwMiRBbHAPFCsAAmQFBjI2NDYzOGQFHUxpc3QxJGN0bDAwJE15SXRlbXMkY3RsMTQkQWxwDxQrAAJkBQUzMzE0MGQFHExpc3QkY3RsMDAkTXlJdGVtcyRjdGwwMSRBbHQPFCsAAmQFBjI1NzAzOGQFHExpc3QkY3RsMDAkTXlJdGVtcyRjdGwyMCRBbHQPFCsAAmQFBTE4Mzk4ZAUdTGlzdDEkY3RsMDAkTXlJdGVtcyRjdGwxNSRBbHAPFCsAAmQFBTI3NTIxZAUdTGlzdDEkY3RsMDAkTXlJdGVtcyRjdGwwOCRBbHAPFCsAAmQFBjI1NTQxNGQFHExpc3QkY3RsMDAkTXlJdGVtcyRjdGwwOCRBbHQPFCsAAmQFBjI5MjUyNmQFHExpc3QkY3RsMDAkTXlJdGVtcyRjdGwxMSRBbHQPFCsAAmQFBTIxNTgxZAUdTGlzdDEkY3RsMDAkTXlJdGVtcyRjdGwwNCRBbHAPFCsAAmQFBjI2NDYzMGQFHExpc3QkY3RsMDAkTXlJdGVtcyRjdGwwNiRBbHQPFCsAAmQFBjI1NTQwNmQFHUxpc3QxJGN0bDAwJE15SXRlbXMkY3RsMDkkQWxwDxQrAAJkBQYzMTg4NTRkBRxMaXN0JGN0bDAwJE15SXRlbXMkY3RsMTgkQWx0DxQrAAJkBQYxODk1MjlkBRxMaXN0JGN0bDAwJE15SXRlbXMkY3RsMjMkQWx0DxQrAAJkBQUxMTA5MGQFHExpc3QkY3RsMDAkTXlJdGVtcyRjdGwxNiRBbHQPFCsAAmQFBjI1ODAwMmQFHExpc3QkY3RsMDAkTXlJdGVtcyRjdGwwNCRBbHQPFCsAAmQFBjI2NTQ0MmQFHUxpc3QxJGN0bDAwJE15SXRlbXMkY3RsMDYkQWxwDxQrAAJkBQUxMTExNGTM2FXf8/UxS6SEhlfvmSQa40WGbqrsW5OYLUMWcH4V9w==', '__EVENTTARGET': 'Localisation$Currency', 'Localisation$Currency': 'GBP', '__EVENTVALIDATION': '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'}

    def parse_fields(self, response):
        loader = response.meta.get('loader')
        URL_BASE = 'http://www.dv247.com'

        hxs = HtmlXPathSelector(response)

        category = hxs.select('//div[@id="breadcrumb"]/p/a/text()').extract()
        category = category[-2] if len(category) > 1 else ''

        loader.add_value('category', category)

        image_url = hxs.select('//img[@itemprop="image"]/@src').extract()
        if image_url:
            image_url = urljoin_rfc(URL_BASE, image_url[0])
            loader.add_value('image_url', image_url)

        brand = hxs.select('//p[@itemprop="manufacturer"]/span[@itemprop="name"]/text()').extract()
        brand = brand[0] if brand else ''
        loader.add_value('brand', brand)
	
        shipping_cost = '4.99' if float(loader.get_output_value('price')) < 99 else '0.00'
        loader.add_value('shipping_cost', shipping_cost)
        stock = None
        out_of_stock = hxs.select('//div[@id="product"]//div[@id="retail"]/p[@class="unavailable"]')
        if not out_of_stock:
            out_of_stock = hxs.select('//*[@id="retail"]//img[@alt="Sold!"]')
        usually_stock = hxs.select('//div[@id="product"]//div[@id="retail"]/p[@class="usually"]')
        if not out_of_stock and not usually_stock:
            stock = hxs.select('//div[@id="product"]//div[@id="retail"]/p[@class="inStock"]/text()')
            if stock:
                stock = stock[0].extract().replace('only ', '').split(' ')[0]
                stock = 6 if '5+' in stock else int(stock)
        if out_of_stock:
            loader.add_value('stock', 0)
        elif stock:
            loader.add_value('stock', stock)
        if loader.get_output_value('price'):
            yield loader.load_item()

    def parse_product(self, response):
        URL_BASE = 'http://www.dv247.com'

        hxs = HtmlXPathSelector(response)
        
        if not hxs.select('//ul[@id="currencySelection"]/li[@class="active"]/a/text()').re('GBP'):
	  yield FormRequest(response.url, formdata=self._formdata, dont_filter=True, callback=self.parse_product)
	  return

        products = hxs.select('//div[@class="listItem clearfix"]')
        products += hxs.select('//div[@class="innerProduct"]')
        for p in products:
            loader = ProductLoader(item=Product(), selector=hxs)
            name = ' '.join(p.select('.//a//text()').extract())
            url = p.select('.//a/@href')[0].extract()
            url = urljoin_rfc(URL_BASE, url)
            sku = url.split('--')[-1] if url.split('--') else ''
            identifier = sku
            price = p.select('.//li[@class="price"]/text()').re('\xa3(.*)')
            if not price:
                price = p.select('.//p[@class="price"]/text()').re('\xa3(.*)')

            price = price[0] if price else '0'

            if price == 'TBA':
                continue
            loader.add_value('url', url)
            loader.add_value('name', name)
            loader.add_value('price', price)
            loader.add_value('sku', sku)
            loader.add_value('identifier', identifier)
            yield Request(url, callback=self.parse_fields, meta={'loader': loader})


    def parse(self, response):
        if not isinstance(response, HtmlResponse):
            return
        URL_BASE = 'http://www.dv247.com'
        # categories
        hxs = HtmlXPathSelector(response)
        category_urls = hxs.select('//nav[@id="megamenu"]//a/@href | \
                                    //nav[@id="megamenu"]//li[@class="accessories threeCol"]//a/@href').extract()
        # the following category had to be added manually because the link is broken.
        category_urls.append('/computer-music-software/')
        # add sub-categories
        category_urls += hxs.select('//ul[li/a[@class="selected"]]//li/a/@href').extract()
        for url in category_urls:
            if url == '#':
                continue
            url = urljoin_rfc(URL_BASE, url)
            yield Request(url)


        # next page
        next_pages = hxs.select('//div[@class="listPaging"]')
        if next_pages:
            next_pages = next_pages[0].select('.//a[not(@class="selectedpage")]/@href').extract()
            for page in next_pages:
                url = urljoin_rfc(URL_BASE, page)
                yield Request(url)

        # products
        for p in self.parse_product(response):
            yield p
