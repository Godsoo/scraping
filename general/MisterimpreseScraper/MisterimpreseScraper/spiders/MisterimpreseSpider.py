# -*- coding: utf-8 -*-
import scrapy
import requests
from scrapy.selector import Selector
from scrapy.http import Request
import re
from MisterimpreseScraper.items import CompanyItem
import random
import base64
from copy import deepcopy
import time

class MisterimpreseSpider(scrapy.Spider):
    name = "MisterimpreseSpider"
    # allowed_domains = ["www.misterimprese.it/aziende"]
    start_urls = (
        'http://www.misterimprese.it/aziende',
    )
    headers = {
                'Host': 'www.misterimprese.it',
                'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:51.0) Gecko/20100101 Firefox/51.0',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                # 'Proxy-Authorization': 'Basic ' + base64.encodestring(b'user:p19gh1a').strip().decode('utf-8') 
                }
    proxy_list = [
                    'http://185.44.77.3:1103', # user:p19gh1a
                    'http://185.44.77.4:1104',
                    'http://185.44.77.5:1105',
                    'http://185.44.77.6:1106',
                    'http://185.44.77.7:1107',
                    'http://185.44.77.8:1108',
                    'http://185.44.77.9:1109',
                    'http://185.44.77.10:1110',
                    'http://185.44.77.11:1111',
                    'http://185.44.77.12:1112',
                    'http://185.44.77.13:1113',
                    'http://185.44.77.14:1114',
                    'http://185.44.77.15:1115',
                    'http://185.44.77.16:1116',
                    'http://185.44.77.17:1117',
                    'http://185.44.77.18:1118',
                    'http://185.44.77.19:1119',
                    'http://185.44.77.20:1120',
                    'http://185.44.77.21:1121',
                    'http://185.44.77.22:1122',
                    'http://185.44.77.23:1123',
                    'http://185.44.77.24:1124',
                    'http://185.44.77.25:1125',
                    'http://185.44.77.26:1126',
                    'http://185.44.77.27:1127',
                    'http://185.44.77.28:1128',
                    'http://185.44.77.29:1129',
                    'http://185.44.77.30:1130',
                    'http://185.44.77.31:1131',
                    'http://185.44.77.32:1132',
                    'http://185.44.77.33:1133',
                    'http://185.44.77.34:1134',
                    'http://185.44.77.35:1135',
                    'http://185.44.77.36:1136',
                    'http://185.44.77.37:1137',
                    'http://185.44.77.38:1138',
                    'http://185.44.77.39:1139',
                    'http://185.44.77.40:11400',
                    'http://185.44.77.41:11401',
                    'http://185.44.77.42:11402',
                    'http://185.44.77.43:11403',
                    'http://185.44.77.44:11404',
                    'http://185.44.77.45:11405',
                    'http://185.44.77.46:11406',
                    'http://185.44.77.47:11407',
                    'http://185.44.77.48:11408',
                    'http://185.44.77.49:11409',
                    'http://185.44.77.50:11500',
                    'http://185.44.77.51:11501',
                    'http://185.44.77.52:11502',
                    'http://185.44.77.53:11503',
                    'http://185.44.77.54:11504',
                    'http://185.44.77.55:11505',
                    'http://185.44.77.56:11506',
                    'http://185.44.77.57:11507',
                    'http://185.44.77.58:11508',
                    'http://185.44.77.59:11509',
                    'http://185.44.77.60:11600',
                    'http://185.44.77.61:11601',
                    'http://185.44.77.62:11602',
                    'http://185.44.77.63:11603',
                    'http://185.44.77.64:11604',
                    'http://185.44.77.65:11605',
                    'http://185.44.77.66:11606',
                    'http://185.44.77.67:11607',
                    'http://185.44.77.68:11608',
                    'http://185.44.77.69:11609',
                    'http://185.44.77.70:11700',
                    'http://185.44.77.71:11701',
                    'http://185.44.77.72:11702',
                    'http://185.44.77.73:11703',
                    'http://185.44.77.74:11704',
                    'http://185.44.77.75:11705',
                    'http://185.44.77.76:11706',
                    'http://185.44.77.77:11707',
                    'http://185.44.77.78:11708',
                    'http://185.44.77.79:11709',
                    'http://185.44.77.80:11800',
                    'http://185.44.77.81:11801',
                    'http://185.44.77.82:11802',
                    'http://185.44.77.83:11803',
                    'http://185.44.77.84:11804',
                    'http://185.44.77.85:11805',
                    'http://185.44.77.86:11806',
                    'http://185.44.77.87:11807',
                    'http://185.44.77.88:11808',
                    'http://185.44.77.89:11809',
                    'http://185.44.77.90:11900',
                    'http://185.44.77.91:11901',
                    'http://185.44.77.92:11902',
                    'http://185.44.77.93:11903',
                    'http://185.44.77.94:11904',
                    'http://185.44.77.95:11905',
                    'http://185.44.77.96:11906',
                    'http://185.44.77.97:11907',
                    'http://185.44.77.98:11908',
                    'http://185.44.77.99:11609',
                    'http://185.44.77.100:11200',
                    'http://185.44.77.101:11201',
                    'http://185.44.77.102:11202',
                    'http://185.44.77.103:11203',
                    'http://185.44.77.104:11204',
                    'http://185.44.77.105:11205',
                    'http://185.44.77.106:11206',
                    'http://185.44.77.107:11207',
                    'http://185.44.77.108:11208',
                    'http://185.44.77.109:11209',
                    'http://185.44.77.110:11210',
                    'http://185.44.77.111:11211',
                    'http://185.44.77.112:11212',
                    'http://185.44.77.113:11213',
                    'http://185.44.77.114:11214',
                    'http://185.44.77.115:11215',
                    'http://185.44.77.116:11216',
                    'http://185.44.77.117:11217',
                    'http://185.44.77.118:11218',
                    'http://185.44.77.119:11219',
                    'http://185.44.77.120:11220',
                    'http://185.44.77.121:11221',
                    'http://185.44.77.122:11222',
                    'http://185.44.77.123:11223',
                    'http://185.44.77.124:11224',
                    'http://185.44.77.125:11225',
                    'http://185.44.77.126:11226',
                    'http://185.44.77.127:11227',
                    'http://185.44.77.128:11228',
                    'http://185.44.77.129:11229',
                    'http://185.44.77.130:11230',
                    'http://185.44.77.131:11231',
                    'http://185.44.77.132:11232',
                    'http://185.44.77.133:11233',
                    'http://185.44.77.134:11234',
                    'http://185.44.77.135:11235',
                    'http://185.44.77.136:11236',
                    'http://185.44.77.137:11237',
                    'http://185.44.77.138:11238',
                    'http://185.44.77.139:11209',
                    'http://185.44.77.140:11240',
                    'http://185.44.77.141:11241',
                    'http://185.44.77.142:11242',
                    'http://185.44.77.143:11243',
                    'http://185.44.77.144:11244',
                    'http://185.44.77.145:11245',
                    'http://185.44.77.146:11246',
                    'http://185.44.77.147:11247',
                    'http://185.44.77.148:11248',
                    'http://185.44.77.149:11249',
                    'http://185.44.77.150:11250',
                    'http://185.44.77.151:11251',
                    'http://185.44.77.152:11252',
                    'http://185.44.77.153:11253',
                    'http://185.44.77.154:11254',
                    'http://185.44.77.155:11255',
                    'http://185.44.77.156:11256',
                    'http://185.44.77.157:11257',
                    'http://185.44.77.158:11258',
                    'http://185.44.77.159:11259',
                    'http://185.44.77.160:11260',
                    'http://185.44.77.161:11261',
                    'http://185.44.77.162:11262',
                    'http://185.44.77.163:11263',
                    'http://185.44.77.164:11264',
                    'http://185.44.77.165:11265',
                    'http://185.44.77.166:11266',
                    'http://185.44.77.167:11267',
                    'http://185.44.77.168:11268',
                    'http://185.44.77.169:11269',
                    'http://185.44.77.170:11270',
                    'http://185.44.77.171:11271',
                    'http://185.44.77.172:11272',
                    'http://185.44.77.173:11273',
                    'http://185.44.77.174:11274',
                    'http://185.44.77.175:11275',
                    'http://185.44.77.176:11276',
                    'http://185.44.77.177:11277',
                    'http://185.44.77.178:11278',
                    'http://185.44.77.179:11279',
                    'http://185.44.77.180:11280',
                    'http://185.44.77.181:11281',
                    'http://185.44.77.182:11282',
                    'http://185.44.77.183:11283',
                    'http://185.44.77.184:11284',
                    'http://185.44.77.185:11285',
                    'http://185.44.77.186:11286',
                    'http://185.44.77.187:11287',
                    'http://185.44.77.188:11288',
                    'http://185.44.77.189:11289',
                    'http://185.44.77.190:11290',
                    'http://185.44.77.191:11291',
                    'http://185.44.77.192:11292',
                    'http://185.44.77.193:11293',
                    'http://185.44.77.194:11294',
                    'http://185.44.77.195:11295',
                    'http://185.44.77.196:11296',
                    'http://185.44.77.197:11297',
                    'http://185.44.77.198:11298',
                    'http://185.44.77.199:11269',
                    'http://185.44.77.200:11300',
                    'http://185.44.77.201:11301',
                    'http://185.44.77.202:11302',
                    'http://185.44.77.203:11303',
                    'http://185.44.77.204:11304',
                    'http://185.44.77.205:11305',
                    'http://185.44.77.206:11306',
                    'http://185.44.77.207:11307',
                    'http://185.44.77.208:11308',
                    'http://185.44.77.209:11309',
                    'http://185.44.77.210:11310',
                    'http://185.44.77.211:11311',
                    'http://185.44.77.212:11312',
                    'http://185.44.77.213:11313',
                    'http://185.44.77.214:11314',
                    'http://185.44.77.215:11315',
                    'http://185.44.77.216:11316',
                    'http://185.44.77.217:11317',
                    'http://185.44.77.218:11318',
                    'http://185.44.77.219:11319',
                    'http://185.44.77.220:11320',
                    'http://185.44.77.221:11321',
                    'http://185.44.77.222:11322',
                    'http://185.44.77.223:11323',
                    'http://185.44.77.224:11324',
                    'http://185.44.77.225:11325',
                    'http://185.44.77.226:11326',
                    'http://185.44.77.227:11327',
                    'http://185.44.77.228:11328',
                    'http://185.44.77.229:11329',
                    'http://185.44.77.230:11330',
                    'http://185.44.77.231:11331',
                    'http://185.44.77.232:11332',
                    'http://185.44.77.233:11333',
                    'http://185.44.77.234:11334',
                    'http://185.44.77.235:11335',
                    'http://185.44.77.236:11336',
                    'http://185.44.77.237:11337',
                    'http://185.44.77.238:11338',
                    'http://185.44.77.239:11339',
                    'http://185.44.77.240:11340',
                    'http://185.44.77.241:11341',
                    'http://185.44.77.242:11342',
                    'http://185.44.77.243:11343',
                    'http://185.44.77.244:11344',
                    'http://185.44.77.245:11345',
                    'http://185.44.77.246:11346',
                    'http://185.44.77.247:11347',
                    'http://185.44.77.248:11348',
                    'http://185.44.77.249:11349',
                    'http://185.44.77.250:11355',
                    'http://185.44.77.251:11356',
                    'http://185.44.77.252:11357',
                    'http://185.44.77.253:11358',
                    'http://185.44.77.254:11359',
                    'http://67.220.254.105:18058', # erwin05dec1998:APg28fvK
                    'http://67.220.254.106:18058',
                    'http://67.220.254.11:18058',
                    'http://67.220.254.110:18058',
                    'http://67.220.254.111:18058',
                    'http://67.220.254.114:18058',
                    'http://67.220.254.115:18058',
                    'http://67.220.254.117:18058',
                    'http://67.220.254.12:18058',
                    'http://67.220.254.121:18058',
                    'http://67.220.254.123:18058',
                    'http://67.220.254.125:18058',
                    'http://67.220.254.126:18058',
                    'http://67.220.254.127:18058',
                    'http://67.220.254.128:18058',
                    'http://67.220.254.13:18058',
                    'http://67.220.254.131:18058',
                    'http://67.220.254.132:18058',
                    'http://67.220.254.133:18058',
                    'http://67.220.254.134:18058',
                    'http://67.220.254.135:18058',
                    'http://67.220.254.137:18058',
                    'http://67.220.254.14:18058',
                    'http://67.220.254.140:18058',
                    'http://67.220.254.142:18058',
                    'http://67.220.254.143:18058',
                    'http://67.220.254.145:18058',
                    'http://67.220.254.146:18058',
                    'http://67.220.254.147:18058',
                    'http://67.220.254.149:18058',
                    'http://67.220.254.15:18058',
                    'http://67.220.254.155:18058',
                    'http://67.220.254.16:18058',
                    'http://67.220.254.164:18058',
                    'http://67.220.254.166:18058',
                    'http://67.220.254.17:18058',
                    'http://67.220.254.172:18058',
                    'http://67.220.254.173:18058',
                    'http://67.220.254.174:18058',
                    'http://67.220.254.175:18058',
                    'http://67.220.254.176:18058',
                    'http://67.220.254.177:18058',
                    'http://67.220.254.179:18058',
                    'http://67.220.254.18:18058',
                    'http://67.220.254.181:18058',
                    'http://67.220.254.183:18058',
                    'http://67.220.254.184:18058',
                    'http://67.220.254.186:18058',
                    'http://67.220.254.187:18058',
                    'http://67.220.254.188:18058',
                    'http://67.220.254.19:18058',
                    'http://67.220.254.190:18058',
                    'http://67.220.254.191:18058',
                    'http://67.220.254.192:18058',
                    'http://67.220.254.193:18058',
                    'http://67.220.254.194:18058',
                    'http://67.220.254.195:18058',
                    'http://67.220.254.196:18058',
                    'http://67.220.254.197:18058',
                    'http://67.220.254.198:18058',
                    'http://67.220.254.20:18058',
                    'http://67.220.254.209:18058',
                    'http://67.220.254.21:18058',
                    'http://67.220.254.210:18058',
                    'http://67.220.254.211:18058',
                    'http://67.220.254.212:18058',
                    'http://67.220.254.213:18058',
                    'http://67.220.254.216:18058',
                    'http://67.220.254.217:18058',
                    'http://67.220.254.218:18058',
                    'http://67.220.254.219:18058',
                    'http://67.220.254.22:18058',
                    'http://67.220.254.220:18058',
                    'http://67.220.254.221:18058',
                    'http://67.220.254.222:18058',
                    'http://67.220.254.223:18058',
                    'http://67.220.254.224:18058',
                    'http://67.220.254.225:18058',
                    'http://67.220.254.25:18058',
                    'http://67.220.254.26:18058',
                    'http://67.220.254.28:18058',
                    'http://67.220.254.29:18058',
                    'http://67.220.254.30:18058',
                    'http://67.220.254.31:18058',
                    'http://67.220.254.32:18058',
                    'http://67.220.254.33:18058',
                    'http://67.220.254.35:18058',
                    'http://67.220.254.36:18058',
                    'http://67.220.254.39:18058',
                    'http://67.220.254.40:18058',
                    'http://67.220.254.41:18058',
                    'http://67.220.254.44:18058',
                    'http://67.220.254.62:18058',
                    'http://67.220.254.63:18058',
                    'http://67.220.254.64:18058',
                    'http://67.220.254.67:18058',
                    'http://67.220.254.68:18058',
                    'http://67.220.254.76:18058',
                    'http://67.220.254.78:18058',
                    'http://67.220.254.89:18058',
                    'http://38.141.0.2:60000',   # silicons:1pRnQcg87F
                    'http://38.141.0.5:60000',
                    'http://38.141.0.8:60000',
                    'http://38.141.0.11:60000',
                    'http://38.141.0.14:60000',
                    'http://38.141.0.16:60000',
                    'http://38.141.0.19:60000',
                    'http://38.141.0.22:60000',
                    'http://38.141.0.25:60000',
                    'http://38.141.0.28:60000',
                    'http://38.141.0.30:60000',
                    'http://38.141.0.33:60000',
                    'http://38.141.0.36:60000',
                    'http://38.141.0.39:60000',
                    'http://38.141.0.42:60000',
                    'http://38.141.0.44:60000',
                    'http://38.141.0.47:60000',
                    'http://38.141.0.50:60000',
                    'http://38.141.0.53:60000',
                    'http://38.141.0.56:60000',
                    'http://38.141.0.58:60000',
                    'http://38.141.0.61:60000',
                    'http://38.141.0.64:60000',
                    'http://38.141.0.67:60000',
                    'http://38.141.0.70:60000',
                    'http://38.141.0.72:60000',
                    'http://38.141.0.75:60000',
                    'http://38.141.0.78:60000',
                    'http://38.141.0.81:60000',
                    'http://38.141.0.84:60000',
                    'http://38.141.0.86:60000',
                    'http://38.141.0.89:60000',
                    'http://38.141.0.92:60000',
                    'http://38.141.0.95:60000',
                    'http://38.141.0.98:60000',
                    'http://38.141.0.100:60000',
                    'http://38.141.0.103:60000',
                    'http://38.141.0.106:60000',
                    'http://38.141.0.109:60000',
                    'http://38.141.0.112:60000',
                    'http://38.141.0.114:60000',
                    'http://38.141.0.117:60000',
                    'http://38.141.0.120:60000',
                    'http://38.141.0.123:60000',
                    'http://38.141.0.126:60000',
                    'http://38.141.0.128:60000',
                    'http://38.141.0.131:60000',
                    'http://38.141.0.134:60000',
                    'http://38.141.0.137:60000',
                    'http://38.141.0.140:60000'
    ]

    def start_requests(self):
        headers = deepcopy(self.headers)
        for url in self.start_urls:
            selected_proxy = random.choice(self.proxy_list)            
            if ( '67.220.254' in selected_proxy ):
                headers['Proxy-Authorization'] = 'Basic ' + base64.encodestring(b'erwin05dec1998:APg28fvK').strip().decode('utf-8')
            elif ( '185.44.77' in selected_proxy ):
                headers['Proxy-Authorization'] = 'Basic ' + base64.encodestring(b'user:p19gh1a').strip().decode('utf-8')
            elif ( '38.141.0' in selected_proxy ):
                headers['Proxy-Authorization'] = 'Basic ' + base64.encodestring(b'silicons:1pRnQcg87F').strip().decode('utf-8')
            time.sleep(1)
            yield Request(url=url, method='GET', headers=headers, callback=self.parse_categories, meta={'proxy': selected_proxy})

    def parse_categories(self, response):
        headers = deepcopy(self.headers)
        category_urls = response.xpath('//div[@id="contcat"]/div[@class="mcat"]//div[@class="scatcont"]/ul/li/div/div/a/@href').extract()
        # self.logger.info(category_urls)
        for category_url in category_urls:
            # self.logger.info(category_url)
            selected_proxy = random.choice(self.proxy_list)            
            if ( '67.220.254' in selected_proxy ):
                headers['Proxy-Authorization'] = 'Basic ' + base64.encodestring(b'erwin05dec1998:APg28fvK').strip().decode('utf-8')
            elif ( '185.44.77' in selected_proxy ):
                headers['Proxy-Authorization'] = 'Basic ' + base64.encodestring(b'user:p19gh1a').strip().decode('utf-8')
            elif ( '38.141.0' in selected_proxy ):
                headers['Proxy-Authorization'] = 'Basic ' + base64.encodestring(b'silicons:1pRnQcg87F').strip().decode('utf-8')
            time.sleep(1)
            yield Request(url=response.urljoin(category_url), headers=headers, callback=self.get_CompanyUrls, meta={'proxy': selected_proxy})
            # break

    def get_CompanyUrls(self, response):
        headers = deepcopy(self.headers)
        pagesearch_url = response.url.replace('.html', '') + '+'
        page_num = 1
        res_page = response
        while (1):
            try:
                company_urls = res_page.xpath('//div[@class="box-company"]/div[@class="company-data"]/div/a/@href').extract()
                # self.logger.info(company_urls)
                if ( len(company_urls) == 0 ):
                    break
                for company_url in company_urls:
                    selected_proxy = random.choice(self.proxy_list)            
                    if ( '67.220.254' in selected_proxy ):
                        headers['Proxy-Authorization'] = 'Basic ' + base64.encodestring(b'erwin05dec1998:APg28fvK').strip().decode('utf-8')
                    elif ( '185.44.77' in selected_proxy ):
                        headers['Proxy-Authorization'] = 'Basic ' + base64.encodestring(b'user:p19gh1a').strip().decode('utf-8')
                    elif ( '38.141.0' in selected_proxy ):
                        headers['Proxy-Authorization'] = 'Basic ' + base64.encodestring(b'silicons:1pRnQcg87F').strip().decode('utf-8')
                    time.sleep(1)
                    yield Request(url=response.urljoin(company_url), headers=headers, callback=self.parse_CompanyInfo, meta={'proxy': selected_proxy})
                # break
                page_num = page_num + 1
                selected_proxy = random.choice(self.proxy_list)            
                if ( '67.220.254' in selected_proxy ):
                    headers['Proxy-Authorization'] = 'Basic ' + base64.encodestring(b'erwin05dec1998:APg28fvK').strip().decode('utf-8')
                elif ( '185.44.77' in selected_proxy ):
                    headers['Proxy-Authorization'] = 'Basic ' + base64.encodestring(b'user:p19gh1a').strip().decode('utf-8')
                elif ( '38.141.0' in selected_proxy ):
                    headers['Proxy-Authorization'] = 'Basic ' + base64.encodestring(b'silicons:1pRnQcg87F').strip().decode('utf-8')
                time.sleep(1)
                res_page = Selector(requests.get(url=pagesearch_url + str(page_num) + '.html', headers=headers, meta={'proxy': selected_proxy}))
            except:
                break

    def parse_CompanyInfo(self, response):
        item = CompanyItem()

        item['RAG1'] = response.xpath('//div[@id="companyDetails"]/h2/span[@itemprop="name"]/text()').extract_first()
        item['RAG2'] = response.xpath('//div[@id="companyDetails"]/h5/text()').extract_first()
        item['INDIRIZZO'] = response.xpath('//div[@id="companyDetails"]//div[@itemprop="address"]/div/span[@itemprop="streetAddress"]/text()').extract_first()
        item['CAP'] = response.xpath('//div[@id="companyDetails"]//div[@itemprop="address"]/div/span[@itemprop="postalCode"]/text()').extract_first()
        item['CITTA'] = ' '.join(response.xpath('//div[@id="companyDetails"]//div[@itemprop="address"]/div/a[@itemprop="addressLocality"]/..//text()').extract())

        if ( item['RAG1'] ):
            item['RAG1'] = item['RAG1'].strip()
        else:
            item['RAG1'] = ''
        if ( item['RAG2'] ):
            item['RAG2'] = item['RAG2'].strip()
        else:
            item['RAG2'] = ''
        if ( item['INDIRIZZO'] ):
            item['INDIRIZZO'] = item['INDIRIZZO'].strip()
        else:
            item['INDIRIZZO'] = ''
        if ( item['CAP'] ):
            item['CAP'] = item['CAP'].strip()
        else:
            item['CAP'] = ''
        if ( item['CITTA'] ):
            item['CITTA'] = item['CITTA'].strip()
        else:
            item['CITTA'] = ''        

        breadcrumb = response.xpath('//ul[@class="breadcrumb navbar-left"]/li/span[@itemprop="breadcrumb"]/a/text()').extract()
        try:
            item['REGIONE'] = breadcrumb[0]
        except:
            item['REGIONE'] = ''
        try:
            item['PROVINCIA'] = breadcrumb[1]
        except:
            item['PROVINCIA'] = ''
        try:
            item['COMUNE'] = breadcrumb[2]
        except:
            item['COMUNE'] = ''

        item['CONTATTI_01'] = response.xpath('//div[@id="companyDetails"]//div/span[@itemprop="telephone"]/text()').extract_first()
        item['CONTATTI_02'] = response.xpath('//div[@id="companyDetails"]//div/span[@itemprop="faxNumber"]/text()').extract_first()
        item['CONTATTI_03'] = response.xpath('//div[@id="companyDetails"]/div/div/div/a[@rel="nofollow"]/text()').extract_first()
        try:
            item['CONTATTI_04'] = response.urljoin('/img/' + re.search('\+z\+\"\/([\w]+)\=', response.xpath('//script[contains(text(), "Iwo3ahTu")]/text()').extract_first(), re.S|re.M|re.I).group(1) + '=')
            # yield Request(url=item['CONTATTI_04'], callback=self.download_file, headers=self.headers, meta={'imagename': item['RAG1'], 'proxy': random.choice(self.proxy_list)})
        except:
            item['CONTATTI_04'] = ''
        # item['file_urls'] = [item['CONTATTI_04']]

        item['CONTATTI_05'] = '' 

        if ( item['CONTATTI_01'] ):
            item['CONTATTI_01'] = item['CONTATTI_01'].strip()
        else:
            item['CONTATTI_01'] = ''
        if ( item['CONTATTI_02'] ):
            item['CONTATTI_02'] = item['CONTATTI_02'].strip()
        else:
            item['CONTATTI_02'] = ''
        if ( item['CONTATTI_03'] ):
            item['CONTATTI_03'] = item['CONTATTI_03'].strip()
        else:
            item['CONTATTI_03'] = ''

        item['PIVA'] = response.xpath('//div[@id="companyDetails"]//div/b[contains(text(), "N. Partita IVA:")]/../following-sibling::div/span/text()').extract_first()
        item['CATEGORIA'] = ', '.join(response.xpath('//div[@id="companyDetails"]//div/b[contains(text(), "Categoria:")]/../following-sibling::div/a/text()').extract())

        if ( item['PIVA'] ):
            item['PIVA'] = item['PIVA'].strip()
        else:
            item['PIVA'] = ''
        if ( item['CATEGORIA'] ):
            item['CATEGORIA'] = item['CATEGORIA'].strip()
        else:
            item['CATEGORIA'] = ''

        yield item

    def download_file(self, response):
        with open('images/' + response.meta['imagename'] + '.jpg', 'wb') as f:
            f.write(response.body)
        
