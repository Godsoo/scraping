# /media/simon/mine/mine/scrape/Jesus/housesalescraper

from scrapy.spiders import Spider
from scrapy.selector import Selector
from scrapy.http import Request
from housesalescraper.items import Inmuebles24Item
# from selenium import webdriver
from bs4 import BeautifulSoup
from lxml import html
import csv
import re

class inmuebles24spider(Spider):
    name = "inmuebles24spider"
    start_urls = [
        # "http://www.inmuebles24.com/departamentos-en-venta-busquedaext-mexico-d.f..html",
        # "http://www.inmuebles24.com/departamentos-en-venta-busquedaext-monterrey.html",
        # "http://www.inmuebles24.com/departamentos-en-venta-busquedaext-guadalajara.html",
        "http://www.inmuebles24.com/departamentos-en-venta-busquedaext-leon.html",
        # "http://www.inmuebles24.com/departamentos-en-venta-busquedaext-queretaro.html",
        ]

    def __init__(self):

        self.page_num  = 0
        self.city_name = ''

    def start_requests(self):

        with open('name', 'w') as outfile:
            # json.dump(newjson, outfile)
            outfile.write("content")

        outfile.close()

        for u in self.start_urls :

            # yield scrapy.Request(u, callback=self.parse_httpbin, errback=self.errback_httpbin, dont_filter=True)

            if ( u == "http://www.inmuebles24.com/departamentos-en-venta-busquedaext-mexico-d.f..html" ) :

                self.city_name = 'mexico-d.f.'

            elif ( u == "http://www.inmuebles24.com/departamentos-en-venta-busquedaext-monterrey.html" ) :

                self.city_name = "monterrey"

            elif ( u == "http://www.inmuebles24.com/departamentos-en-venta-busquedaext-guadalajara.html" ) :

                self.city_name = "guadalajara"

            elif ( u == "http://www.inmuebles24.com/departamentos-en-venta-busquedaext-leon.html" ) :

                self.city_name = "leon"

            elif ( u == "http://www.inmuebles24.com/departamentos-en-venta-busquedaext-queretaro.html" ) :

                self.city_name = "queretaro"

            request = Request(u, callback=self.parse_httpbin, dont_filter=True)

            request.meta['mycity'] = self.city_name

            # yield Request(u, callback=self.parse_httpbin, dont_filter=True)
            yield request

    # def parse(self, response):
    def parse_httpbin(self, response):

        tree     = html.parse( response.url )
        ul_xpath = '//div[@class="container"]/section/ul[@class="list-posts"]'
        ul_body  = tree.xpath( ul_xpath )[0]
        ul_html  = html.tostring( ul_body )

        soup = BeautifulSoup( ul_html )

        liTags = soup.find_all("li", attrs={'data-href' : True})

        for liTag in liTags:

            divTag_desc = liTag.find('div', attrs={'class': 'post-text-desc'})
            divTag_pay  = liTag.find('div', attrs={'class': 'post-text-pay'})

            liTag_unidades     = liTag.find('li', attrs={'class': 'misc-unidades'})
            liTag_metros       = liTag.find('li', attrs={'class': 'misc-metros'})
            liTag_habitaciones = liTag.find('li', attrs={'class': 'misc-habitaciones'})
            liTag_m2totales    = liTag.find('li', attrs={'class': 'misc-m2totales'})
            liTag_banos        = liTag.find('li', attrs={'class': 'misc-banos'})

            spanTag_price  = liTag.find('span', attrs={'class': 'precio-valor '} )

            item = Inmuebles24Item()

            item['title']   = divTag_desc.div.h4.a.get_text().strip('\n').strip()
            # item['title_href'] = divTag_desc.div.h4.a.get('href')
            item['comment'] = divTag_desc.div.p.get_text().strip('\n').strip()
            item['detail']  = divTag_desc.div.a.get('href').strip('\n').strip()
            item['entrega'] = divTag_pay.ul.span.get_text().strip('\n').strip()


            
            if ( liTag_banos ) :
                item['banos']     = liTag_banos.text.strip('\n').strip()
            else :
                item['banos']     = '_'

            if ( liTag_m2totales ) :
                item['m2totales']     = liTag_m2totales.text.strip('\n').strip()
            else :
                item['m2totales']     = '_'

            if ( liTag_unidades ) :
                item['unidades']     = liTag_unidades.text.strip('\n').strip()
            else :
                item['unidades']     = '_'

            if ( liTag_metros ) :
                item['metros']       = liTag_metros.text.strip('\n').strip()
            else :
                item['metros']     = '_'

            if ( liTag_habitaciones ) :
                item['habitaciones'] = liTag_habitaciones.text.strip('\n').strip()
            else :
                item['habitaciones']     = '_'

            if ( spanTag_price ) :
                item['price'] = spanTag_price.text.strip('\n').strip()
            else :
                item['price']     = '_'

            # yield item

            # if ( len(item['detail']) > 0 ) :

            request = Request(url="http://www.inmuebles24.com" + item['detail'], callback=self.parse_detail, dont_filter=True)
            
            # request = Request(url="http://www.inmuebles24.com" + item['detail'], callback=self.parse_detail, errback=self.parse_detail_error, dont_filter=True)
            # request = Request(url="http://www.inmuebles24.com" + item['detail'], callback=self.parse_detail)

            request.meta['mycity']       = response.meta['mycity']
            request.meta['title']        = item['title']
            request.meta['comment']      = item['comment']
            request.meta['detail']       = item['detail']
            request.meta['entrega']      = item['entrega']
            request.meta['banos']        = item['banos']
            request.meta['m2totales']    = item['m2totales']
            request.meta['unidades']     = item['unidades']
            request.meta['metros']       = item['metros']
            request.meta['habitaciones'] = item['habitaciones']
            request.meta['price']        = item['price']


            yield request


        self.page_num = self.page_num + 1

        # if ( len(response.xpath( '//a[@rel="next"]/@href' ).extract()) > 0 ) :
        # if ( self.page_num < 3 ) :

        nexturl = response.xpath( '//a[@rel="next"]/@href' ).extract()[0]

        if ( nexturl != '#') :

            req_self = Request(url=nexturl, callback=self.parse_httpbin, dont_filter=True)

            req_self.meta['mycity'] = response.meta['mycity']

            yield req_self
            # yield Request(url=nexturl, callback=self.parse_httpbin, dont_filter=True)
            # yield Request(url=nexturl, callback=self.parse, dont_filter=True)


    def parse_detail(self, response):

        item = Inmuebles24Item()


        item['mycity']       = response.meta['mycity']

        item['title']        = response.meta['title']
        item['comment']      = response.meta['comment']
        item['detail']       = response.meta['detail']
        item['entrega']      = response.meta['entrega']
        item['banos']        = response.meta['banos']
        item['m2totales']    = response.meta['m2totales']
        item['unidades']     = response.meta['unidades']
        item['metros']       = response.meta['metros']
        item['habitaciones'] = response.meta['habitaciones']
        item['price']        = response.meta['price']

        try :

            tree = html.parse( response.url )

            ul_xpath = '//div[@class="row sticky-holder"]/div[@class="span16"]/div[@class="row"]'

            temp_ul_body = tree.xpath( ul_xpath )

            if ( len(temp_ul_body) > 0 ) :

                ul_body  = temp_ul_body[0]
                ul_html  = html.tostring( ul_body )

                soup = BeautifulSoup( ul_html )

                divTag_datos    = soup.find('div', attrs={'class': 'card aviso-datos'})
                divTag_location = soup.find('div', attrs={'class': 'card location'})
                divTag_desc     = soup.find('div', attrs={'class': 'card description'})
                divTag_chars    = soup.find_all('div', attrs={'class': 'card aviso-caracteristicas'})
                
                if ( divTag_datos ) :
                    temptag = divTag_datos.find('ul')
                    if ( temptag ) :
                        item['datos_principales'] = temptag.text.strip()
                    else :
                        item['datos_principales'] = '_'
                else :
                    item['datos_principales'] = '_'

                if ( divTag_location ) :
                    temptag = divTag_location.find('ul')
                    if ( temptag ) :
                        item['ubicación']         = temptag.text.strip()
                    else :
                        item['ubicación'] = '_'
                else :
                    item['ubicación'] = '_'

                if ( divTag_desc ) :
                    temptag = divTag_desc.find('span', attrs={'id': 'id-descipcion-aviso'})
                    if ( temptag ) :
                        item['descripción']       = temptag.text.strip()
                    else :
                        item['descripción'] = '_'
                else :
                    item['descripción'] = '_'

                for divTag_char in divTag_chars :

                    temp_ul = divTag_char.find('div',  attrs={'class': 'list list-checkmark no-margin'}).ul

                    if ( temp_ul ) :

                        if ( divTag_char.find('h3').text == 'Áreas Sociales'):
                            item['areas_sociales']    = temp_ul.text.strip()  

                        if ( divTag_char.find('h3').text == 'Ambientes'):
                            item['ambientes']         = temp_ul.text.strip()  

                        if ( divTag_char.find('h3').text == 'Exteriores'):
                            item['exteriores']        = temp_ul.text.strip()  

                        if ( divTag_char.find('h3').text == 'Generales'):
                            item['generales']         = temp_ul.text.strip()  

                        if ( divTag_char.find('h3').text == 'Servicios'):
                            item['servicios']         = temp_ul.text.strip()  

        except e:
            pass

        yield item
