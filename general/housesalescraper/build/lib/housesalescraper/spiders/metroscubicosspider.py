# /media/simon/mine/mine/scrape/nicolas/program/hotelscraper/hotelscraper/spiders

from scrapy.spiders import Spider
from scrapy.selector import Selector
from scrapy.http import Request
from housesalescraper.items import MetroscubicosItem
# from selenium import webdriver
from bs4 import BeautifulSoup
from lxml import html
import csv
import re

class metroscubicosspider(Spider):
    name = "metroscubicosspider"
    start_urls = [
        # "http://inmuebles.metroscubicos.com/casas/venta/#origin=search&as_word=true",
        "http://inmuebles.metroscubicos.com/departamentos/renta/polanco#origin=search&as_word=true",
        # "http://departamento.metroscubicos.com/MLM-565409316-grand-polanco-irrigacion-magnifica-ubicacion-_JM"
        ]

    def __init__(self):

        self.page_num = 0


    def parse(self, response):

        tree     = html.parse( response.url )
        ol_xpath = '//div[@class="section"]/ol[@class="section gallery-large classified real-estate res "]'
        ol_body  = tree.xpath( ol_xpath )[0]
        ol_html  = html.tostring( ol_body )

        soup = BeautifulSoup( ol_html )

        liTags = soup.find_all("li", attrs={'class' : 'item-realestate rowItem'})

        for liTag in liTags:

            divTag_cont = liTag.find('div', attrs={'class': 'item-content'})


            item = MetroscubicosItem()

            o_price = divTag_cont.find('p', attrs={'class': 'item-price'})

            if ( o_price ) :
                item['price'] = o_price.text.strip('\n').strip()
            else :
                item['price'] = '_'

            o_offers = divTag_cont.find('h2', attrs={'class': 'list-view-item-title'})

            if ( o_offers ) :
                item['offers'] = o_offers.text.strip('\n').strip()
            else :
                item['offers'] = '_'

            o_address = divTag_cont.find('div', attrs={'class': 'item-title'})

            if ( o_address ) :
                item['address'] = o_address.text.strip('\n').strip()
            else :
                item['address'] = '_'

            o_detail = divTag_cont.find('a',   attrs={'class': ''})

            if ( o_detail ) :
                item['detail'] = o_detail.get('href')
            else :
                item['detail'] = '_'

            ul_detail = divTag_cont.find('ul', attrs={'class': 'classified-details'})

            if ( ul_detail ) :

                lis = ul_detail.findAll('li')

                if ( len(lis) > 0 ) :
                    item['size'] = lis[0].get_text()
                else :
                    item['size'] = '_'

                if ( len(lis) > 1 ) :
                    item['rooms'] = lis[1].get_text()
                else :
                    item['rooms'] = '_'

            else :

                item['size']  = '_'
                item['rooms'] = '_'

            # yield item

            request = Request(url=item['detail'], callback=self.parse_detail)

            request.meta['price']   = item['price']
            request.meta['offers']  = item['offers']
            request.meta['address'] = item['address']
            request.meta['detail']  = item['detail']
            request.meta['size']    = item['size']
            request.meta['rooms']   = item['rooms']

            yield request

        self.page_num = self.page_num + 1

        if ( len(response.xpath( '//a[contains(text(), "Siguiente >")]/@href' ).extract()) > 0 ) :
        # if ( self.page_num < 1 ) :

            yield Request(url=response.xpath( '//a[contains(text(), "Siguiente >")]/@href' ).extract()[0], callback=self.parse)


    def parse_detail(self, response):

        tree = html.parse( response.url )

        main_content_xpath  = '//div[@class="nav-main-content"]'
        main_content        = tree.xpath( main_content_xpath )[0]
        main_content_html   = html.tostring( main_content )

        soup = BeautifulSoup( main_content_html )

        item = MetroscubicosItem()

        item['price']   = response.meta['price']
        item['offers']  = response.meta['offers']
        item['address'] = response.meta['address']
        item['detail']  = response.meta['detail']
        item['size']    = response.meta['size']
        item['rooms']   = response.meta['rooms']

        sec_ubi = soup.find('section', attrs={'class': 'vip-section-map container'})

        if ( sec_ubi ) :
            item['Ubicación'] = sec_ubi.h2.get_text().strip('\n').strip()
        else :
            item['Ubicación'] = '_'


        sec_desc = soup.find('div', attrs={'class': 'description-content-main-group attribute-content'})

        if ( sec_desc ) :
            item['Descripción'] = sec_desc.get_text().strip('\n').strip()
        else :
            item['Descripción'] = '_'

        div_secondaries = soup.find('div', attrs={'class': 'description-content-secondary-group attribute-content'})

        if ( div_secondaries ) :

            span_amb = div_secondaries.find('span', text='Ambientes')

            if ( span_amb ) :
                div_amb = span_amb.parent.findNext('div')
                if ( div_amb ) :
                    item['Ambientes'] = div_amb.get_text().strip('\n').strip()
                else :
                    item['Ambientes'] = '_'
            else :
                item['Ambientes'] = '_'

            span_como = div_secondaries.find('span', text='Comodidades y amenities')

            if ( span_como ) :
                div_como = span_como.parent.findNext('div')
                if ( div_como ) :
                    item['Comodidades'] = div_como.get_text().strip('\n').strip()
                else :
                    item['Comodidades'] = '_'
            else :
                item['Comodidades'] = '_'
        else :
            item['Comodidades'] = '_'


        p_desc_title = soup.find('p', attrs={'class': 'description-content-title'})

        if ( p_desc_title ) :
            item['Desc_title'] = p_desc_title.get_text().strip('\n').strip()
        else :
            item['Desc_title'] = '_'


        pre_desc_content = soup.find('pre', attrs={'class': 'preformated-text'})

        if ( pre_desc_content ) :
            item['Desc_content'] = pre_desc_content.get_text().strip('\n').strip()
        else :
            item['Desc_content'] = '_'

        yield item
