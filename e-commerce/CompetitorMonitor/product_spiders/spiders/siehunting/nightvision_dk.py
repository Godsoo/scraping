# -*- coding: utf-8 -*-

__author__ = 'Theophile R. <rotoudjimaye.theo@gmail.com>'


from .kikkertland_dk import SpiderTemplate, xpath_select

import re
DIGITS = re.compile('^\d+$')

def custom_name_extractor(hxs):
    name = [n.strip(' \r\n') for n in xpath_select(hxs, '//body/table/tbody/tr/td/p/font/text()').extract() if n.strip(' \r\n')]
    if not name:
        name = [n.strip(' \r\n') for n in xpath_select(hxs, '//font[@size=4]/text()').extract() if n.strip(' \r\n')]
    return "".join(name)

def custom_price_extractor(hxs, name=None):
    result = []
    #- special cases
    if 'Night Shadow generation' in name:
        return "".join(xpath_select(hxs, '//body//table[1]/tbody/tr/td//div//table[1]/tbody/tr/td[1]//font[1]/text()').extract()[1].split(":")[1])
    if 'Night Shadow' in name:
        return "".join(hxs.select('//body//table//tbody//tr//td//table//tbody//tr//td//font[1]//text()').extract()[1])
    if '75 x 75 mm, 100 x 100 mm, 150 x 150 mm' in name:
        return xpath_select(hxs, '//body/table/tbody/tr/td/table/tbody/tr/td//div//center//table//tbody//tr//td//p//b/font/text()').extract()[-1].split(" \r\n")[1].strip()

    #- generalisations
    start = xpath_select(hxs, '//table[@id="table9"]/tbody/tr//td//p//b/font/text()').extract()
    if start:
        end = xpath_select(hxs, '//table[@id="table9"]/tbody/tr//td//p//b/font//span/text()').extract()
        result.append([e for e in start if DIGITS.match(e)][-1])
        result.extend(end)
        return "".join([text.strip(' \r\n') for text in result if text.strip(' \r\n')])
    #
    start = xpath_select(hxs, '//table[@id="table3"]/tbody/tr//td//p//b/font/text()').extract()
    if start:
        end = xpath_select(hxs, '//table[@id="table3"]/tbody/tr//td//p//b/font//span/text()').extract()
        result.append([e for e in start if DIGITS.match(e)][-1])
        result.extend(end)
        return "".join([text.strip(' \r\n') for text in result if text.strip(' \r\n')])
    #-
    start = xpath_select(hxs, '//body/table/tbody/tr/td/table/tbody/tr/td//div//center//table//tbody//tr//td//p//b//font/text()').extract()
    end = xpath_select(hxs, '//body/table/tbody/tr/td/table/tbody/tr/td//div//center//table//tbody//tr//td//p//b//font/span/text()').extract()
    if start:
        result.append(start[-1])
    result.extend(end)
    return "".join([text.strip(' \r\n') for text in result if text.strip(' \r\n')])


class NighVisionSpider(SpiderTemplate):
    name = "nightvision.dk"
    allowed_domains = ["nightvision.dk"]
    start_urls = ["http://www.nightvision.dk/"]

    THOUSAND_SEP = "."
    DECIMAL_SEP = ","

    NAV_URL_EXCLUDE = ('.jpg', '.avi', '.pdf', '.gif', '/chat_online.htm', 'Brochure.exe')
    PRODUCT_URL_EXCLUDE = ('/hovedside.htm', '/brugen_af_night_vision.htm', '/download_manualer.htm', '/Hovedside%20for%20laser_ranger_finder_laser_afstandsmåler.htm',
        '/hovedside_til_thermisk_kikkert.htm', '/forhandler_i_ostrig.htm', '/hovedside_til_digitale%20natkikkert.htm', '/forhandler_i_ostrig.htm',
        '/Forhandler%20i%20colombia.htm', '/hovedside%20til%20tilbud.htm', '/Overvaagningsudstyr.htm', '/expert_lrf_8x40_web_galleri.htm',
        '/billeder_optaget_med_cuddeback_overvaagningskameraer.htm', '/billeder_optaget_med_cuddeback_overvaagningskameraer.htm', '/billeder_optaget_med_cuddeback_overvaagningskameraer.htm',
        '/billeder_optaget_med_cuddeback_overvaagningskameraer.htm', '/hovedramme_til_standard.htm', '/forhandlere_i_sverige.htm', '/finansering.htm',
        '/Hovedside%20for%20laser_ranger_finder_laser_afstandsm%C3%A5ler.htm', '/infrared_light.htm', '/hovedside%20til%20kikkerter%20teleskoper.htm', '/hovedside_til_nightvision_natkikert%20night%20vision.htm',
        '/vejledning%20til%20forstegangskobere.htm', '/forhandler%20i%20slovakiet.htm', '/forhandler_i_norge.htm', '/lys_og_lygter.htm', '/hovedside_til_photon_microlight.htm', '/forhandler_i_serbien.htm',
        '/Forhandler%20i%20kuwait.htm', '/hovedramme_til_tilbehor.htm', '/hovedside_til_vejrtaette.htm', '/forklaring_til_photon_lys.htm',
        '/hovedramme_til_binokular_og_gogg.htm', '/forhandlere_i_danmark.htm')

    NAVIGATION = ['//frame/@src', '//a/@href']
    PRODUCT_BOX = [('.', {'name': custom_name_extractor,
                          'price': [custom_price_extractor,
                                    '//body/table/tbody/tr[3]/td/table/tbody/tr/td[3]/div/center/table/tbody/tr[2]/td/p[2]/b/font/span/text()',
                                    '//body/table/tbody/tr[3]/td/table/tbody/tr/td[3]/div/center/table/tbody/tr[2]/td/p/b/font/span/text()',
                                    '//body/table/tbody/tr/td/table/tbody/tr/td//div//center//table//tbody//tr//td//p//b/font/text()',
                                    ]})]





