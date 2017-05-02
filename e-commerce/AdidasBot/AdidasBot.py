from scrapex import *
import timeit
import time
import sys
import csv
from random import randint
import base64
import threading
import re
from time import sleep
import json
import base64
import smtplib
from email.mime.text import MIMEText
from urlparse import urlparse
# import msvcrt
from cookielib import Cookie, CookieJar

threads = 1   # Number of threads to create
login = False # Whether should login or not
# UserAgent = 'Mozilla/5.0 (Windows NT 6.3; Win64; x64; rv:46.0) Gecko/20100101 Firefox/46.0'
UserAgent = 'Mozilla/5.0 (Windows NT 6.3; Win64; x64; rv:50.0) Gecko/20100101 Firefox/50.0'

proxy_pool = [  '67.220.254.105:18058', '67.220.254.106:18058', '67.220.254.11:18058', '67.220.254.110:18058', '67.220.254.111:18058', 
                '67.220.254.114:18058', '67.220.254.115:18058', '67.220.254.117:18058', '67.220.254.12:18058', '67.220.254.121:18058', 
                '67.220.254.123:18058', '67.220.254.125:18058', '67.220.254.126:18058', '67.220.254.127:18058', '67.220.254.128:18058', 
                '67.220.254.13:18058', '67.220.254.131:18058', '67.220.254.132:18058', '67.220.254.133:18058', '67.220.254.134:18058', 
                '67.220.254.135:18058', '67.220.254.137:18058', '67.220.254.14:18058', '67.220.254.140:18058', '67.220.254.142:18058', 
                '67.220.254.143:18058', '67.220.254.145:18058', '67.220.254.146:18058', '67.220.254.147:18058', '67.220.254.149:18058', 
                '67.220.254.15:18058', '67.220.254.155:18058', '67.220.254.16:18058', '67.220.254.164:18058', '67.220.254.166:18058', 
                '67.220.254.17:18058', '67.220.254.172:18058', '67.220.254.173:18058', '67.220.254.174:18058', '67.220.254.175:18058', 
                '67.220.254.176:18058', '67.220.254.177:18058', '67.220.254.179:18058', '67.220.254.18:18058', '67.220.254.181:18058', 
                '67.220.254.183:18058', '67.220.254.184:18058', '67.220.254.186:18058', '67.220.254.187:18058', '67.220.254.188:18058', 
                '67.220.254.19:18058', '67.220.254.190:18058', '67.220.254.191:18058', '67.220.254.192:18058', '67.220.254.193:18058', 
                '67.220.254.194:18058', '67.220.254.195:18058', '67.220.254.196:18058', '67.220.254.197:18058', '67.220.254.198:18058', 
                '67.220.254.20:18058', '67.220.254.209:18058', '67.220.254.21:18058', '67.220.254.210:18058', '67.220.254.211:18058', 
                '67.220.254.212:18058', '67.220.254.213:18058', '67.220.254.216:18058', '67.220.254.217:18058', '67.220.254.218:18058', 
                '67.220.254.219:18058', '67.220.254.22:18058', '67.220.254.220:18058', '67.220.254.221:18058', '67.220.254.222:18058', 
                '67.220.254.223:18058', '67.220.254.224:18058', '67.220.254.225:18058', '67.220.254.25:18058', '67.220.254.26:18058', 
                '67.220.254.28:18058', '67.220.254.29:18058', '67.220.254.30:18058', '67.220.254.31:18058', '67.220.254.32:18058', 
                '67.220.254.33:18058', '67.220.254.35:18058', '67.220.254.36:18058', '67.220.254.39:18058', '67.220.254.40:18058', 
                '67.220.254.41:18058', '67.220.254.44:18058', '67.220.254.62:18058', '67.220.254.63:18058', '67.220.254.64:18058', 
                '67.220.254.67:18058', '67.220.254.68:18058', '67.220.254.76:18058', '67.220.254.78:18058', '67.220.254.89:18058' ]

proxy_auth = 'Basic ' + base64.encodestring(b'erwin05dec1998:APg28fvK').strip().decode('utf-8')

# from 2captcha.com
API_KEYS = ['368777fb0a6378526d68c88569d730a0', 'c9ed683b19d4b8322a04f481f3b1b0f1', 'aa062166007f6877c77f412eb1725bf5']
# API_KEY = '3fe1c78b19d0c7c7115e679e87cae3c5' # mine

# adidas uses same sitekey for all hmac product pages -> 6LeOnCkTAAAAAK72JqRneJQ2V7GvQvvgzsVr-6kR
# adidas uses same sitekey for all none-hmac products -> 6LdaWw0UAAAAAPB2Dag2Ev9o5Unev3jD5kO-e7FE
global_sitekeys = ['6LeOnCkTAAAAAK72JqRneJQ2V7GvQvvgzsVr-6kR', # hmac product
                   '6LeOnCkTAAAAAK72JqRneJQ2V7GvQvvgzsVr-6kR', # '6LdaWw0UAAAAAPB2Dag2Ev9o5Unev3jD5kO-e7FE', # none-hmac product
                   '6Ldl1BUUAAAAAGluqZ8C1ywfKC_B4xbAQgr47gFG', # yeezy product
                   # '6Lc93RMUAAAAAPMKucaHJk3zfPYxdCCUOgtYqU7J' # yeezy product
                   ]
global_sitekey = '6LeOnCkTAAAAAK72JqRneJQ2V7GvQvvgzsVr-6kR'
# e.g. http://www.adidas.co.uk/dw/shop/v15_6/products/BA7519?client_id=2904a24b-e4b4-4ef7-89a4-2ebd2d175dde&expand=availability%2Cvariations%2Cprices
# stock_check_url = '%sdw/shop/v15_6/products/%s?client_id=2904a24b-e4b4-4ef7-89a4-2ebd2d175dde&expand=availability,variations,prices'
# USA -> http://production-us-adidasgroup.demandware.net/s/adidas-US/dw/shop/v15_6/products/BA8920?client_id=a28c0749-f253-4c41-8bf4-cafdc1ba1df9&expand=availability%2Cvariations%2Cprices
stock_check_url = '%sdw/shop/v15_6/products/%s?client_id=%s&expand=availability,variations,prices'

# Client ID:
client_id_us = 'a28c0749-f253-4c41-8bf4-cafdc1ba1df9'   # 'bb1e6193-3c86-481e-a440-0d818af5f3c8'   # United States
client_id_ca = '5e396c6-5589-425b-be03-774c21a74702'    # Canada
client_id_au = '75e396c6-5589-425b-be03-774c21a74702'   # Australia / New Zealand
client_id_uk = '2904a24b-e4b4-4ef7-89a4-2ebd2d175dde'   # Europe / United Kingdom (UK Sizing)
client_id_eu = '2904a24b-e4b4-4ef7-89a4-2ebd2d175dde'   # Europe / United Kingdom (EU Sizing)

yeezy_dupecaptcha_code = 'AARMFK' # 'x-PrdRt' # 'DhnjhrCA'
yeezy_clientId = 'e355279a-0f17-4caf-a7d4-9211f3562dcc' # '2904a24b-e4b4-4ef7-89a4-2ebd2d175dde' # '2d10d8ab-445f-405b-9275-a92a24a57e9d'
yeezy_sitekey = '6Le4AQgUAAAAAABhHEq7RWQNJwGR_M-6Jni9tgtA' # '6LeOnCkTAAAAAK72JqRneJQ2V7GvQvvgzsVr-6kR'
setcookie = 'HRPYYU' # 'KPDMJU'
yeezy_products = ['CP9652', 'CP9654', 'BB6372', 'CM7828']
# hmac_products = ['S76777', 'BB1234', 'BA7518', 'BA7519', 'CP9652', 'CP9654', 'BY9090']
# captcha_products = ['S76777', 'BB1234', 'BA7518', 'BA7519', 'CP9652', 'CP9654', 'BY9090']
# hmac_products = ['S76777', 'BB1234', 'BA7518', 'BA7519', 'BY9090']
# captcha_products = ['BA9797', 'S76777', 'BB1234', 'BA7518', 'BA7519', 'BY9090']
hmac_products = ['CP9652', 'CP9654']
captcha_products = ['CP9652', 'CP9654', 'BA8143', 'BB6372', 'S31507', 'BA8920', 'BY9089', 'BB2978', 'CM7828']

################# scrapex install guide (refer to https://github.com/valen0214/scrapex) ###############
#  - easy_install https://github.com/valen0214/scrapex/archive/master.zip or
#  - pip install https://github.com/valen0214/scrapex/archive/master.zip

##################################  Variables for country  #########################################
site_name  = 'adidas'
site_url  = 'https://www.adidas.com/'
country_urls = { 'US': {'domain': 'www.adidas.com',    'product_prefix': 'https://www.adidas.com/us/', 'loadsignin_url': 'https://cp.adidas.com/web/eCom/en_US/loadsignin?target=account', 'sso_url': 'https://cp.adidas.com/idp/startSSO.ping', 'ssoCookieCreate_url': 'https://cp.adidas.com/web/ssoCookieCreate?resume=%s&cd=%s', 'ACSsaml2_url': 'https://cp.adidas.com/sp/ACS.saml2', 'ResumeLogin_url': 'https://www.adidas.com/on/demandware.store/Sites-adidas-US-Site/en_US/MyAccount-ResumeLogin', 'addproduct_url': 'https://www.adidas.com/on/demandware.store/Sites-adidas-US-Site/en_US/Cart-MiniAddProduct',    'checkout_url': 'https://www.adidas.com/us/delivery-start'},
                 'CA': {'domain': 'www.adidas.ca',     'product_prefix': 'https://www.adidas.ca/en/',  'loadsignin_url': 'https://cp.adidas.ca/web/eCom/en_CA/loadsignin?target=account',  'addproduct_url': 'https://www.adidas.ca/on/demandware.store/Sites-adidas-CA-Site/en_CA/Cart-MiniAddProduct',     'checkout_url': 'https://www.adidas.ca/on/demandware.store/Sites-adidas-CA-Site/en_CA/CODelivery-Start'},
                 'IT': {'domain': 'www.adidas.it',     'product_prefix': 'https://www.adidas.it/',     'loadsignin_url': 'https://cp.adidas.it/web/eCom/it_IT/loadsignin?target=account',  'sso_url': 'https://cp.adidas.it/idp/startSSO.ping',  'ssoCookieCreate_url': 'https://cp.adidas.it/web/ssoCookieCreate?resume=%s&cd=%s',  'ACSsaml2_url': 'https://cp.adidas.it/sp/ACS.saml2',  'ResumeLogin_url': 'https://www.adidas.it/on/demandware.store/Sites-adidas-IT-Site/it_IT/MyAccount-ResumeLogin',  'addproduct_url': 'https://www.adidas.it/on/demandware.store/Sites-adidas-IT-Site/it_IT/Cart-MiniAddProduct',     'checkout_url': 'https://www.adidas.it/on/demandware.store/Sites-adidas-IT-Site/it_IT/COShipping-Show'},
                 'FR': {'domain': 'www.adidas.fr',     'product_prefix': 'https://www.adidas.fr/',     'loadsignin_url': 'https://cp.adidas.fr/web/eCom/fr_FR/loadsignin?target=account',  'sso_url': 'https://cp.adidas.fr/idp/startSSO.ping',  'ssoCookieCreate_url': 'https://cp.adidas.fr/web/ssoCookieCreate?resume=%s&cd=%s',  'ACSsaml2_url': 'https://cp.adidas.fr/sp/ACS.saml2',  'ResumeLogin_url': 'https://www.adidas.fr/on/demandware.store/Sites-adidas-FR-Site/fr_FR/MyAccount-ResumeLogin',  'addproduct_url': 'https://www.adidas.fr/on/demandware.store/Sites-adidas-FR-Site/fr_FR/Cart-MiniAddProduct',     'checkout_url': 'https://www.adidas.fr/on/demandware.store/Sites-adidas-FR-Site/fr_FR/COShipping-Show'},
                 'DE': {'domain': 'www.adidas.de',     'product_prefix': 'https://www.adidas.de/',     'loadsignin_url': 'https://cp.adidas.de/web/eCom/de_DE/loadsignin?target=account',  'sso_url': 'https://cp.adidas.de/idp/startSSO.ping',  'ssoCookieCreate_url': 'https://cp.adidas.de/web/ssoCookieCreate?resume=%s&cd=%s',  'ACSsaml2_url': 'https://cp.adidas.de/sp/ACS.saml2',  'ResumeLogin_url': 'https://www.adidas.de/on/demandware.store/Sites-adidas-DE-Site/de_DE/MyAccount-ResumeLogin',  'addproduct_url': 'https://www.adidas.de/on/demandware.store/Sites-adidas-DE-Site/de_DE/Cart-MiniAddProduct',     'checkout_url': 'https://www.adidas.de/on/demandware.store/Sites-adidas-DE-Site/de_DE/COShipping-Show'},
                 'AU': {'domain': 'www.adidas.com.au', 'product_prefix': 'https://www.adidas.com.au/', 'loadsignin_url': 'https://cp.adidas.com.au/web/eCom/en_AU/loadsignin?target=account', 'addproduct_url': 'https://www.adidas.com.au/on/demandware.store/Sites-adidas-AU-Site/en_AU/Cart-MiniAddProduct', 'checkout_url': 'https://www.adidas.com.au/on/demandware.store/Sites-adidas-AU-Site/en_AU/CODelivery-Start'},
                 'BE': {'domain': 'www.adidas.be',     'product_prefix': 'https://www.adidas.be/',     'loadsignin_url': 'https://cp.adidas.be/web/eCom/fr_BE/loadsignin?target=account',  'sso_url': 'https://cp.adidas.be/idp/startSSO.ping',  'ssoCookieCreate_url': 'https://cp.adidas.be/web/ssoCookieCreate?resume=%s&cd=%s',  'ACSsaml2_url': 'https://cp.adidas.be/sp/ACS.saml2',  'ResumeLogin_url': 'https://www.adidas.be/on/demandware.store/Sites-adidas-BE-Site/fr_BE/MyAccount-ResumeLogin',  'addproduct_url': 'https://www.adidas.be/on/demandware.store/Sites-adidas-BE-Site/fr_BE/Cart-MiniAddProduct',     'checkout_url': 'https://www.adidas.be/on/demandware.store/Sites-adidas-BE-Site/fr_BE/COShipping-Show'},
                 'RU': {'domain': 'www.adidas.ru',     'product_prefix': 'https://www.adidas.ru/',     'loadsignin_url': 'https://cp.adidas.ru/web/eCom/ru_RU/loadsignin?target=account',  'addproduct_url': 'https://www.adidas.ru/on/demandware.store/Sites-adidas-RU-Site/ru_RU/Cart-MiniAddProduct',     'checkout_url': 'https://www.adidas.ru/on/demandware.store/Sites-adidas-RU-Site/ru_RU/CODelivery-Start'},
                 'GB': {'domain': 'www.adidas.co.uk',  'product_prefix': 'https://www.adidas.co.uk/',  'loadsignin_url': 'https://cp.adidas.co.uk/web/eCom/en_GB/loadsignin?target=account', 'sso_url': 'https://cp.adidas.co.uk/idp/startSSO.ping', 'ssoCookieCreate_url': 'https://cp.adidas.co.uk/web/ssoCookieCreate?resume=%s&cd=%s', 'ACSsaml2_url': 'https://cp.adidas.co.uk/sp/ACS.saml2', 'ResumeLogin_url': 'https://www.adidas.co.uk/on/demandware.store/Sites-adidas-GB-Site/en_GB/MyAccount-ResumeLogin', 'addproduct_url': 'https://www.adidas.co.uk/on/demandware.store/Sites-adidas-GB-Site/en_GB/Cart-MiniAddProduct',  'checkout_url': 'https://www.adidas.co.uk/on/demandware.store/Sites-adidas-GB-Site/en_GB/COShipping-Show'},
                }

#####################################    Product info   ############################################
# csv header sequence is like product_id, size, quantity
# product_id = 'BB3045'
# size       = '6'
# quantity   = 3

# product_list = []

#####################################    Buyer info    ##############################################
# csv header sequence is like first_name, last_name, billing_address_1, billing_address_2, billing_city, billing_state_abbrv, billing_country_abbrv, billing_zip, phone_number, shipping_address_1, shipping_address_2, shipping_city, shipping_state_abbrv, shipping_state, shipping_zip, email, card_cvv, card_exp_month, card_number, card_exp_year
# first_name            = 'First'
# last_name             = 'Last'
# billing_address_1     = '1121'
# billing_address_2     = 'New Hampshire Avenue'
# billing_city          = 'Washington'
# billing_state_abbrv   = 'DC'
# billing_country_abbrv = 'USA'
# billing_zip           = '20037'
# phone_number          = '2023572020'
# shipping_address_1    = '1121'
# shipping_address_2    = 'New Hampshire Avenue'
# shipping_city         = 'Washington'
# shipping_state_abbrv  = 'DC'
# shipping_state        = 'District of Columbia'
# shipping_zip          = '20037'
# email                 = 'rec@mail.com'
# password              = 'Thanks'

# card_cvv       = ''
# card_exp_month = ''
# card_number    = ''
# card_exp_year  = ''

log_s = Scraper(use_cache=False, retries=3, timeout=30, log_file='log_%s.txt' % (time.strftime("%b%d%Y%H%M%S", time.gmtime())))
g_logger = log_s.logger

def bot_info(logger, msg, pid):
    logger.info(time.strftime("%b %d %Y %H:%M:%S", time.gmtime()) + ': pid -> %d -> %s' % (pid, msg))

def get_APIKEY():
    rand_index = randint(0, len(API_KEYS) - 1)
    return API_KEYS[rand_index]

# Select a buyer randomly.
# All info about buyer are saved into global variables.
def select_buyer(logger, csv_filename='buyer.csv', p_country='', p_name='', pid=0):
    bot_info(logger, 'Selecting buyer...', pid)
    bot_info(logger, 'Buyer condition -> Country: %s, Name: %s' %(p_country, p_name), pid)
    p_country = p_country.lower()
    p_name = p_name.lower()

    buyer_list = []
    with open(csv_filename, 'r') as f:
        buyer_list = list(csv.reader(f))

    del buyer_list[0]   # remove head line

    buyer_counter = 0
    while ( buyer_counter < len(buyer_list) ):
        country_matching = False
        if ( p_country != '' ):
            if ( any(p_country in field.lower() for field in buyer_list[buyer_counter]) ):
                country_matching = True
        else:
            country_matching = True

        name_matching = False
        if ( p_name != '' ):
            if ( any(p_name in field.lower() for field in buyer_list[buyer_counter]) ):
                name_matching = True
        else:
            name_matching = True

        if ( country_matching and name_matching ):
            buyer_counter = buyer_counter + 1
            continue
        else:
            del buyer_list[buyer_counter]

    buyer_count = len(buyer_list)

    bot_info(logger, 'Number of matching buyers: %d' % buyer_count, pid)
    if ( buyer_count == 0 ):
        return
    rand_index = randint(0, buyer_count - 1)

    for index_row, data_in_row in enumerate(buyer_list):
        if ( index_row == rand_index ):
            # first_name, last_name, billing_address_1, billing_address_2, billing_city, billing_state_abbrv, billing_country_abbrv, billing_zip, phone_number, shipping_address_1, shipping_address_2, shipping_city, shipping_state_abbrv, shipping_state, shipping_zip, email, password, card_cvv, card_exp_month, card_number, card_exp_year = data_in_row
            bot_info(logger, 'Selected buyer -> {}'.format(data_in_row), pid)
            return data_in_row

# Read all products, params are optional.
def read_products(logger, csv_filename='product.csv', p_product_id='', p_size='', p_sizeval='', p_quantity=0, pid=0):
    bot_info(logger, 'Reading products... -> product_id: %s, size: %s, size_val: %s, quantity: %d' % (p_product_id, p_size, p_sizeval, p_quantity), pid)
    with open(csv_filename, 'r') as f:
        product_list = list(csv.reader(f))

    del product_list[0]   # remove head line

    bot_info(logger, str(product_list), pid)
    return product_list

# Get the gceeqs from http://www.adidashmac.com/hmac/#hmac
def get_hmac_from_adidashmac(s, logger, pid):
    try:
        doc = s.load('http://www.adidashmac.com/hmac/#hmac', post={'dropdown': 'US', 'KCDNocKwIM2cypYgzaHCsCk': ''})
        gceeqs = doc.x('//textarea[@id="exampleTextarea"]/text()').strip()
        bot_info(logger, 'Getting hmac from adidashmac -> gceeqs: %s' % gceeqs, pid)
    except:
        bot_info(logger, 'Getting hmac from adidashmac failed.', pid)
        return False
    return gceeqs

# load hmac from various sites
def load_hmac(s, logger, product_url, product_id, pid):
    bot_info(logger, '%s -> Loading hmac...' % product_id, pid)
    domain = '{uri.scheme}://{uri.netloc}/'.format(uri=urlparse(product_url))
    gceeqs = ''
    # doc = s.load('http://www.adidas.com/yeezy', headers={'User-Agent': UserAgent}, merge_headers=True)
    # doc = s.load('http://www.adidas.com/us/apps/yeezy', headers={'User-Agent': UserAgent}, merge_headers=True)
    # bot_info(logger, doc.status.final_url, pid)
    gceeqs = exist_hmac(s, logger, product_id, pid)
    if gceeqs:
        bot_info(logger, 'load hmac from %s' % doc.status.final_url, pid)
        return gceeqs
    else:
        for hmac_product in hmac_products:
            if ( product_id != hmac_product ):
                doc = s.load(domain + hmac_product + '.html')
                bot_info(logger, doc.status.final_url, pid)
                gceeqs = exist_hmac(s, logger, hmac_product, pid)
                if ( gceeqs ):
                    bot_info(logger, 'load hmac from %s' % doc.status.final_url, pid)
                    return gceeqs
                else:
                    doc = s.load(domain + 'dis/dw/image/' + hmac_product + '.html')
                    bot_info(logger, doc.status.final_url, pid)
                    gceeqs = exist_hmac(s, logger, hmac_product, pid)
                    if ( gceeqs ):
                        bot_info(logger, 'load hmac from %s' % doc.status.final_url, pid)
                        return gceeqs
            else:
                # 'http://www.adidas.fr/dis/dw/image/BY9090.html'
                doc = s.load(domain + 'dis/dw/image/' + hmac_product + '.html')
                bot_info(logger, doc.status.final_url, pid)
                gceeqs = exist_hmac(s, logger, hmac_product, pid)
                if ( gceeqs ):
                    bot_info(logger, 'load hmac from %s' % doc.status.final_url, pid)
                    return gceeqs
    # gceeqs = get_hmac_from_adidashmac(s, logger, pid)
    # if ( (gceeqs == '') or (gceeqs == False) ):
    #     return False
    # else:
    #     return gceeqs
    return False

# Add to cart each product directly without going product page.
def add_to_cart_directly(s, logger, product_url, product_id, size, size_val, quantity, selected_country, pid):
    # e.g. get http://www.adidas.fr/ from http://www.adidas.fr/S76777.html
    domain = '{uri.scheme}://{uri.netloc}/'.format(uri=urlparse(product_url))

    product_json = None
    product_html = ''
    try:
        if 'https://www.adidas.com/us/' in product_url:
            url = stock_check_url % ('http://production-us-adidasgroup.demandware.net/s/adidas-US/', product_id, client_id_us)
        else:
            url = stock_check_url % (domain, product_id, client_id_uk)
        bot_info(logger, 'Checking stock for %s -> %s' % (product_id, url), pid)
        # product_html = s.load_html(stock_check_url % (domain, product_id), headers={'User-Agent': UserAgent, 'Cookie': ''}, merge_headers=True)
        product_html = s.load_html(url, headers={'User-Agent': UserAgent}, merge_headers=True)
        product_json = json.loads(product_html)
        # product_json = s.load_json(stock_check_url % (domain, product_id))
    except:
        bot_info(logger, 'Checking stock for %s failed. -> %s' % (product_id, product_html), pid)
        return False

    if ( (product_json is None) or ('variants' not in product_json) ):
        return False

    for variant in product_json['variants']:
        if ( variant['product_id'] == size_val ):
            if ( (variant['orderable'] == 'false') or (variant['orderable'] == False) ):
                bot_info(logger,  '{} unavailable -> product_id: {}, size: {}, quantity: {}'.format(size_val, product_id, size_val, quantity), pid)
            else:
                gceeqs = ''
                KPDMJU = ''

                start_url = product_url
                doc = s.load(start_url, headers={'User-Agent': UserAgent}, merge_headers=True, use_cookie=True)
                # doc = s.load(start_url, headers={'Cookie': 'gceeqs=%s' % gceeqs}, merge_headers=True, use_cookie=True)
                bot_info(logger, 'loading %s' % doc.status.final_url, pid)

                gceeqs = exist_hmac(s, logger, product_id, pid)

                # hmac removed
                # getting hmac from others
                if ( (product_id in hmac_products) and ((gceeqs == '') or (gceeqs == False)) ):
                    gceeqs = load_hmac(s, logger, product_url, product_id, pid)
                    if (gceeqs == '') or (gceeqs == False):
                        return False
                    # bot_info(logger, '%s -> hmac removed. Getting from others...' % product_id, pid)
                    # doc = s.load('http://www.adidas.com/yeezy', headers={'User-Agent': UserAgent}, merge_headers=True, use_cookie=True)
                    # gceeqs = exist_hmac(s, logger, product_id, pid)
                    # if gceeqs:
                    #     pass
                    # else:
                    #     for hmac_product in hmac_products:
                    #         if ( product_id != hmac_product ):
                    #             doc = s.load(domain + hmac_product + '.html')
                    #             gceeqs = exist_hmac(s, logger, hmac_product, pid)
                    #             if ( gceeqs ):
                    #                 break
                    #             else:
                    #                 doc = s.load(domain + 'dis/dw/image/' + hmac_product + '.html')
                    #                 gceeqs = exist_hmac(s, logger, hmac_product, pid)
                    #                 if ( gceeqs ):
                    #                     break
                    #         else:
                    #             # 'http://www.adidas.fr/dis/dw/image/BY9090.html'
                    #             doc = s.load(domain + 'dis/dw/image/' + hmac_product + '.html')
                    #             gceeqs = exist_hmac(s, logger, hmac_product, pid)
                    #             if ( gceeqs ):
                    #                 break

                # if ( (product_id in hmac_products) and ((gceeqs == '') or (gceeqs == False)) ):
                #     gceeqs = get_hmac_from_adidashmac(s, logger, pid)
                #     if ( (gceeqs == '') or (gceeqs == False) ):
                #         return False

                bot_info(logger,  'Adding to cart... -> product_id: %s, size: %s, quantity: %s' % (product_id, size_val, quantity), pid)
                payload = {
                                      'layer': 'Add+To+Bag+overlay',
                                        'pid': size_val,
                                   'Quantity': quantity,
                                  'masterPid': product_id,
                     'sessionSelectedStoreID': 'null',
                                       'ajax': 'true',
                }
                if ( product_id in captcha_products ):
                    if product_id in yeezy_products:
                        site_key = yeezy_sitekey      # global_sitekeys[2] # yeezy product
                    elif product_id in hmac_products:
                        site_key = global_sitekeys[0] # hmac product
                    else:
                        site_key = global_sitekeys[1] # none-hmac product
                    # site_key = global_sitekey
                    bot_info(logger, 'Processing captcha...', pid)
                    bot_info(logger, 'site_key -> %s' % site_key, pid)
                    while ( True ):
                        API_KEY = get_APIKEY()
                        bot_info(logger, 'API_KEY -> %s' % API_KEY, pid)

                        # Post site key to 2captcha to get captcha ID
                        req_params = {    'key': API_KEY,
                                       'method': 'userrecaptcha', 
                                    'googlekey': site_key, 
                                      'pageurl': product_url }

                        captcha_id = ''
                        try:
                            captcha_id = s.load_html(url='http://2captcha.com/in.php?key={}&method=userrecaptcha&googlekey={}&pageurl={}'.format(API_KEY, site_key, product_url), post=req_params).split('|')[1]
                            bot_info(logger, 'captcha_id -> %s' % captcha_id, pid)
                        except:
                            bot_info(logger, 'Seems that your 2Captcha balance is low. Please put some budget on your account in order to continue solving CAPTCHAS.', pid)
                            return False

                        # Parse gresponse from 2captcha response
                        recaptcha_answer = s.load_html(url='http://2captcha.com/res.php?key={}&action=get&id={}'.format(API_KEY, captcha_id))
                        while ( 'CAPCHA_NOT_READY' in recaptcha_answer ):
                            sleep(5)
                            recaptcha_answer = s.load_html(url='http://2captcha.com/res.php?key={}&action=get&id={}'.format(API_KEY, captcha_id))
                        try:
                            recaptcha_answer = recaptcha_answer.split('|')[1]
                            bot_info(logger, 'recaptcha_answer -> %s' % recaptcha_answer, pid)

                            payload = {
                                                  'layer': 'Add+To+Bag+overlay',
                                                    'pid': size_val,
                                               'Quantity': quantity,
                                   'g-recaptcha-response': recaptcha_answer,
                                              'masterPid': product_id,
                                'sessionSelectedStoreID' : 'null',
                                                   'ajax': 'true',
                            }
                            break
                        except:
                            pass
                # url = site_url + 'on/demandware.store/Sites-adidas-US-Site/en_US/Cart-MiniAddProduct'
                url = selected_country['addproduct_url']

                if ( product_id in yeezy_products ):
                    payload[yeezy_dupecaptcha_code] = payload['g-recaptcha-response']
                    url = url + '?clientId=' + yeezy_clientId
                # s.clear_cookies()
                # doc = s.load_html(url, post=payload, headers={'X-Requested-With': 'XMLHttpRequest', 'Cookie': 'gceeqs=%s;KPDMJU=true' % gceeqs}, merge_headers=True, use_cookie=True, ajax=True)
                doc = s.load_html( url, post=payload, headers={'User-Agent': UserAgent, 'X-Requested-With': 'XMLHttpRequest'}, merge_headers=True, use_cookie=True, ajax=True )
                # if (gceeqs == '') or (gceeqs == False):
                #     doc = s.load_html( url, post=payload, headers={'User-Agent': UserAgent, 'X-Requested-With': 'XMLHttpRequest'}, merge_headers=True, use_cookie=True, ajax=True )
                # else:
                #     doc = s.load_html( url, post=payload, headers={'User-Agent': UserAgent, 'X-Requested-With': 'XMLHttpRequest', 'Cookie': 'gceeqs=%s' % gceeqs}, merge_headers=True, use_cookie=True, ajax=True )
                # doc = s.load_html( url, post=payload, headers={'X-Requested-With': 'XMLHttpRequest', 'Proxy-Authorization': proxy_auth}, merge_headers=True, use_cookie=True, ajax=True, meta={'proxy': 'https://' + proxy_addr}, use_proxy=True )
                try:
                    # When fail, it responds as json
                    resJson = json.loads(doc)
                    if ( resJson['success'] == 'true' ):
                        bot_info(logger, 'Adding to cart success! -> product_id: %s, size: %s, quantity: %s' % (product_id, size_val, quantity), pid)
                        return True
                    else:
                        bot_info(logger, 'Adding to cart failed! (resJson[\'error\']: %s) -> product_id: %s, size: %s, quantity: %s' % (resJson['error'], product_id, size_val, quantity), pid)
                        return False
                except:
                    if ( (doc is None) or (doc.strip() == '') ):
                        bot_info(logger, 'Adding to cart failed! (doc.status.code: %s, %s) -> product_id: %s, size: %s, quantity: %s' % (str(doc.status.code), 'empty', product_id, size_val, quantity), pid)
                        return False
                    else:
                        bot_info(logger, 'Adding to cart success! -> product_id: %s, size: %s, quantity: %s' % (product_id, size_val, quantity), pid)
                        return True
    return False

def exist_hmac(s, logger, product_id, pid):
    for cookie in s.client.opener.cj:
        if ( cookie.name == 'gceeqs' ):
            bot_info(logger, '%s hmac gceeqs -> ' % product_id + cookie.value, pid)
            return cookie.value
    return False

# Add to cart each product.
def add_to_cart(s, logger, product_url, product_id, size, quantity, selected_country, pid):
    gceeqs = ''
    KPDMJU = ''

    if product_id in hmac_products:
        gceeqs = load_hmac(s, logger, product_url, product_id, pid)
    start_url = product_url
    # gceeqs = get_hmac_from_adidashmac(s, logger, pid)
    # if ( (gceeqs == '') or (gceeqs == False) ):
    #     doc = s.load(start_url)
    # else:
    #     doc = s.load(start_url, headers={'Cookie': 'gceeqs=%s' % gceeqs}, merge_headers=True, use_cookie=True)
    # doc = s.load(start_url, headers={'User-Agent': UserAgent, 'Cookie': ''}, merge_headers=True)
    doc = s.load(start_url, headers={'User-Agent': UserAgent}, merge_headers=True)
    bot_info(logger, 'loading %s' % doc.status.final_url, pid)
    gceeqs = exist_hmac(s, logger, product_id, pid)

    splash_on = False
    while ( True ):
        if ( doc.status.code != 200):
            bot_info(logger, product_id + ' -> ' + str(doc.status), pid)
            return False
        bot_info(logger, doc.status.final_url, pid)
        if (doc.status.final_url.strip() != start_url.strip()) and (product_id in doc.status.final_url.strip()):
            product_url = doc.status.final_url
            break
        if product_id in yeezy_products:
            if ('/apps/yeezy' in doc.status.final_url) or ('/blanc' in doc.status.final_url) or (re.search('blanc$', doc.status.final_url, re.M|re.I|re.S)):
                bot_info(logger,  'All sold out!', pid)
                return False
        else:
            if (doc.status.final_url.strip() != start_url.strip()):
                bot_info(logger,  'All sold out!', pid)
                return False                
        splash_on = True
        bot_info(logger, 'Splash is on. Retrying after 5 seconds... -> %s' % start_url, pid)
        # return False
        sleep(5)
        # Cookie(version, name, value, port, port_specified, domain, domain_specified, domain_initial_dot, path, path_specified, secure, discard, comment, comment_url, rest)
        s.client.opener.cj.set_cookie(Cookie(None, setcookie, 'true', '', '', '', None, None, '', None, False, False, '', None, None, None))
        doc = s.load(start_url, headers={'User-Agent': UserAgent}, merge_headers=True, use_cookie=True)
        # doc = s.load(start_url, headers={'User-Agent': UserAgent, 'Cookie': setcookie}, merge_headers=True, use_cookie=True)
        # doc = s.load(start_url, headers={'User-Agent': UserAgent, 'Cookie': 'KPDMJU=true'}, merge_headers=True, use_cookie=True)
        # s.clear_cookies()
        # if ( (gceeqs == '') or (gceeqs == False) ):
        #     doc = s.load(start_url, headers={'Cookie': 'KPDMJU=true'}, merge_headers=True, use_cookie=True)
        # else:
        #     doc = s.load(start_url, headers={'Cookie': 'gceeqs=%s;KPDMJU=true' % gceeqs}, merge_headers=True, use_cookie=True)
    if ( splash_on ):
        bot_info(logger, 'Get through splash -> %s' % product_url, pid)
    else:
        bot_info(logger, 'product_url -> %s' % product_url, pid)

    url = product_url

    # check if sizes are sold out, if not, find size value
    size_val = 'null'
    try:
        for sz in doc.q('//select[@name="pid"]//option'):
            if sz.x('text()').strip() == size:
                # bot_info(logger, sz.x('text()').strip() + ', ' + sz.x('@data-status').strip() + ': ' + size)
                size_val = sz.x('@value')
                quantity_available = min(int(float(sz.x('@data-maxavailable'))), int(float(sz.x('@data-maxorderqty'))))
                quantity = str(min(int(quantity), quantity_available))
                break
    except:
        bot_info(logger,  'All sold out!', pid)
        return False

    if ( (size_val == 'null') or (quantity == '') or (quantity == '0') ):
        bot_info(logger,  '{} unavailable -> product_id: {}, size: {}, quantity: {}'.format(size, product_id, size, quantity), pid)
        return False

    bot_info(logger,  'Adding to cart... -> product_id: %s, size: %s, quantity: %s' % (product_id, size, quantity), pid)
    payload = {
                          'layer': 'Add+To+Bag+overlay',
                            'pid': size_val,
                       'Quantity': quantity,
                      'masterPid': product_id,
         'sessionSelectedStoreID': 'null',
                           'ajax': 'true',
    }

    ################################   get sitekey   ##################################
    # e.g. <div class="g-recaptcha" data-sitekey="6LdaWw0UAAAAAPB2Dag2Ev9o5Unev3jD5kO-e7FE"></div>
    site_key = doc.x('//div[@class="g-recaptcha"]/@data-sitekey')
    # There is no sitekey in case of not appearing of captcha.
    if ( site_key and (site_key != '') ):
        bot_info(logger, 'Processing captcha...', pid)
        bot_info(logger, 'site_key -> %s' % site_key, pid)
        esc_pressed = False
        while ( True ):
            if ( esc_pressed == True ):
                break
            # if msvcrt.kbhit():
            #     if ord(msvcrt.getch()) == 27:
            #         break
            API_KEY = get_APIKEY()

            bot_info(logger, 'API_KEY -> %s' % API_KEY, pid)
            # Post site key to 2captcha to get captcha ID
            req_params = {    'key': API_KEY,
                           'method': 'userrecaptcha', 
                        'googlekey': site_key, 
                          'pageurl': product_url }

            captcha_id = ''
            try:
                captcha_id = s.load_html(url='http://2captcha.com/in.php?key={}&method=userrecaptcha&googlekey={}&pageurl={}'.format(API_KEY, site_key, url), post=req_params).split('|')[1]
                bot_info(logger, 'captcha_id -> %s' % captcha_id, pid)
            except:
                bot_info(logger, 'Seems that your 2Captcha balance is low. Please put some budget on your account in order to continue solving CAPTCHAS.', pid)
                return False

            # Parse gresponse from 2captcha response
            recaptcha_answer = s.load_html(url='http://2captcha.com/res.php?key={}&action=get&id={}'.format(API_KEY, captcha_id))
            while ( 'CAPCHA_NOT_READY' in recaptcha_answer ):
                sleep(5)
                recaptcha_answer = s.load_html(url='http://2captcha.com/res.php?key={}&action=get&id={}'.format(API_KEY, captcha_id))
                # if (msvcrt.kbhit()):
                #     if (ord(msvcrt.getch()) == 27):
                #         esc_pressed = True
                #         break
                # bot_info(logger, 'recaptcha_answer -> %s' % recaptcha_answer)
            try:
                recaptcha_answer = recaptcha_answer.split('|')[1]
                bot_info(logger, 'recaptcha_answer -> %s' % recaptcha_answer, pid)

                payload = {
                                      'layer': 'Add+To+Bag+overlay',
                                        'pid': size_val,
                                   'Quantity': quantity,
                       'g-recaptcha-response': recaptcha_answer,
                                  'masterPid': product_id,
                    'sessionSelectedStoreID' : 'null',
                                       'ajax': 'true',
                }
                break
            except:
                pass

    if size_val != 'null':
        # url = site_url + 'on/demandware.store/Sites-adidas-US-Site/en_US/Cart-MiniAddProduct'
        url = selected_country['addproduct_url']
        if ( product_id in yeezy_products ):
            payload[yeezy_dupecaptcha_code] = payload['g-recaptcha-response']
            yeezy_url = doc.x('//form[@id="flashproductform"]/@data-desktop')
            if (yeezy_url is None) or (yeezy_url == ''):
                url = url + '?clientId=' + yeezy_clientId
            else:
                url = yeezy_url

        gceeqs_self = exist_hmac(s, logger, product_id, pid)
        if (gceeqs_self == '') or (gceeqs_self == False):
            # <img src="https://m.adidas.ca/en/test_assets/73146813.gif?b=exp=1486834852~acl=*~hmac=1faff39d2a92db54231689cddb42a3a4872c884217cd4517b8c031004d6cd830" class="hidden">
            gceeqs_self = doc.x('//img[contains(@src, "hmac")]/@src')
            if gceeqs_self:
                gceeqs_self = 'exp=' + gceeqs_self.split('exp=')[1]
                # Cookie(version, name, value, port, port_specified, domain, domain_specified, domain_initial_dot, path, path_specified, secure, discard, comment, comment_url, rest)
                s.client.opener.cj.set_cookie(Cookie(None, 'gceeqs', gceeqs_self, '', '', '', None, None, '', None, False, False, '', None, None, None))

        # s.clear_cookies()
        # doc = s.load_html(url, post=payload, headers={'X-Requested-With': 'XMLHttpRequest', 'Cookie': 'gceeqs=%s;KPDMJU=true' % gceeqs}, merge_headers=True, use_cookie=True, ajax=True)
        doc = s.load_html(url, post=payload, headers={'User-Agent': UserAgent, 'X-Requested-With': 'XMLHttpRequest'}, merge_headers=True, use_cookie=True, ajax=True )
        # if ( (gceeqs_self == '') or (gceeqs_self == False) ):
        #     if ( (gceeqs == '') or (gceeqs == False) ):
        #         doc = s.load_html(url, post=payload, headers={'X-Requested-With': 'XMLHttpRequest'}, merge_headers=True, use_cookie=True, ajax=True )
        #     else:
        #         doc = s.load_html(url, post=payload, headers={'X-Requested-With': 'XMLHttpRequest', 'Cookie': 'gceeqs=%s' % gceeqs}, merge_headers=True, use_cookie=True, ajax=True)
        # else:
        #     doc = s.load_html( url, post=payload, headers={'X-Requested-With': 'XMLHttpRequest'}, merge_headers=True, use_cookie=True, ajax=True )
        # doc = s.load_html( url, post=payload, headers={'X-Requested-With': 'XMLHttpRequest', 'Proxy-Authorization': proxy_auth}, merge_headers=True, use_cookie=True, ajax=True, meta={'proxy': 'https://' + proxy_addr}, use_proxy=True )
        
        # bot_info(logger, doc)
        # return False
        try:
            # When fail, it responds as json
            resJson = json.loads(doc)
            # bot_info(logger, resJson)
            if ( resJson['success'] == 'true' ):
            # if doc.status.code == 200:
                bot_info(logger, 'Adding to cart success! -> product_id: %s, size: %s, quantity: %s' % (product_id, size, quantity), pid)
                return True
            else:
                bot_info(logger, 'Adding to cart failed! (resJson[\'error\']: %s) -> product_id: %s, size: %s, quantity: %s' % (resJson['error'], product_id, size, quantity), pid)
                return False
        except:
            # bot_info(logger, 'Adding to cart failed! (%s) -> product_id: %s, size: %s, quantity: %s' % (doc, product_id, size, quantity), pid)
            # return False
            if ( (doc is None) or (doc.strip() == '') ):
                bot_info(logger, 'Adding to cart failed! (doc.status.code: %s, %s) -> product_id: %s, size: %s, quantity: %s' % (str(doc.status.code), 'empty', product_id, size, quantity), pid)
                return False
            else:
                # bot_info(logger, 'Adding to cart success! -> product_id: %s, size: %s, quantity: %s, response: %s' % (product_id, size, quantity, doc), pid)
                bot_info(logger, 'Adding to cart success! -> product_id: %s, size: %s, quantity: %s' % (product_id, size, quantity), pid)
                return True

    else:
        bot_info(logger,  '{} unavailable -> product_id: {}, size: {}, quantity: {}'.format(size, product_id, size, quantity), pid)
        return False

def send_notify_email(logger, mail_addr, password, content, pid):
    from_mail = 'jeanmarc.romain@mail.ru'
    from_mail_pw = 'Yesnayah141103'
    content = 'Please check your cart. [' + content + ']'

    msg = MIMEText(content.encode('utf-8'))
    msg['Subject'] = 'Notification from AdidasBot'
    msg['From'] = from_mail
    msg['To'] = mail_addr

    bot_info(logger, 'Sending email to %s -> Subject: %s, Content: %s' % (msg['To'], msg['Subject'], content), pid)

    server = ''
    if ( '@gmail.com' in from_mail ):
        server = smtplib.SMTP('smtp.gmail.com:587')
    elif ( '@hotmail.com' in from_mail ):
        server = smtplib.SMTP('smtp.live.com', 587)
    elif ( '@mail.ru' in from_mail ):
        server = smtplib.SMTP('smtp.mail.ru', 587)
    else:
        bot_info(logger, 'Sending email to %s failed. [None of e-mail provider]' % msg['To'], pid)
        return False

    try:
        server.ehlo()
        server.starttls()
        server.login(msg['From'], from_mail_pw)
        server.sendmail(msg['From'], msg['To'], msg.as_string())
        server.sendmail(msg['From'], 'jiajia0214@mail.ru', msg.as_string())
        server.quit()
    except Exception, e:
        bot_info(logger, 'Sending email to %s failed. [%s]' % (msg['To'], str(e)), pid)
        return False

    bot_info(logger, 'Sending email to %s success!' % msg['To'], pid)
    return True

def checkout(s, logger, checkout_url, p_buyer, p_domain, pid):
    bot_info(logger, 'Checking out... -> %s %s' % (p_buyer['first_name'], p_buyer['last_name']), pid)
    bot_info(logger, 'checkout_url -> %s' % checkout_url, pid)
    headers = {
                   'Host': p_domain,
             'User-Agent': UserAgent,
                 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
                # 'Referer': product_url,
    }

    doc_checkout = s.load(checkout_url, headers=headers)

    ############################################# checking all products added #########################################
    products_number = doc_checkout.x('//div[@class="cart-widget-block"]/div/div[@class="cart-widget-label"]/text()').strip()
    total_price = doc_checkout.x('//div[@class="cart-widget-mainblock cart-products-payment_total"]/div/div[@class="cart-widget-value"]/text()').strip()

    checkout_msg = '%s %s -> products_number: %s, total_price: %s' % (p_buyer['first_name'], p_buyer['last_name'], products_number, total_price)
    bot_info(logger, checkout_msg, pid)

    send_notify_email(logger, p_buyer['email'], p_buyer['password'], checkout_msg, pid)

    return

    # if ( p_buyer['billing_country_abbrv'] == 'France' ):
        # POST /on/demandware.store/Sites-adidas-FR-Site/fr_FR/COShipping-Submit HTTP/1.1
        # coshpping_submit_url = doc_checkout.x('//form[@id="shippingForm"]/@action')
        # bot_info(logger, 'coshpping_submit_url -> ' + coshpping_submit_url)

        # dwfrm_shipping_selectedDeliveryMethodID  = doc_checkout.q('//input[contains(@name, "dwfrm_shipping_selectedDeliveryMethodID")]')[0]
        # bot_info(logger, dwfrm_shipping_selectedDeliveryMethodID.x('@name') + ' -> shiptoaddress')
        # dwfrm_shipping_selectedShippingType = doc_checkout.q('//input[contains(@name, "dwfrm_shipping_selectedShippingType")]')[0]
        # bot_info(logger, dwfrm_shipping_selectedShippingType.x('@name') + ' -> shiptoaddress')

        # dwfrm_shipping_shiptoaddress_shippingAddress_firstName = doc_checkout.x('//input[@id="dwfrm_shipping_shiptoaddress_shippingAddress_firstName"]/@name')
        # bot_info(logger, dwfrm_shipping_shiptoaddress_shippingAddress_firstName + ' -> ' + p_buyer['first_name'])
        # dwfrm_shipping_shiptoaddress_shippingAddress_lastName = doc_checkout.x('//input[@id="dwfrm_shipping_shiptoaddress_shippingAddress_lastName"]/@name')
        # bot_info(logger, dwfrm_shipping_shiptoaddress_shippingAddress_lastName + ' -> ' + p_buyer['last_name'])
        # dwfrm_shipping_shiptoaddress_shippingAddress_address1 = doc_checkout.x('//input[@id="dwfrm_shipping_shiptoaddress_shippingAddress_address1"]/@name')
        # bot_info(logger, dwfrm_shipping_shiptoaddress_shippingAddress_address1 + ' -> ' + p_buyer['shipping_address_1'])
        # dwfrm_shipping_shiptoaddress_shippingAddress_address2 = doc_checkout.x('//input[@id="dwfrm_shipping_shiptoaddress_shippingAddress_address2"]/@name')
        # bot_info(logger, dwfrm_shipping_shiptoaddress_shippingAddress_address2 + ' -> ' + p_buyer['shipping_address_2'])
        # dwfrm_shipping_shiptoaddress_shippingAddress_city = doc_checkout.x('//input[@id="dwfrm_shipping_shiptoaddress_shippingAddress_city"]/@name')
        # bot_info(logger, dwfrm_shipping_shiptoaddress_shippingAddress_city + ' -> ' + p_buyer['shipping_city'])
        # dwfrm_shipping_shiptoaddress_shippingAddress_postalCode = doc_checkout.x('//input[@id="dwfrm_shipping_shiptoaddress_shippingAddress_postalCode"]/@name')
        # bot_info(logger, dwfrm_shipping_shiptoaddress_shippingAddress_postalCode + ' -> ' + p_buyer['shipping_zip'])

        # dwfrm_shipping_shiptoaddress_shippingAddress_country = doc_checkout.q('//input[contains(@name, "dwfrm_shipping_shiptoaddress_shippingAddress_country")]')[0]
        # bot_info(logger, dwfrm_shipping_shiptoaddress_shippingAddress_country.x('@name') + ' -> ' + dwfrm_shipping_shiptoaddress_shippingAddress_country.x('@value'))

        # dwfrm_shipping_shiptoaddress_shippingAddress_phone = doc_checkout.x('//input[@id="dwfrm_shipping_shiptoaddress_shippingAddress_phone"]/@name')
        # bot_info(logger, dwfrm_shipping_shiptoaddress_shippingAddress_phone + ' -> ' + p_buyer['phone_number'])
        # dwfrm_shipping_email_emailAddress = doc_checkout.x('//input[@id="dwfrm_shipping_email_emailAddress"]/@name')
        # bot_info(logger, dwfrm_shipping_email_emailAddress + ' -> ' + p_buyer['email'])

        # dwfrm_shipping_shiptoaddress_billingAddress_firstName = doc_checkout.x('//input[@id="dwfrm_shipping_shiptoaddress_billingAddress_firstName"]/@name')
        # bot_info(logger, dwfrm_shipping_shiptoaddress_billingAddress_firstName + ' -> ' + p_buyer['first_name'])
        # dwfrm_shipping_shiptoaddress_billingAddress_lastName = doc_checkout.x('//input[@id="dwfrm_shipping_shiptoaddress_billingAddress_lastName"]/@name')
        # bot_info(logger, dwfrm_shipping_shiptoaddress_billingAddress_lastName + ' -> ' + p_buyer['last_name'])
        # dwfrm_shipping_shiptoaddress_billingAddress_address1 = doc_checkout.x('//input[@id="dwfrm_shipping_shiptoaddress_billingAddress_address1"]/@name')
        # bot_info(logger, dwfrm_shipping_shiptoaddress_billingAddress_address1 + ' -> ' + p_buyer['billing_address_1'])
        # dwfrm_shipping_shiptoaddress_billingAddress_address2 = doc_checkout.x('//input[@id="dwfrm_shipping_shiptoaddress_billingAddress_address2"]/@name')
        # bot_info(logger, dwfrm_shipping_shiptoaddress_billingAddress_address2 + ' -> ' + p_buyer['billing_address_2'])
        # dwfrm_shipping_shiptoaddress_billingAddress_city = doc_checkout.x('//input[@id="dwfrm_shipping_shiptoaddress_billingAddress_city"]/@name')
        # bot_info(logger, dwfrm_shipping_shiptoaddress_billingAddress_city + ' -> ' + p_buyer['billing_city'])
        # dwfrm_shipping_shiptoaddress_billingAddress_postalCode = doc_checkout.x('//input[@id="dwfrm_shipping_shiptoaddress_billingAddress_postalCode"]/@name')
        # bot_info(logger, dwfrm_shipping_shiptoaddress_billingAddress_postalCode + ' -> ' + p_buyer['billing_zip'])

        # dwfrm_shipping_shiptoaddress_billingAddress_country = doc_checkout.q('//input[contains(@name, "dwfrm_shipping_shiptoaddress_billingAddress_country")]')[0]
        # bot_info(logger, dwfrm_shipping_shiptoaddress_billingAddress_country.x('@name') + ' -> ' + dwfrm_shipping_shiptoaddress_billingAddress_country.x('@value'))

        # dwfrm_shipping_shiptoaddress_billingAddress_phone = doc_checkout.x('//input[@id="dwfrm_shipping_shiptoaddress_billingAddress_phone"]/@name')
        # bot_info(logger, dwfrm_shipping_shiptoaddress_billingAddress_phone + ' -> ' + p_buyer['phone_number'])
        # dwfrm_shipping_shiptoaddress_shippingAddress_ageConfirmation = doc_checkout.x('//input[@id="dwfrm_shipping_shiptoaddress_shippingAddress_ageConfirmation"]/@name')
        # bot_info(logger, dwfrm_shipping_shiptoaddress_shippingAddress_ageConfirmation + ' -> true')

        # dwfrm_shipping_shiptoaddress_shippingDetails_selectedShippingOption = doc_checkout.q('//input[contains(@name, "dwfrm_shipping_shiptoaddress_shippingDetails_selectedShippingOption")]')[0]
        # bot_info(logger, dwfrm_shipping_shiptoaddress_shippingDetails_selectedShippingOption.x('@name') + ' -> eyJtZSI6IjIwMTcwMDI3In0=')
        # dwfrm_shipping_shiptoaddress_shippingDetails_selectedShippingSubOption = doc_checkout.q('//input[contains(@name, "dwfrm_shipping_shiptoaddress_shippingDetails_selectedShippingSubOption")]')[0]
        # bot_info(logger, dwfrm_shipping_shiptoaddress_shippingDetails_selectedShippingSubOption.x('@name') + ' -> eyJtZSI6eyJib29raW5nQ29kZSI6bnVsbCwiY2FycmllckNvZGUiOiJESEwtMjEiLCJjYXJyaWVyU2VydmljZUNvZGUiOiJESFcwMDBGUjA2MDAwMDI4OTgiLCJjYXJyaWVyU2VydmljZU5hbWUiOiJESEwiLCJjb2xsZWN0aW9uIjp7ImZyb20iOjE0ODUyMTk2MDAwMDAsInRvIjoxNDg1Mjg0NDAwMDAwfSwiZGVsaXZlcnkiOnsiZnJvbSI6MTQ4NTUwNDAwMDAwMCwidG8iOjE0ODU1NDAwMDAwMDB9LCJmdWxsTmFtZSI6IkRITCIsImdyb3VwQ29kZXMiOlsiU3RhbmRhcmQiXSwic2hpcHBpbmdDaGFyZ2UiOjAsInN0b3JlVGltZXMiOm51bGwsImRpc3RhbmNlIjp7InZhbHVlIjowLCJ1bml0IjoibSJ9LCJzdG9yZUlkIjpudWxsLCJzdG9yZU5hbWUiOm51bGwsInBob3RvVXJscyI6bnVsbCwibG9nb1VybCI6bnVsbCwiaGFzRGlzYWJsZWRBY2Nlc3MiOmZhbHNlLCJ0ZWxlcGhvbmVOdW1iZXIiOm51bGwsImxvY2F0aW9uUHJvdmlkZXJJZCI6bnVsbCwiaGF6bWF0IjpudWxsLCJjb2QiOm51bGwsImxhdCI6MCwibG9uZyI6MCwicG9zdGNvZGUiOiIiLCJhZGRyZXNzIjoiIiwiY2Fycmllck5hbWUiOiJESEwtMjEiLCJzaGlwbWVudFR5cGUiOiJpbmxpbmUiLCJzZXJ2aWNlVHlwZSI6IkxpdnJhaXNvbiBzdGFuZGFyZCIsInNoaXBwaW5nQ2hhcmdlRm9ybWF0IjoiIiwic2hpcHBpbmdNZXRob2RJRCI6IlN0YW5kYXJkIiwiZGVmYXVsdE1ldGhvZCI6MX19')

        # bot_info(logger, 'shippingMethodType_0 -> inline')
        # bot_info(logger, 'dwfrm_cart_selectShippingMethod -> ShippingMethodID')
        # bot_info(logger, 'dwfrm_cart_shippingMethodID_0 -> Standard')
        # bot_info(logger, 'referer -> Cart-Show')
        # bot_info(logger, 'shipping-option-me -> 20170027')

        # for country in doc_checkout.q('//input[contains(@name, "dwfrm_shipping_shiptostore_search_country")]'):
        #     dwfrm_shipping_shiptostore_search_country = country.x['@name']
        #     bot_info(logger, dwfrm_shipping_shiptostore_search_country + ' -> ' + country.x('@value'))
        
        # for maxdistance in doc_checkout.q('//input[@id="dwfrm_shipping_shiptostore_search_maxdistance"]'):
        #     dwfrm_shipping_shiptostore_search_maxdistance = maxdistance.x('@name')
        #     bot_info(logger, dwfrm_shipping_shiptostore_search_maxdistance + ' -> 50')

        # for latitude in doc_checkout.q('//input[contains(@name, "dwfrm_shipping_shiptostore_search_latitude")]'):
        #     dwfrm_shipping_shiptostore_search_latitude = latitude.x('@name')
        #     bot_info(logger, dwfrm_shipping_shiptostore_search_latitude + ' -> ')
        # for longitude in doc_checkout.q('//input[contains(@name, "dwfrm_shipping_shiptostore_search_longitude")]'):
        #     dwfrm_shipping_shiptostore_search_longitude = longitude.x('@name')
        #     bot_info(logger, dwfrm_shipping_shiptostore_search_longitude + ' -> ')
        
        # dwfrm_shipping_shiptostore_shippingDetails_selectedShippingMethod = doc_checkout.x('//input[contains(@name, "dwfrm_shipping_shiptostore_shippingDetails_selectedShippingMethod")]/@name')
        # bot_info(logger, dwfrm_shipping_shiptostore_shippingDetails_selectedShippingMethod + ' -> ')
        # dwfrm_shipping_shiptostore_shippingDetails_storeId = doc_checkout.x('//input[contains(@name, "dwfrm_shipping_shiptostore_shippingDetails_storeId")]/@name')
        # bot_info(logger, dwfrm_shipping_shiptostore_shippingDetails_storeId + ' -> ')

        # for country in doc_checkout.q('//input[contains(@name, "dwfrm_shipping_shiptopudo_search_country")]'):
        #     dwfrm_shipping_shiptopudo_search_country = country.x['@name']
        #     bot_info(logger, dwfrm_shipping_shiptopudo_search_country + ' -> ' + country.x('@value'))

        # for maxdistance in doc_checkout.q('//input[@id="dwfrm_shipping_shiptopudo_search_maxdistance"]'):
        #     dwfrm_shipping_shiptopudo_search_maxdistance = maxdistance.x('@name')
        #     bot_info(logger, dwfrm_shipping_shiptopudo_search_maxdistance + ' -> 10')

        # dwfrm_shipping_shiptopudo_shippingDetails_selectedShippingMethod = doc_checkout.x('//input[contains(@name, "dwfrm_shipping_shiptopudo_shippingDetails_selectedShippingMethod")]/@name')
        # bot_info(logger, dwfrm_shipping_shiptopudo_shippingDetails_selectedShippingMethod + ' -> ')
        # dwfrm_shipping_shiptopudo_shippingDetails_pudoId = doc_checkout.x('//input[contains(@name, "dwfrm_shipping_shiptopudo_shippingDetails_pudoId")]/@name')
        # bot_info(logger, dwfrm_shipping_shiptopudo_shippingDetails_pudoId + ' -> ')
        # bot_info(logger, 'dwfrm_shipping_updateshippingmethods -> updateshippingmethods')


        # headers = {
        #             'Host': p_domain,
        #             'User-Agent': UserAgent,
        #             'Accept': 'application/json, text/plain, */*',
        #             'Accept-Language': 'en-US,en;q=0.5',
        #             'Accept-Encoding': 'gzip, deflate, br',
        #             'Referer': checkout_url,
        #             'Content-Type': 'application/x-www-form-urlencoded;charset=utf-8',
        #             'Content-Length': len(str(payload))
        # }


        # bot_info(logger, doc_checkout.x('//input[@id="dwfrm_adyenencrypted_holderName"]/@value'))
        # bot_info(logger, doc_checkout.x('//div[@class="phone"]/text()'))



#         payload = {
#             'dwfrm_shipping_securekey': doc_checkout.x('//input[@name="dwfrm_shipping_securekey"]/@value'),
#             : 
#         }
#         headers = {
# Host: www.adidas.fr
# User-Agent: Mozilla/5.0 (Windows NT 6.3; Win64; x64; rv:50.0) Gecko/20100101 Firefox/50.0
# Accept: application/json, text/plain, */*
# Accept-Language: en-US,en;q=0.5
# Accept-Encoding: gzip, deflate, br
# Referer: https://www.adidas.fr/on/demandware.store/Sites-adidas-FR-Site/fr_FR/COShipping-Show
# Content-Type: application/x-www-form-urlencoded;charset=utf-8
# Content-Length: 3312
# Cookie: dwanonymous_947b8007787ff0d335b6caf714d96554=abmFCN3HDehkeRmTONCPBKhA4I; optimizelyEndUserId=oeu1484873608362r0.5748382262864108; LastPageUpdateTimestamp=1485039874406; us_criteo_sociomantic_split=criteo; __adi_rt_DkpyPh8=CRTOH2H; utag_main=v_id:0159b95d2fd3001a72656bb37c010004d003200d00bd0$_sn:8$_ss:0$_st:1485041663585$_pn:29%3Bexp-session$ses_id:1485037047775%3Bexp-session; AMCV_7ADA401053CCF9130A490D4C%40AdobeOrg=-227196251%7CMCIDTS%7C17187%7CMCMID%7C67003813000988443842922613095188779933%7CMCAAMLH-1485478410%7C7%7CMCAAMB-1485641850%7CNRX38WO0n5BH8Th-nqAG_A%7CMCOPTOUT-1485044251s%7CNONE%7CMCAID%7CNONE; _ga=GA1.2.1672648003.1484873609; RES_TRACKINGID=317652878339259; ResonanceSegment=1; __CT_Data=gpv=47&apv_452_www06=47&cpv_452_www06=38; __troRUID=bc555995-622f-4230-b76b-60ab265ec7cc; s_pers=%20s_vnum%3D1485936000196%2526vn%253D8%7C1485936000196%3B%20pn%3D8%7C1487631632506%3B%20v56%3D%255B%255B%2527INTERNAL%252520SEARCH%25257CSEARCH-QUERY%2527%252C%25271485017932903%2527%255D%252C%255B%2527SITE%252520NAVIGATION%2527%252C%25271485039602007%2527%255D%252C%255B%2527INTERNAL%252520SEARCH%25257CSEARCH-QUERY%2527%252C%25271485039632508%2527%255D%255D%7C1642806032508%3B%20c4%3DCHECKOUT%257CPAYMENT%7C1485041663750%3B%20s_visit%3D1%7C1485041663769%3B%20s_invisit%3Dtrue%7C1485041663772%3B; __cq_uuid=41450bc0-de9b-11e6-8095-5ff5138e331c; __cq_seg=; WRUID15122016=0; __cq_bc=%7B%22aagl-adidas-FR%22%3A%5B%7B%22id%22%3A%22BA8612%22%2C%22sku%22%3A%22%22%2C%22type%22%3A%22%22%2C%22alt_id%22%3A%22%22%7D%2C%7B%22id%22%3A%22BA8096%22%2C%22sku%22%3A%22%22%2C%22type%22%3A%22%22%2C%22alt_id%22%3A%22%22%7D%2C%7B%22id%22%3A%22S80106%22%2C%22sku%22%3A%22%22%2C%22type%22%3A%22%22%2C%22alt_id%22%3A%22%22%7D%2C%7B%22id%22%3A%22BA7519%22%2C%22sku%22%3A%22%22%2C%22type%22%3A%22%22%2C%22alt_id%22%3A%22%22%7D%2C%7B%22id%22%3A%22BA7518%22%2C%22sku%22%3A%22%22%2C%22type%22%3A%22%22%2C%22alt_id%22%3A%22%22%7D%2C%7B%22id%22%3A%22BA7326%22%2C%22sku%22%3A%22%22%2C%22type%22%3A%22%22%2C%22alt_id%22%3A%22%22%7D%2C%7B%22id%22%3A%22BA9797%22%2C%22sku%22%3A%22%22%2C%22type%22%3A%22%22%2C%22alt_id%22%3A%22%22%7D%5D%7D; BVBRANDID=72d8e1b6-a551-43a8-9b7c-4774ce74a682; geoRedirectionAlreadySuggested=true; UserSignUpAndSave=11; lastVisitedProducts=BA8612%2CBA8096%2CS80106%2CBA7519; persistentBasketCount=1; restoreBasketUrl=%2Fon%2Fdemandware.store%2FSites-adidas-FR-Site%2Ffr_FR%2FCart-UpdateItems%3Fpid_0%3DBA8612_530%26qty_0%3D1%26basketKey%3Db7cc9f93bea60436510761bb0f029c77; geo_country=US; __troSYNC=1; dwac_cfdbEiaagZZN6aaadXRcbIATa4=H-X7m3KckqKlVVfxfCaFV8BXScICvaHOmUc%3D|dw-only|||EUR|false|Europe%2FParis|true; cqcid=abmFCN3HDehkeRmTONCPBKhA4I; sid=H-X7m3KckqKlVVfxfCaFV8BXScICvaHOmUc; pagecontext_geo_country=US; pagecontext_logged_in=""; dwsid=ErfLI0xx0W8GWixT3atgRs0FeXo8UOIDOkh1RWDAZKsTK9oWrTtc8bS758WQ2Umw9zzIs3RQEpFjmb_wlYYPuw==; PrevPageURL=https%3A%2F%2Fwww.adidas.fr%2Fon%2Fdemandware.store%2FSites-adidas-FR-Site%2Ffr_FR%2FMyAccount-CreateOrLogin; onesite_language=fr; onesite_country=FR; onesite_market=FR; AMCVS_7ADA401053CCF9130A490D4C%40AdobeOrg=1; s_pvs=5; s_tps=6; s_cc=true; s_sess=%20c12%3DBA%3B; s_sq=%5B%5BB%5D%5D; SSOAuthParams=https%7CCOShipping-Show%7Cfromlogin%3Dtrue; _cycurrln=; _cybskt=; __cy_d=381659B1-46FB-4E08-81AA-E380704BC120; QSI_HistorySession=; ak_bmsc=EB9B8C872480D2F260B3D5105CE65451174338CA32410000706D83586538FF4A~plXGU6UtPPZe0zLOysthw2ZXrkZBWYv7ZNfOFHXOni5gqEQ+sEadX186gYc6btjRESS4TRfw9bA673w+3xSw6hMgSN+0Xba/M9ZAqmRclOAUZzXMH4bzmhUDmnLPSwEqxaGv6almB4cOwwCbUEjrmSpZC/7+qSpimZZv9yg+wtN0Fvm997GG2iUL8iysvxA9btZ2BehbornTs7oqgFctZnwM+1JQgOY1BzV362KylcGX3QXoGDJ3SEtdHB0MfF/Ak9; RES_SESSIONID=34172929383644; BVBRANDSID=916c2da8-3be3-41ed-a4af-3973c18d085f; isYourReebokLogin=""; suppressedByEverLogged=1; euci_persisted=V3M4KNXMF8FK71V2; dwsecuretoken_947b8007787ff0d335b6caf714d96554=uCVMmphQ8w1TwLD2awyWDp8ESIZqE00Rkg==; pagecontext_customer_id=abmFCN3HDehkeRmTONCPBKhA4I; _gat_tealium_0=1; cartUpdateTimestamp=1485010920212; RT="dm=adidas.fr&si=3020cd71-e9a4-4116-b9b0-517bbea2a901&ss=1485039523819&sl=21&tt=200705&obo=8&sh=1485039869662%3D21%3A8%3A200705%2C1485039736657%3D20%3A8%3A188395%2C1485039735082%3D19%3A8%3A176268%2C1485039714419%3D18%3A8%3A170007%2C1485039636827%3D17%3A8%3A92199&bcn=%2F%2F36f1f23d.mpstat.us%2F"
# Connection: keep-alive }

    # elif ( p_buyer['billing_country_abbrv'] == 'USA' ):
    #     cossummary_start_url = doc_checkout.x('//div[@class="cart_wrapper rbk_shadow_angle rbk_wrapper_checkout summary_wrapper"]/@data-url')
    #     # bot_info(logger, 'cossummary_start_url -> ' + cossummary_start_url)

    #     delivery_key = doc_checkout.x('//input[@name="dwfrm_delivery_securekey"]/@value')
    #     # bot_info(logger, 'delivery_key -> ' + delivery_key)

    #     ############################################## delivery details ###################################################
    #     # bot_info(logger, 'first_name: %s' % p_buyer['first_name'])
    #     # return
    #     payload = {
    #         # 'state[]': '',
    #         # 'state[]': '',
    #         # 'dwfrm_delivery_singleshipping_shippingAddress_useAsBillingAddress': 'true',
    #         'dwfrm_cart_selectShippingMethod': 'ShippingMethodID',
    #         'dwfrm_cart_shippingMethodID_0': 'Standard',
    #         'dwfrm_delivery_billingOriginalAddress': 'false',
    #         'dwfrm_delivery_billingSuggestedAddress': 'false',
    #         'dwfrm_delivery_billing_billingAddress_addressFields_address1': p_buyer['billing_address_1'],
    #         'dwfrm_delivery_billing_billingAddress_addressFields_address2': p_buyer['billing_address_2'],
    #         'dwfrm_delivery_billing_billingAddress_addressFields_city': p_buyer['billing_city'],
    #         'dwfrm_delivery_billing_billingAddress_addressFields_country': p_buyer['billing_country_abbrv'],
    #         'dwfrm_delivery_billing_billingAddress_addressFields_countyProvince': p_buyer['billing_state_abbrv'],
    #         'dwfrm_delivery_billing_billingAddress_addressFields_firstName': p_buyer['first_name'],
    #         'dwfrm_delivery_billing_billingAddress_addressFields_lastName': p_buyer['last_name'],
    #         'dwfrm_delivery_billing_billingAddress_addressFields_phone': p_buyer['phone_number'],
    #         'dwfrm_delivery_billing_billingAddress_addressFields_zip': p_buyer['billing_zip'],
    #         'dwfrm_delivery_billing_billingAddress_isedited': 'false',
    #         'dwfrm_delivery_savedelivery': 'Review%20and%20Pay', # 'Review and Pay',
    #         'dwfrm_delivery_securekey': delivery_key,
    #         'dwfrm_delivery_shippingOriginalAddress': 'false',
    #         'dwfrm_delivery_shippingSuggestedAddress': 'false',
    #         'dwfrm_delivery_singleshipping_shippingAddress_addressFields_address1': p_buyer['shipping_address_1'],
    #         'dwfrm_delivery_singleshipping_shippingAddress_addressFields_address2': p_buyer['shipping_address_2'],
    #         'dwfrm_delivery_singleshipping_shippingAddress_addressFields_city': p_buyer['shipping_city'],
    #         'dwfrm_delivery_singleshipping_shippingAddress_addressFields_countyProvince': p_buyer['shipping_state_abbrv'],
    #         'dwfrm_delivery_singleshipping_shippingAddress_addressFields_firstName': p_buyer['first_name'],
    #         'dwfrm_delivery_singleshipping_shippingAddress_addressFields_lastName': p_buyer['last_name'],
    #         'dwfrm_delivery_singleshipping_shippingAddress_addressFields_phone': p_buyer['phone_number'],
    #         'dwfrm_delivery_singleshipping_shippingAddress_addressFields_zip': p_buyer['shipping_zip'],
    #         'dwfrm_delivery_singleshipping_shippingAddress_ageConfirmation': 'true',
    #         'dwfrm_delivery_singleshipping_shippingAddress_agreeForSubscription': 'false',
    #         'dwfrm_delivery_singleshipping_shippingAddress_email_emailAddress': p_buyer['email'],
    #         'dwfrm_delivery_singleshipping_shippingAddress_isedited': 'false',
    #         'format': 'ajax',
    #         'referer': 'Cart-Show',
    #         'shipping-group-0': 'Standard',
    #         'shippingMethodType_0': 'inline',
    #         'signup_source': 'shipping',
    #         'state': p_buyer['shipping_state'] + ','
    #     }
    #     headers = {
    #                     'Host': p_domain,
    #               'User-Agent': UserAgent,
    #                   'Accept': 'text/html, */*; q=0.01',
    #          'Accept-Language': 'en-US,en;q=0.5',
    #          'Accept-Encoding': 'gzip, deflate, br',
    #             'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
    #         'X-Requested-With': 'XMLHttpRequest',
    #                  'Referer': checkout_url,
    #           'Content-Length': len(str(payload)),
    #     }

    #     doc = s.load( cossummary_start_url, post=payload, headers=headers )

    #     ##################################### checking post delivery detail ######################################################
    #     # doc = s.load( 'https://www.adidas.com/on/demandware.store/Sites-adidas-US-Site/en_US/COSummary-Start' )
    #     # bot_info(logger,  'delivery confirmation ------------------> ' + doc.x('//input[@id="dwfrm_payment_creditCard_owner"]/@value'))
    #     # return

    #     ################################################### review & pay ###########################################################
    #     headers = {
    #                     'Host': p_domain,
    #                   'Accept': 'application/json, text/javascript, */*; q=0.01',
    #               'User-Agent': UserAgent,
    #                  'Referer': cossummary_start_url, # 'https://www.adidas.com/us/on/demandware.store/Sites-adidas-US-Site/en_US/COSummary-Start'
    #         'X-Requested-With': 'XMLHttpRequest',
    #     }
    #     payload = {
    #         'dwfrm_payment_creditCard_cvn': p_buyer['card_cvv'],
    #         'dwfrm_payment_creditCard_month': p_buyer['card_exp_month'],
    #         'dwfrm_payment_creditCard_number': p_buyer['card_number'],
    #         'dwfrm_payment_creditCard_owner': '{} {}'.format(p_buyer['first_name'], p_buyer['last_name']),
    #         'dwfrm_payment_creditCard_type': '001',  # visa
    #         'dwfrm_payment_creditCard_year': p_buyer['card_exp_year'],
    #         'dwfrm_payment_securekey': delivery_key,
    #         'dwfrm_payment_signcreditcardfields': 'sign'
    #     }

    #     url = doc_checkout.x('//form[@id="dwfrm_delivery"]/@action')

    #     doc = s.load(url, post=payload, headers=headers)

    #     if doc.status.code == 200:
    #         bot_info(logger, '%s %s -> Check your email for confirmation!' % (p_buyer['first_name'], p_buyer['last_name']), pid)

def do_login(s, logger, selected_country, p_email, p_password, pid):
    bot_info(logger, 'Login processing... -> email: %s, password: %s' % (p_email, p_password), pid)

    ####################################################################################################
    headers = {
                    'Host': selected_country['loadsignin_url'].split('//')[1].split('/')[0],
                  'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
              'User-Agent': UserAgent,
         'Accept-Language': 'en-US,en;q=0.5',
         'Accept-Encoding': 'gzip, deflate, br',
    }
    # e.g. https://cp.adidas.com/web/eCom/en_US/loadsignin?target=account
    doc = s.load(url=selected_country['loadsignin_url'], headers=headers)
    bot_info(logger, selected_country['loadsignin_url'], pid)
    #####################################################################################################

    # e.g. eCom|en_US|cp.adidas.com|null
    cd = str(doc.x('//input[@name="cd"]/@value'))

    #####################################################################################################
    payload = {
                'username'               : p_email,
                'password'               : p_password,
                'signinSubmit'           : 'Sign+in',
                'IdpAdapterId'           : str(doc.x('//input[@name="IdpAdapterId"]/@value')),
                'SpSessionAuthnAdapterId': str(doc.x('//input[@name="SpSessionAuthnAdapterId"]/@value')),
                'PartnerSpId'            : str(doc.x('//input[@name="PartnerSpId"]/@value')),
                'validator_id'           : str(doc.x('//input[@name="validator_id"]/@value')),
                'TargetResource'         : str(doc.x('//input[@name="TargetResource"]/@value')),
                'InErrorResource'        : str(doc.x('//input[@name="InErrorResource"]/@value')),
                'loginUrl'               : str(doc.x('//input[@name="loginUrl"]/@value')),
                'cd'                     : str(doc.x('//input[@name="cd"]/@value')),
                'remembermeParam'        : str(doc.x('//input[@name="remembermeParam"]/@value')),
                'app'                    : str(doc.x('//input[@name="app"]/@value')),
                'locale'                 : str(doc.x('//input[@name="locale"]/@value')),
                'domain'                 : str(doc.x('//input[@name="domain"]/@value')),
                'email'                  : str(doc.x('//input[@name="email"]/@value')),
                'pfRedirectBaseURL_test' : str(doc.x('//input[@name="pfRedirectBaseURL_test"]/@value')),
                'pfStartSSOURL_test'     : str(doc.x('//input[@name="pfStartSSOURL_test"]/@value')),
                'resumeURL_test'         : str(doc.x('//input[@name="resumeURL_test"]/@value')),
                'FromFinishRegistraion'  : str(doc.x('//input[@name="FromFinishRegistraion"]/@value')),
                'CSRFToken'              : str(doc.x('//input[@name="CSRFToken"]/@value'))
    }
    headers = { 
                           'Host': selected_country['loadsignin_url'].split('//')[1].split('/')[0],
                     'User-Agent': UserAgent,
                         'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                   'Content-Type': 'application/x-www-form-urlencoded',
                        'Referer': selected_country['loadsignin_url']
    }
    # e.g. https://cp.adidas.com/idp/startSSO.ping
    doc = s.load_html(url=selected_country['sso_url'], post=payload, headers=headers)
    bot_info(logger, selected_country['sso_url'], pid)
    ####################################################################################################

    # e.g. /idp/Ncytb/resumeSAML20/idp/startSSO.ping
    resume = re.search('^[a-z\.]+(.*)', re.search('var resURL = \'(.*)\'\;', doc).group(1).split('//')[1]).group(1)

    ###################################################################################################
    headers = { 
                           'Host': selected_country['loadsignin_url'].split('//')[1].split('/')[0],
                     'User-Agent': UserAgent,
                         'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                        'Referer': selected_country['loadsignin_url']
    }

    # e.g. https://cp.adidas.com/web/ssoCookieCreate?resume=%2Fidp%2F7InxE%2FresumeSAML20%2Fidp%2FstartSSO.ping&cd=eCom%7Cen_US%7Ccp.adidas.com%7Cnull
    doc = s.load(url=selected_country['ssoCookieCreate_url'] % (resume, cd), headers=headers)
    bot_info(logger, selected_country['ssoCookieCreate_url'], pid)
    ####################################################################################################

    headers = { 
                           'Host': selected_country['loadsignin_url'].split('//')[1].split('/')[0],
                     'User-Agent': UserAgent,
                         'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                        'Referer': selected_country['ssoCookieCreate_url'] % (resume, cd)
    }
    # e.g. https://cp.adidas.com/idp/7InxE/resumeSAML20/idp/startSSO.ping    
    cp_prefix = re.search('^(https\:\/\/[a-z\.]+)/', selected_country['loadsignin_url']).group(1)
    doc = s.load(url=cp_prefix + resume, headers=headers)
    bot_info(logger, cp_prefix + resume, pid)
    ####################################################################################################

    RelayState   = doc.x('//input[@name="RelayState"]/@value')
    SAMLResponse = doc.x('//input[@name="SAMLResponse"]/@value')

    ####################################################################################################
    headers = { 
                           'Host': selected_country['loadsignin_url'].split('//')[1].split('/')[0],
                     'User-Agent': UserAgent,
                         'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                        'Referer': cp_prefix
    }
    payload = {'RelayState': RelayState, 'SAMLResponse': SAMLResponse}
    # e.g. https://cp.adidas.com/sp/ACS.saml2
    doc = s.load(url=selected_country['ACSsaml2_url'], post=payload, headers=headers)
    bot_info(logger, selected_country['ACSsaml2_url'], pid)
    ####################################################################################################

    REF            = doc.x('//input[@name="REF"]/@value')
    TargetResource = doc.x('//input[@name="TargetResource"]/@value')

    ####################################################################################################
    headers = { 
                           'Host': selected_country['domain'],
                     'User-Agent': UserAgent,
                         'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                        'Referer': cp_prefix
    }
    payload = {'REF': REF, 'TargetResource': TargetResource}
    # e.g. https://www.adidas.com/on/demandware.store/Sites-adidas-US-Site/en_US/MyAccount-ResumeLogin
    doc = s.load(url=selected_country['ResumeLogin_url'], post=payload, headers=headers)
    bot_info(logger, selected_country['ResumeLogin_url'], pid)
    ####################################################################################################

    bot_info(logger, 'Login done.', pid)


# start buying all products by randomly selected buyer
def start_buying_by_one_buyer(s, logger, p_buyer, p_product_list, p_login, pid):

    if ( p_buyer['billing_country_abbrv'] == 'USA' ):
        selected_country = country_urls['US']
    elif ( p_buyer['billing_country_abbrv'] == 'Canada' ):
        selected_country = country_urls['CA']
    elif ( p_buyer['billing_country_abbrv'] == 'France' ):
        selected_country = country_urls['FR']
    elif ( p_buyer['billing_country_abbrv'] == 'Italy' ):
        selected_country = country_urls['IT']
    elif ( p_buyer['billing_country_abbrv'] == 'Germany' ):
        selected_country = country_urls['DE']
    elif ( p_buyer['billing_country_abbrv'] == 'Australia' ):
        selected_country = country_urls['AU']
    elif ( p_buyer['billing_country_abbrv'] == 'Belgium' ):
        selected_country = country_urls['BE']
    elif ( p_buyer['billing_country_abbrv'] == 'Russia' ):
        selected_country = country_urls['RU']
    else:
        selected_country = country_urls['GB']

    if ( p_login == True ):
        do_login(s=s, logger=logger, selected_country=selected_country, p_email=p_buyer['email'], p_password=p_buyer['password'], pid=pid)

    successful = False
    for product in p_product_list:
        if ( (product is None) or (len(product) < 3) ):
            continue
        # if ( p_buyer['billing_country_abbrv'] == 'USA' ):
        #     result = add_to_cart(s=s, logger=logger, product_url=selected_country['product_prefix'] + product[0] + '.html', product_id=product[0], size=product[1], quantity=product[3], selected_country=selected_country, pid=pid)
        # else:
        result = add_to_cart_directly(s=s, logger=logger, product_url=selected_country['product_prefix'] + product[0] + '.html', product_id=product[0], size=product[1], size_val=product[2], quantity=product[3], selected_country=selected_country, pid=pid)
        if ( result == False ):
            bot_info(logger, 'Failed with direct method. Running with human method...', pid)
            result = add_to_cart(s=s, logger=logger, product_url=selected_country['product_prefix'] + product[0] + '.html', product_id=product[0], size=product[1], quantity=product[3], selected_country=selected_country, pid=pid)
        # result = add_to_cart(s=s, logger=logger, product_url=selected_country['product_prefix'] + product[0] + '.html', product_id=product[0], size=product[1], quantity=product[3], selected_country=selected_country, pid=pid)
        successful = successful or result

    if ( successful ):
        checkout(s=s, logger=logger, checkout_url=selected_country['checkout_url'], p_buyer=p_buyer, p_domain=selected_country['domain'], pid=pid)

def check_cookie(s, logger):
    for cookie in s.client.opener.cj:
        logger.info('name: %s, value %s' % (cookie.name, cookie.value))

if __name__ == '__main__':
    if (len(sys.argv) < 2):

        print( '\n    Usage: AdidasBot.py [threads] [timeout in seconds] [login(True/False)] [retries]\n' )
        print( '\n    e.g: AdidasBot.py 2 30 True\n' )
        print( '         AdidasBot.py 100 900 True 180 -> In case of limited products such as yeezy')

        print( ' 1. Input products info into product.csv which is in form like [product_id,size,quantity]' )
        print( ' 2. Input buyers info into buyer.csv which is in form like [first_name,last_name,billing_address_1,billing_address_2,billing_city,billing_state_abbrv,billing_country_abbrv,billing_zip,phone_number,shipping_address_1,shipping_address_2,shipping_city,shipping_state_abbrv,shipping_state,shipping_zip,email,card_cvv,card_exp_month,card_number,card_exp_year]' )
        print( ' 3. In the command prompt, run this command: python AdidasBot.py [threads] [timeout in seconds] [login(True/False)] [retries]\n' )
        
        print( ' Bot will select a buyer from buyer.csv randomly and start purchasing all products in product.csv' )
        print( ' With multi-threading, variable threads number of buyers are selected so concurrent purchasing will be started.' )
        print( ' Variable timeout and retries are for the case of queue to buy limited release product such as Yeezy, NMD S79168, BA7518, BA7519 etc.\n' )
        print( ' Variable login is to decide whether bot should login or not.\n')
        
        print( ' Note: Some products in one country might not be in other country.')
    else:
        # - One drop day at 8.55am, clear your cookies via Inspect > Application > Cookies
        # - Open ONE tab only, this DOES NOT work for multiple tabs, wait for stock to be loaded.
        # - Once loaded (should be 9.00am) clear your cookies again via Inspect > Application > Cookies
        # - Refresh splash screen every 5 seconds, you can use auto referesh extension to do it.
        # - You should get through splash screen within 30 seconds - 1 minute.
        # - Repeat this for multiple cops
        # **This is tried and tested and works**
        # Times are examples.
        
        # You can find your user-agent here whoishostingthis.com/tools/user-agent
        # Enter it in your bot and set the hmac cookie manually and you will be able to cart
        # Advanced -> Set a cookie for HMAC and Advanced -> Set User Agent for setting the User Agent

        # In case of limited products such as yeezy, threads = 100, timeout = 900, retries = 180

        threads = int(sys.argv[1])
        timeout = 30
        retries = 3
        if ( len(sys.argv) > 2 ):
            timeout = int(sys.argv[2])
        if ( len(sys.argv) > 3 ):
            login = True if sys.argv[3] == 'True' else False
        if ( len(sys.argv) > 4 ):
            retries = int(sys.argv[4])

        print('Threads: %d' % threads)
        print('Timeout: %d' % timeout)
        print('Retries: %d' % retries)
        print('login: %s' % ('True' if login else 'False'))

        print('start_time: ' + time.strftime("%b %d %Y %H:%M:%S", time.gmtime()))
        start_time = timeit.default_timer()

        # Create a list of jobs and then iterate through the number of threads appending each thread to the job list 
        jobs = []
        for i in range(0, threads):
            product_list = read_products(logger=g_logger, pid=i)

            first_name, last_name, billing_address_1, billing_address_2, billing_city, billing_state_abbrv, billing_country_abbrv, billing_zip, phone_number, shipping_address_1, shipping_address_2, shipping_city, shipping_state_abbrv, shipping_state, shipping_zip, email, password, card_cvv, card_exp_month, card_number, card_exp_year = select_buyer(logger=g_logger, p_country='', pid=i)
            buyer_info = { 'first_name'           : first_name, 
                           'last_name'            : last_name, 
                           'billing_address_1'    : billing_address_1, 
                           'billing_address_2'    : billing_address_2, 
                           'billing_city'         : billing_city, 
                           'billing_state_abbrv'  : billing_state_abbrv, 
                           'billing_country_abbrv': billing_country_abbrv, 
                           'billing_zip'          : billing_zip, 
                           'phone_number'         : phone_number, 
                           'shipping_address_1'   : shipping_address_1, 
                           'shipping_address_2'   : shipping_address_2, 
                           'shipping_city'        : shipping_city, 
                           'shipping_state_abbrv' : shipping_state_abbrv, 
                           'shipping_state'       : shipping_state, 
                           'shipping_zip'         : shipping_zip, 
                           'email'                : email, 
                           'password'             : password, 
                           'card_cvv'             : card_cvv, 
                           'card_exp_month'       : card_exp_month, 
                           'card_number'          : card_number, 
                           'card_exp_year'        : card_exp_year }

            if ( buyer_info['billing_country_abbrv'].strip() == '' ):
                continue

            s = Scraper(use_cache=False, 
                  max_redirects=10,
                  retries=retries, 
                  timeout=timeout, 
                  log_file='log_%s_%d.txt' % (time.strftime("%b%d%Y%H%M%S", time.gmtime()), i),
                  proxy_file='proxy_%s.txt' % buyer_info['billing_country_abbrv'],
                  one_proxy=True
                  )
            logger = s.logger

            # send_notify_email(logger, 'jeanmarcr088@gmail.com', 'Yesnayah141103', 'checkout_msg')
            # exit()

            thread = threading.Thread(target=start_buying_by_one_buyer, args=(s, logger, buyer_info, product_list, login, i))
            jobs.append(thread)

        # Start the threads
        for j in jobs:
            j.start()

        # Ensure all of the threads have finished
        for j in jobs:
            j.join()

        end_time = timeit.default_timer()
        print('end_time: ' + time.strftime("%b %d %Y %H:%M:%S", time.gmtime()))
        print('elapsed_time: %f seconds' % (end_time - start_time))


