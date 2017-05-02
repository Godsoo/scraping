'''
Extracting only the next categories:
Fitness Technology http://screencast.com/t/ZApe0i6XZO 
DIY http://screencast.com/t/pQHfOzyKUXm
Televisions http://screencast.com/t/XrWhotFPNFOF
Computing and Phones http://screencast.com/t/suze9FYu8aQ
Home Electricals http://screencast.com/t/8DbXY3oBy
Baby & Nursery http://screencast.com/t/53YeShyLowF
Garden and Outdoor http://screencast.com/t/ZJ9quuEnxW9
'''

import re
import os
import csv
import urllib
from urlparse import urljoin as urljoin_rfc

from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.spiders import Spider
from scrapy import log
from scrapy.utils.response import get_base_url

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price

HERE = os.path.abspath(os.path.dirname(__file__))


class Argos(Spider):
    name = 'aldi-argos'
    allowed_domains = ['argos.co.uk']
    start_urls = ('http://www.argos.co.uk/static/Browse/ID72/42413318/c_1/1%7Ccategory_root%7CSports+and+leisure%7C33006346/c_2/2%7C33006346%7CFitness+equipment%7C33008186/c_3/3%7Ccat_33008186%7CFitness+technology%7C42413318.htm',
                  'http://www.argos.co.uk/static/Browse/ID72/33017148/c_1/1%7Ccategory_root%7CTechnology%7C33006169/c_2/2%7C33006169%7CTelevisions+and+accessories%7C33008651/c_3/3%7Ccat_33008651%7CTelevisions%7C33017148.htm?tag=ar:ddn:tn:tv',
                  'http://www.argos.co.uk/static/Browse/ID72/33020252/c_1/1%7Ccategory_root%7CSports+and+leisure%7C33006346/c_2/2%7C33006346%7CHobbies+and+crafts%7C33006502/c_3/3%7C33006502%7CSewing+machines+and+accessories%7C33009599/c_4/4%7Ccat_33009599%7CSewing+machines%7C33020252.htm') + (u'http://www.argos.co.uk/static/Browse/ID72/33007178/c_1/1|category_root|Home+and+garden|33005908/c_2/2|cat_33005908|DIY+tools+and+power+tools|33007178.htm',
 u'http://www.argos.co.uk/static/Browse/ID72/33013811/c_1/1%7Ccategory_root%7CHome+and+garden%7C33005908/c_2/2%7C33005908%7CDIY+tools+and+power+tools%7C33007178/c_3/3%7Ccat_33007178%7CDIY+power+tools%7C33013811.htm',
 u'http://www.argos.co.uk/static/Browse/ID72/33018827/c_1/1%7Ccategory_root%7CHome+and+garden%7C33005908/c_2/2%7C33005908%7CDIY+tools+and+power+tools%7C33007178/c_3/3%7Ccat_33007178%7CDIY+power+tools%7C33013811/c_4/4%7Ccat_33013811%7CDrills%7C33018827.htm',
 u'http://www.argos.co.uk/static/Browse/ID72/33021229/c_1/1%7Ccategory_root%7CHome+and+garden%7C33005908/c_2/2%7C33005908%7CDIY+tools+and+power+tools%7C33007178/c_3/3%7Ccat_33007178%7CElectrical+accessories%7C33010322/c_4/4%7Ccat_33010322%7CExtension+leads+and+cable+reels%7C33021229.htm',
 u'http://www.argos.co.uk/static/Browse/ID72/33013081/c_1/1|category_root|Home+and+garden|33005908/c_2/2|33005908|Heating+and+cooling|33007608/c_3/3|cat_33007608|Fans|33013081.htm',
 u'http://www.argos.co.uk/static/Browse/ID72/33010665/c_1/1|category_root|Home+and+garden|33005908/c_2/2|33005908|Home+improvements|33007046/c_3/3|cat_33007046|Home+security+and+safety|33010665.htm?tag=ar:gnav:HomeSecurity',
 u'http://www.argos.co.uk/static/Browse/ID72/33008463/c_1/1|category_root|Home+and+garden|33005908/c_2/2|cat_33005908|Fitted+kitchens|33008463.htm',
 u'http://www.argos.co.uk/static/Browse/ID72/33016652/c_1/1|category_root|Home+and+garden|33005908/c_2/2|33005908|Heating+and+cooling|33007608/c_3/3|cat_33007608|Heaters+and+radiators|33016652.htm',
 u'http://www.argos.co.uk/static/Browse/ID72/33007046/c_1/1|category_root|Home+and+garden|33005908/c_2/2|cat_33005908|Home+improvements|33007046.htm',
 u'http://www.argos.co.uk/static/Browse/ID72/33013182/c_1/1|category_root|Home+and+garden|33005908/c_2/2|33005908|DIY+tools+and+power+tools|33007178/c_3/3|cat_33007178|Ladders+and+step+stools|33013182.htm',
 u'http://www.argos.co.uk/static/Browse/ID72/33010705/c_1/1|category_root|Home+and+garden|33005908/c_2/2|33005908|Home+improvements|33007046/c_3/3|cat_33007046|Showers+and+accessories|33010705.htm',
 u'http://www.argos.co.uk/static/Browse/ID72/33021006/c_1/1%7Ccategory_root%7CHome+and+garden%7C33005908/c_2/2%7C33005908%7CHome+improvements%7C33007046/c_3/3%7Ccat_33007046%7CShowers+and+accessories%7C33010705/c_4/4%7Ccat_33010705%7CShowers%7C33021006/r_001/1%7C3DTV+Glasses-Type%7CElectric+showers%7C1.htm',
 u'http://www.argos.co.uk/static/Browse/ID72/33010334/c_1/1|category_root|Home+and+garden|33005908/c_2/2|33005908|Home+improvements|33007046/c_3/3|cat_33007046|Wallpaper+and+decorating|33010334.htm',
 u'http://www.argos.co.uk/static/Browse/ID72/33014350/c_1/1|category_root|Home+and+garden|33005908/c_2/2|33005908|DIY+tools+and+power+tools|33007178/c_3/3|cat_33007178|Workbenches|33014350.htm') + (u'http://www.argos.co.uk/static/Browse/ID72/33007659/c_1/1|category_root|Technology|33006169/c_2/2|cat_33006169|iPad%2C+tablets+and+E-readers|33007659.htm',
 u'http://www.argos.co.uk/static/Browse/ID72/33007795/c_1/1|category_root|Technology|33006169/c_2/2|cat_33006169|Laptops+and+PCs|33007795.htm',
 u'http://www.argos.co.uk/static/Browse/ID72/33007724/c_1/1|category_root|Technology|33006169/c_2/2|cat_33006169|Home+office|33007724.htm',
 u'http://www.argos.co.uk/static/Browse/ID72/33008085/c_1/1|category_root|Technology|33006169/c_2/2|cat_33006169|Mobile+phones+and+accessories|33008085.htm',
 u'http://www.argos.co.uk/static/Browse/ID72/33008137/c_1/1|category_root|Technology|33006169/c_2/2|cat_33006169|Video+games+and+consoles|33008137.htm',
 u'http://www.argos.co.uk/static/Browse/ID72/33008117/c_1/1|category_root|Technology|33006169/c_2/2|cat_33006169|Telephones+and+accessories|33008117.htm',
 u'http://www.argos.co.uk/static/Browse/ID72/42413313/c_1/1%7Ccategory_root%7CTechnology%7C33006169/c_2/2%7C33006169%7CMobile+phones+and+accessories%7C33008085/c_3/3%7Ccat_33008085%7CSmart+watches%7C42413313.htm?tag=ar:ddn:tn:smartwatches',
 u'http://www.argos.co.uk/static/Browse/ID72/33016389/c_1/1%7Ccategory_root%7CTechnology%7C33006169/c_2/2%7C33006169%7CHome+office%7C33007724/c_3/3%7Ccat_33007724%7CPrinters%7C33016389.htm?tag=ar:ddn:tn:printers',
 u'http://www.argos.co.uk/static/Browse/ID72/33014063/c_1/1%7Ccategory_root%7CTechnology%7C33006169/c_2/2%7C33006169%7CLaptops+and+PCs%7C33007795/c_3/3%7Ccat_33007795%7CLaptop+and+PC+accessories%7C33014063.htm?tag=ar:ddn:tn:laptoppcaccessories') + (u'http://www.argos.co.uk/static/Browse/ID72/40384661/c_1/1|category_root|Home+and+garden|33005908/c_2/2|33005908|Large+kitchen+appliances|33008255/c_3/3|cat_33008255|Built-in+integrated+appliances|40384661.htm',
 u'http://www.argos.co.uk/static/Browse/ID72/40835839/c_1/1|category_root|Home+and+garden|33005908/c_2/2|33005908|Floorcare|40835641/c_3/3|cat_40835641|Carpet+cleaners+and+accessories|40835839.htm',
 u'http://www.argos.co.uk/static/Browse/ID72/33014862/c_1/1|category_root|Home+and+garden|33005908/c_2/2|33005908|Large+kitchen+appliances|33008255/c_3/3|cat_33008255|Cooking|33014862.htm',
 u'http://www.argos.co.uk/static/Browse/ID72/33016098/c_1/1|category_root|Home+and+garden|33005908/c_2/2|33005908|Large+kitchen+appliances|33008255/c_3/3|cat_33008255|Fridge+freezers|33016098.htm',
 u'http://www.argos.co.uk/static/Browse/ID72/33017080/c_1/1|category_root|Home+and+garden|33005908/c_2/2|33005908|Kitchen+electricals|33007917/c_3/3|cat_33007917|Kettles|33017080.htm',
 u'http://www.argos.co.uk/static/Browse/ID72/33007917/c_1/1|category_root|Home+and+garden|33005908/c_2/2|cat_33005908|Kitchen+electricals|33007917.htm',
 u'http://www.argos.co.uk/static/Browse/ID72/33008255/c_1/1|category_root|Home+and+garden|33005908/c_2/2|cat_33005908|Large+kitchen+appliances|33008255.htm',
 u'http://www.argos.co.uk/static/Browse/ID72/40835833/c_1/1|category_root|Home+and+garden|33005908/c_2/2|33005908|Floorcare|40835641/c_3/3|cat_40835641|Handheld+and+cordless+cleaners|40835833.htm',
 u'http://www.argos.co.uk/static/Browse/ID72/33007608/c_1/1|category_root|Home+and+garden|33005908/c_2/2|cat_33005908|Heating+and+cooling|33007608.htm?tag=ar:ddn:hg:heatingcooling',
 u'http://www.argos.co.uk/static/Browse/ID72/33017029/c_1/1|category_root|Home+and+garden|33005908/c_2/2|33005908|Laundry+and+cleaning|33007566/c_3/3|cat_33007566|Irons|33017029.htm',
 u'http://www.argos.co.uk/static/Browse/ID72/40835793/c_1/1|category_root|Home+and+garden|33005908/c_2/2|33005908|Floorcare|40835641/c_3/3|cat_40835641|Steam+cleaners+and+accessories|40835793.htm',
 u'http://www.argos.co.uk/static/Browse/ID72/33014029/c_1/1|category_root|Home+and+garden|33005908/c_2/2|33005908|Kitchen+electricals|33007917/c_3/3|cat_33007917|Toasters|33014029.htm',
 u'http://www.argos.co.uk/static/Browse/ID72/33012718/c_1/1|category_root|Home+and+garden|33005908/c_2/2|33005908|Large+kitchen+appliances|33008255/c_3/3|cat_33008255|Tumble+dryers|33012718.htm',
 u'http://www.argos.co.uk/static/Browse/ID72/40835641/c_1/1|category_root|Home+and+garden|33005908/c_2/2|cat_33005908|Floorcare|40835641.htm',
 u'http://www.argos.co.uk/static/Browse/ID72/33012832/c_1/1|category_root|Home+and+garden|33005908/c_2/2|33005908|Large+kitchen+appliances|33008255/c_3/3|cat_33008255|Washing+machines|33012832.htm',
 u'http://www.argos.co.uk/static/Browse/ID72/33012700/c_1/1|category_root|Home+and+garden|33005908/c_2/2|33005908|Large+kitchen+appliances|33008255/c_3/3|cat_33008255|Washer+dryers|33012700.htm') + (u'http://www.argos.co.uk/static/Browse/ID72/33008394/c_1/1|category_root|Baby+and+nursery|33005732/c_2/2|cat_33005732|Sleep|33008394.htm',
 u'http://www.argos.co.uk/static/Browse/ID72/33008428/c_1/1|category_root|Baby+and+nursery|33005732/c_2/2|cat_33005732|Travel|33008428.htm',
 u'http://www.argos.co.uk/static/Browse/ID72/33006629/c_1/1|category_root|Baby+and+nursery|33005732/c_2/2|cat_33005732|Baby+toys|33006629.htm',
 u'http://www.argos.co.uk/static/Browse/ID72/33006591/c_1/1|category_root|Baby+and+nursery|33005732/c_2/2|cat_33005732|Feeding|33006591.htm',
 u'http://www.argos.co.uk/static/Browse/ID72/33006607/c_1/1|category_root|Baby+and+nursery|33005732/c_2/2|cat_33005732|Bathing+and+changing|33006607.htm',
 u'http://www.argos.co.uk/static/Browse/ID72/33006577/c_1/1|category_root|Baby+and+nursery|33005732/c_2/2|cat_33005732|Safety+and+health|33006577.htm',
 u'http://www.argos.co.uk/static/Browse/ID72/33008805/c_1/1|category_root|Clothing|33006249/c_2/2|cat_33006249|Baby+clothing|33008805.htm',
 u'http://www.argos.co.uk/static/Browse/ID72/33008180/c_1/1|category_root|Baby+and+nursery|33005732/c_2/2|cat_33005732|Maternity|33008180.htm',
 u'http://www.argos.co.uk/static/Browse/ID72/33007339/c_1/1|category_root|Baby+and+Nursery|33005732/c_2/2|cat_33005732|Baby+and+Christening+gifts|33007339.htm',
 u'http://www.argos.co.uk/static/Browse/ID72/50000040/c_1/1%7Ccategory_root%7CToys%7C33006252/c_2/2%7Ccat_33006252%7CBaby+and+pre-school+toys%7C50000040.htm',
 u'http://www.argos.co.uk/static/Search/searchTerm/BABY+AND+NURSERY+WOW+DEALS+AT+ARGOS.htm',
 u'http://www.argos.co.uk/static/Browse/ID72/33005732/c_1/2%7Ccategory_root%7CBaby+and+Nursery%7C33005732/r_001/1%7CPrice+Cut%7CYes%7C1.htm',
 u'http://www.argos.co.uk/static/Browse/ID72/42729002/c_1/1|category_root|Baby+and+nursery|33005732/c_2/2|cat_33005732|Clearance+Baby+and+Nursery|42729002.htm?tag=ar:dropdown:clearance:babynursery',
 u'http://www.argos.co.uk/static/Browse/ID72/33012089/c_1/1%7Ccategory_root%7CBaby+and+Nursery%7C33005732/c_2/2%7C33005732%7CTravel%7C33008428/c_3/3%7Ccat_33008428%7CPushchairs%7C33012089.htm',
 u'http://www.argos.co.uk/static/Browse/ID72/33012103/c_1/1|category_root|Baby+and+Nursery|33005732/c_2/2|33005732|Travel|33008428/c_3/3|cat_33008428|Travel+systems|33012103.htm',
 u'http://www.argos.co.uk/static/Browse/ID72/33021456/c_1/1|category_root|Baby+and+nursery|33005732/c_2/2|33005732|Baby+toys|33006629/c_3/3|cat_33006629|Baby+bouncers+and+swings|33009877/c_4/4|cat_33009877|Baby+bouncers|33021456.htm',
 u'http://www.argos.co.uk/static/Browse/ID72/33021876/c_1/1|category_root|Baby+and+Nursery|33005732/c_2/2|33005732|Travel|33008428/c_3/3|cat_33008428|Car+seats%2C+booster+seats+and+travel+accessories|33009371/c_4/4|cat_33009371|Car+seats|33021876.htm',
 u'http://www.argos.co.uk/static/Browse/ID72/33021964/c_1/1|category_root|Baby+and+Nursery|33005732/c_2/2|33005732|Safety+and+health|33006577/c_3/3|cat_33006577|Safety|33009404/c_4/4|cat_33009404|Safety+gates|33021964.htm',
 u'http://www.argos.co.uk/static/Browse/ID72/33010534/c_1/1|category_root|Baby+and+Nursery|33005732/c_2/2|33005732|Sleep|33008394/c_3/3|cat_33008394|Travel+cots|33010534.htm',
 u'http://www.argos.co.uk/static/Browse/ID72/33021683/c_1/1|category_root|Baby+and+Nursery|33005732/c_2/2|33005732|Feeding|33006591/c_3/3|cat_33006591|Highchairs+and+booster+seats|33009416/c_4/4|cat_33009416|Highchairs|33021683.htm',
 u'http://www.argos.co.uk/static/Browse/ID72/33009389/c_1/1|category_root|Baby+and+Nursery|33005732/c_2/2|33005732|Safety+and+health|33006577/c_3/3|cat_33006577|Baby+monitors+and+listening+systems|33009389.htm',
 u'http://www.argos.co.uk/static/Browse/ID72/33021492/c_1/1|category_root|Baby+and+nursery|33005732/c_2/2|33005732|Baby+toys|33006629/c_3/3|cat_33006629|Baby+walkers%2C+ride-ons+and+trikes|33009895/c_4/4|cat_33009895|Baby+walkers|33021492.htm',
 u'http://www.argos.co.uk/static/Browse/ID72/33011300/c_1/1|category_root|Baby+and+nursery|33005732/c_2/2|33005732|Sleep|33008394/c_3/3|cat_33008394|Nursery+furniture|33011300.htm',
 u'http://www.argos.co.uk/static/Browse/ID72/33021552/c_1/1%7Ccategory_root%7CBaby+and+nursery%7C33005732/c_2/2%7C33005732%7CFeeding%7C33006591/c_3/3%7Ccat_33006591%7CBaby+feeding+and+accessories%7C33009431/c_4/4%7Ccat_33009431%7CBaby+bottle+starter+kits+and+sets%7C33021552.htm',
 u'http://www.argos.co.uk/static/Browse/ID72/33011352/c_1/1%7Ccategory_root%7CBaby+and+nursery%7C33005732/c_2/2%7C33005732%7CSleep%7C33008394/c_3/3%7Ccat_33008394%7CCot+toys%2C+baby+mobiles+and+nightlights%7C33011352.htm',
 u'http://www.argos.co.uk/static/Browse/ID72/33009453/c_1/1%7Ccategory_root%7CBaby+and+nursery%7C33005732/c_2/2%7C33005732%7CBathing+and+changing%7C33006607/c_3/3%7Ccat_33006607%7CBaby+baths+and+accessories%7C33009453.htm',
 u'http://www.argos.co.uk/static/Browse/ID72/33009445/c_1/1%7Ccategory_root%7CBaby+and+nursery%7C33005732/c_2/2%7C33005732%7CBathing+and+changing%7C33006607/c_3/3%7Ccat_33006607%7CPotty+and+toilet+training%7C33009445.htm',
 u'http://www.argos.co.uk/static/Browse/ID72/33021634/c_1/1%7Ccategory_root%7CBaby+and+nursery%7C33005732/c_2/2%7C33005732%7CBathing+and+changing%7C33006607/c_3/3%7Ccat_33006607%7CBaby+changing%7C33009867/c_4/4%7Ccat_33009867%7CChanging+bags%7C33021634.htm',
 u'http://www.argos.co.uk/static/ArgosPromo3/includeName/Fisher_price_shop_home.htm',
 u'http://www.argos.co.uk/static/ArgosPromo3/includeName/mamas-and-papas-shop-home.htm',
 u'http://www.argos.co.uk/static/ArgosPromo3/includeName/Babystart-home.htm',
 u'http://www.argos.co.uk/static/Search/searchTerms/JOIE.htm',
 u'http://www.argos.co.uk/static/ArgosPromo3/includeName/chicco-shop-home.htm',
 u'http://www.argos.co.uk/static/ArgosPromo3/includeName/disney-baby-shop-home.htm',
 u'http://www.argos.co.uk/static/ArgosPromo3/includeName/maxi-cosi-shop-home.htm',
 u'http://www.argos.co.uk/static/ArgosPromo3/includeName/Tommee-Tippee.htm',
 u'http://www.argos.co.uk/static/Search/searchTerm/graco.htm',
 u'http://www.argos.co.uk/static/Search/searchTerm/BABY+EINSTEIN.htm?tag=ar:ddn:babyeinstein',
 u'http://www.argos.co.uk/static/Search/searchTerm/red+kite.htm?tag=ar:ddn:redkite',
 u'http://www.argos.co.uk/static/Search/searchTerm/BRITAX.htm?tag=ar:ddn:britax',
 u'http://www.argos.co.uk/static/Search/searchTerm/MOTOROLA.htm?tag=ar:ddn:motorola',
 u'http://www.argos.co.uk/static/ArgosPromo3/includeName/lindam-shop-home.htm?tag=ar:ddn:lindam') + (u'http://www.argos.co.uk/static/Browse/ID72/33007078/c_1/1|category_root|Home+and+garden|33005908/c_2/2|cat_33005908|Garden+furniture|33007078.htm',
 u'http://www.argos.co.uk/static/Browse/ID72/33011579/c_1/1%7Ccategory_root%7CHome+and+garden%7C33005908/c_2/2%7C33005908%7CLawnmowers+and+garden+power+tools%7C33007285/c_3/3%7Ccat_33007285%7CPressure+washers+and+accessories%7C33011579.htm',
 u'http://www.argos.co.uk/static/Browse/ID72/33011240/c_1/1%7Ccategory_root%7CHome+and+garden%7C33005908/c_2/2%7C33005908%7CLawnmowers+and+garden+power+tools%7C33007285/c_3/3%7Ccat_33007285%7CLawnmowers+and+accessories%7C33011240.htm',
 u'http://www.argos.co.uk/static/Browse/ID72/41047650/c_1/1%7Ccategory_root%7CHome+and+garden%7C33005908/c_2/2%7C33005908%7CBarbecues+and+garden+heating%7C41035253/c_3/3%7Ccat_41035253%7CBarbecues%2C+tools%2C+covers+and+fuel%7C41047650.htm',
 u'http://www.argos.co.uk/static/Browse/ID72/33013122/c_1/1%7Ccategory_root%7CHome+and+garden%7C33005908/c_2/2%7C33005908%7CConservatories%2C+sheds+and+greenhouses%7C33007618/c_3/3%7Ccat_33007618%7CSheds+and+bases%7C33013122.htm',
 u'http://www.argos.co.uk/static/Browse/ID72/33011117/c_1/1%7ccategory_root%7cHome+and+garden%7c33005908/c_2/2%7c33005908%7cGarden+furniture%7c33007078/c_3/3%7ccat_33007078%7cGazebos,+marquees+and+awnings%7c33011117.htm',
 u'http://www.argos.co.uk/static/Browse/ID72/33006928/c_1/1|category_root|Home+and+garden|33005908/c_2/2|cat_33005908|Garden+decoration+and+landscaping|33006928.htm',
 u'http://www.argos.co.uk/static/Browse/ID72/33011539/c_1/1%7Ccategory_root%7CHome+and+garden%7C33005908/c_2/2%7C33005908%7CGarden+decoration+and+landscaping%7C33006928/c_3/3%7Ccat_33006928%7CDecking%7C33011539.htm',
 u'http://www.argos.co.uk/static/Browse/ID72/33011136/c_1/1%7Ccategory_root%7CHome+and+garden%7C33005908/c_2/2%7C33005908%7CGarden+furniture%7C33007078/c_3/3%7Ccat_33007078%7CHot+tubs%2C+spas+and+accessories%7C33011136.htm',
 u'http://www.argos.co.uk/static/Browse/ID72/41047658/c_1/1|category_root|Home+and+garden|33005908/c_2/2|33005908|Barbecues+and+garden+heating|41035253/c_3/3|cat_41035253|Garden+heating|41047658.htm',
 u'http://www.argos.co.uk/static/Browse/ID72/33013130/c_1/1|category_root|Home+and+garden|33005908/c_2/2|33005908|Conservatories%2C+sheds+and+greenhouses|33007618/c_3/3|cat_33007618|Garden+storage+boxes+and+cupboards|33013130.htm',
 u'http://www.argos.co.uk/static/Browse/ID72/33007285/c_1/1%7Ccategory_root%7CHome+and+garden%7C33005908/c_2/2%7Ccat_33005908%7CLawnmowers+and+garden+power+tools%7C33007285.htm',
 u'http://www.argos.co.uk/static/Browse/ID72/33007279/c_1/1|category_root|Home+and+garden|33005908/c_2/2|cat_33005908|Gardening+tools|33007279.htm',
 u'http://www.argos.co.uk/static/Browse/ID72/33011215/c_1/1%7Ccategory_root%7CHome+and+garden%7C33005908/c_2/2%7Ccat_33005908%7CHoses+and+garden+watering%7C33011215.htm',
 u'http://www.argos.co.uk/static/Browse/ID72/33007618/c_1/1%7Ccategory_root%7CHome+and+garden%7C33005908/c_2/2%7Ccat_33005908%7CConservatories%2C+sheds+and+greenhouses%7C33007618.htm',
 u'http://www.argos.co.uk/static/ArgosPromo3/includeName/garden.htm?tag=ar:ddn:gardenliving')

    def parse(self, response):
        subcategories = response.xpath('//ul[@id="categoryList"]/li/a/@href').extract()
        for url in subcategories:
            url = response.urljoin(url.replace('/c_1', '/s/Price%3A+Low+-+High/pp/150/c_1'))
            yield Request(url,
                          callback=self.parse_listing)
        for request in self.parse_listing(response):
            yield request

    def parse_listing(self, response):

        next_page = response.xpath('//div[contains(@class,"pagination")]//a[text()="Next"]/@href').extract()
        if next_page:
            yield Request(response.urljoin(next_page[0]),
                          callback=self.parse_listing)

        products = response.xpath('//dt[@class="title"]/a/@href').extract()
        for url in products:
            yield Request(response.urljoin(url),
                          callback=self.parse_product)

    def parse_product(self, response):
        options = response.xpath('//ul[@class="swatch-carousel-items"]//a/@href').extract()
        for url in options:
            yield Request(response.urljoin(url),
                          callback=self.parse_product)

        loader = ProductLoader(item=Product(), response=response)

        # name
        name = response.xpath('//h2[@class="product-title"]/text()').extract()
        name = name[0].strip()
        loader.add_value('name', name)

        # price
        price = response.xpath('//span[@itemprop="price"]/text()').extract()
        loader.add_value('price', price)

        # sku
        sku = response.xpath('//div[contains(@class,"pdp-description")]//li/text()').re('EAN: (\d+)')
        if not sku:
            sku = response.xpath('//span[@itemprop="sku"]/text()').re('\d+')
            sku = [''.join(sku)] if sku else []
        if sku:
            loader.add_value('sku', sku[0])
        identifier = re.search('/partNumber/(.*)\.html?', response.url).group(1)
        loader.add_value('identifier', identifier)

        # category
        categories = response.xpath('//li[@class="breadcrumb-item"]/a/span/text()')[1:].extract()
        for category in categories:
            loader.add_value('category', category)

        # product image
        image_url = response.xpath('//meta[@itemprop="image"]/@content').extract()
        if image_url:
            loader.add_value('image_url', response.urljoin(image_url[0]))
        # url
        loader.add_value('url', response.url)
        # brand
        loader.add_xpath('brand', '//strong[@class="pdp-view-brand-main"]/text()')

        yield loader.load_item()
