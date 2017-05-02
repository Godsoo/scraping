# /media/simon/mine/mine/scrape/nicolas/program/hotelscraper/hotelscraper/spiders

from scrapy.spiders import Spider
from scrapy.selector import Selector
from scrapy.http import Request
from hotelscraper.items import HotelscraperItem
from selenium import webdriver

class bookingspider(Spider):
    name = "bookingspider"
    start_urls = [
        # "http://www.booking.com/searchresults.en-gb.html?aid=304142&label=gen173nr-1FCAEoggJCAlhYSDNiBW5vcmVmaDGIAQGYAS64AQ_IAQ_YAQHoAQH4AQuoAgM&sid=5cbc0943071c4be0f169e0311620a7b8&class_interval=1&dest_id=835&dest_id=835&dest_type=region&dest_type=region&group_adults=2&group_children=0&hlrd=0&label_click=undef&no_rooms=1&review_score_group=empty&room1=A%2CA&sb_price_type=total&score_min=0&src=index&ss=Bali%2C%20Indonesia&ss_raw=bali&ssb=empty&nflt=ht_id%3D204%3B&lsf=ht_id|204|841&unchecked_filter=hoteltype", # bali hotels
        # "http://www.booking.com/searchresults.html?aid=304142&label=gen173nr-1FCAEoggJCAlhYSDNiBW5vcmVmaDGIAQGYATG4AQrIAQXYAQHoAQH4AQKoAgM&sid=1f2c035bd5ad694c7f29f7e85bef83dc&class_interval=1&clear_ht_id=1&dest_id=835&dest_type=region&group_adults=2&group_children=0&hlrd=0&label_click=undef&no_rooms=1&review_score_group=empty&room1=A%2CA&sb_price_type=total&score_min=0&src=index&ss=Bali%2C Indonesia&ss_raw=bali&ssb=empty&nflt=ht_id%3D206%3B&lsf=ht_id%7C206%7C299&unchecked_filter=hoteltype", # bali resorts
        # "http://www.booking.com/searchresults.html?label=gen173nr-1FCAEoggJCAlhYSDNiBW5vcmVmaDGIAQGYATG4AQrIAQXYAQHoAQH4AQKoAgM&sid=1f2c035bd5ad694c7f29f7e85bef83dc&class_interval=1&dest_id=4209&dest_type=region&dtdisc=0&group_adults=2&group_children=0&hlrd=0&hyb_red=0&inac=0&label_click=undef&nha_red=0&no_rooms=1&postcard=0&redirected_from_city=0&redirected_from_landmark=0&redirected_from_region=0&review_score_group=empty&room1=A%2CA&sb_price_type=total&score_min=0&src=searchresults&ss=Gili Islands%2C Indonesia&ss_all=0&ss_raw=gili island&ssb=empty&sshis=0&ssne_untouched=Bali&nflt=ht_id%3D204%3B&lsf=ht_id%7C204%7C31&unchecked_filter=hoteltype", # gili islands hotels
        # "http://www.booking.com/searchresults.html?aid=304142&label=gen173nr-1FCAEoggJCAlhYSDNiBW5vcmVmaDGIAQGYATG4AQrIAQXYAQHoAQH4AQKoAgM&sid=1f2c035bd5ad694c7f29f7e85bef83dc&class_interval=1&dest_id=4209&dest_type=region&group_adults=2&group_children=0&hlrd=0&label_click=undef&no_rooms=1&review_score_group=empty&room1=A%2CA&sb_price_type=total&score_min=0&src=searchresults&ss=Gili Islands%2C Indonesia&ss_raw=gili island&ssb=empty&ssne_untouched=Bali&clear_ht_id=1&unchecked_filter=hoteltype&nflt=ht_id%3D206%3B&lsf=ht_id%7C206%7C20", # gili islands resorts
        # "http://www.booking.com/searchresults.en-gb.html?label=gen173nr-1FCAEoggJCAlhYSDNiBW5vcmVmaDGIAQGYATG4AQrIAQXYAQHoAQH4AQKoAgM&lang=en-gb&sid=5cbc0943071c4be0f169e0311620a7b8&sb=1&src=searchresults&src_elem=sb&error_url=http%3A%2F%2Fwww.booking.com%2Fsearchresults.en-gb.html%3Flabel%3Dgen173nr-1FCAEoggJCAlhYSDNiBW5vcmVmaDGIAQGYATG4AQrIAQXYAQHoAQH4AQKoAgM%3Bsid%3D5cbc0943071c4be0f169e0311620a7b8%3Bcheckin_month%3D10%3Bcheckin_monthday%3D4%3Bcheckin_year%3D2016%3Bcheckout_month%3D10%3Bcheckout_monthday%3D5%3Bcheckout_year%3D2016%3Bclass_interval%3D1%3Bdest_id%3D153%3Bdest_type%3Dcountry%3Bdtdisc%3D0%3Bgroup_adults%3D2%3Bgroup_children%3D0%3Bhlrd%3D0%3Bhyb_red%3D0%3Binac%3D0%3Blabel_click%3Dundef%3Bnflt%3Dht_id%253D204%253B%3Bnha_red%3D0%3Bno_rooms%3D1%3Boffset%3D0%3Bpostcard%3D0%3Bredirected_from_city%3D0%3Bredirected_from_landmark%3D0%3Bredirected_from_region%3D0%3Breview_score_group%3Dempty%3Broom1%3DA%252CA%3Bsb_price_type%3Dtotal%3Bscore_min%3D0%3Bsrc%3Dsearchresults%3Bsrc_elem%3Dsb%3Bss%3DNicaragua%3Bss_all%3D0%3Bssb%3Dempty%3Bsshis%3D0%3Bssne%3DNicaragua%3Bssne_untouched%3DNicaragua%26%3B&ss=Nicaragua&ssne=Nicaragua&ssne_untouched=Nicaragua&dest_id=153&dest_type=country&checkin_monthday=4&checkin_month=10&checkin_year=2016&checkout_monthday=5&checkout_month=10&checkout_year=2016&room1=A%2CA&no_rooms=1&group_adults=2&group_children=0&track_sskfc=1&nflt=ht_id%3D204%3B", # nicaragua hotels
        # "http://www.booking.com/searchresults.en-gb.html?aid=304142&label=gen173nr-1FCAEoggJCAlhYSDNiBW5vcmVmaDGIAQGYATG4AQrIAQXYAQHoAQH4AQKoAgM&sid=5cbc0943071c4be0f169e0311620a7b8&checkin_month=10&checkin_monthday=4&checkin_year=2016&checkout_month=10&checkout_monthday=5&checkout_year=2016&class_interval=1&clear_ht_id=1&dest_id=153&dest_type=country&group_adults=2&group_children=0&hlrd=0&label_click=undef&no_rooms=1&review_score_group=empty&room1=A%2CA&sb_price_type=total&score_min=0&src=searchresults&ss=Nicaragua&ssb=empty&ssne=Nicaragua&ssne_untouched=Nicaragua&nflt=ht_id%3D206%3B&lsf=ht_id%7C206%7C19&unchecked_filter=hoteltype", # nicaragua resorts
        # "http://www.booking.com/searchresults.html?label=gen173nr-1FCAEoggJCAlhYSDNiBW5vcmVmaDGIAQGYATG4AQrIAQXYAQHoAQH4AQKoAgM&sid=1f2c035bd5ad694c7f29f7e85bef83dc&class_interval=1&dest_id=52&dest_type=country&dtdisc=0&group_adults=2&group_children=0&hlrd=0&hyb_red=0&inac=0&label_click=undef&nha_red=0&no_rooms=1&postcard=0&redirected_from_city=0&redirected_from_landmark=0&redirected_from_region=0&review_score_group=empty&room1=A%2CA&sb_price_type=total&score_min=0&src=searchresults&ss=Costa Rica&ss_all=0&ss_raw=costa rica&ssb=empty&sshis=0&ssne_untouched=Nicaragua&nflt=ht_id%3D204%3B&lsf=ht_id%7C204%7C692&unchecked_filter=hoteltype", # costa rica hotels
        # "http://www.booking.com/searchresults.html?aid=304142&label=gen173nr-1FCAEoggJCAlhYSDNiBW5vcmVmaDGIAQGYATG4AQrIAQXYAQHoAQH4AQKoAgM&sid=1f2c035bd5ad694c7f29f7e85bef83dc&class_interval=1&dest_id=52&dest_type=country&group_adults=2&group_children=0&hlrd=0&label_click=undef&no_rooms=1&review_score_group=empty&room1=A%2CA&sb_price_type=total&score_min=0&src=searchresults&ss=Costa Rica&ss_raw=costa rica&ssb=empty&ssne_untouched=Nicaragua&clear_ht_id=1&unchecked_filter=hoteltype&nflt=ht_id%3D206%3B&lsf=ht_id%7C206%7C91", # costa rica resorts
        "http://www.booking.com/searchresults.html?aid=304142&label=gen173nr-1FCAEoggJCAlhYSDNiBW5vcmVmaDGIAQGYATG4AQrIAQXYAQHoAQH4AQKoAgM&sid=5cbc0943071c4be0f169e0311620a7b8&checkin_month=10&checkin_monthday=5&checkin_year=2016&checkout_month=10&checkout_monthday=6&checkout_year=2016&class_interval=1&dest_id=835&dest_type=region&group_adults=2&group_children=0&hlrd=0&label_click=undef&no_rooms=1&review_score_group=empty&room1=A%2CA&sb_price_type=total&score_min=0&src=searchresults&ss=Bali%2C%20Indonesia&ss_raw=bali&ssb=empty&ssne_untouched=Gili%20Islands&nflt=ht_id%3D204%3Bht_id%3D206%3B&lsf=ht_id|206|299&unchecked_filter=hoteltype", # bali indonesia usd
        # "http://www.booking.com/searchresults.html?aid=304142&label=gen173nr-1FCAEoggJCAlhYSDNiBW5vcmVmaDGIAQGYATG4AQrIAQXYAQHoAQH4AQKoAgM&sid=5cbc0943071c4be0f169e0311620a7b8&checkin_month=10&checkin_monthday=5&checkin_year=2016&checkout_month=10&checkout_monthday=6&checkout_year=2016&class_interval=1&clear_ht_id=1&dest_id=4209&dest_type=region&group_adults=2&group_children=0&hlrd=0&label_click=undef&no_rooms=1&review_score_group=empty&room1=A%2CA&sb_price_type=total&score_min=0&src=searchresults&ss=Gili%20Islands%2C%20Indonesia&ss_raw=gili%20islands&ssb=empty&ssne_untouched=Nicaragua&nflt=ht_id%3D204%3Bht_id%3D206%3B&lsf=ht_id|206|20&unchecked_filter=hoteltype", # gili islands indonesia usd
        # "http://www.booking.com/searchresults.html?aid=304142&label=gen173nr-1FCAEoggJCAlhYSDNiBW5vcmVmaDGIAQGYATG4AQrIAQXYAQHoAQH4AQKoAgM&sid=5cbc0943071c4be0f169e0311620a7b8&checkin_month=10&checkin_monthday=5&checkin_year=2016&checkout_month=10&checkout_monthday=6&checkout_year=2016&class_interval=1&dest_id=153&dest_type=country&group_adults=2&group_children=0&hlrd=0&label_click=undef&no_rooms=1&review_score_group=empty&room1=A%2CA&sb_price_type=total&score_min=0&src=searchresults&ss=Nicaragua&ss_raw=nicaragua&ssb=empty&ssne_untouched=Costa%20Rica&nflt=ht_id%3D204%3Bht_id%3D206%3B&lsf=ht_id|206|19&unchecked_filter=hoteltype", # nicaragua usd
        # "http://www.booking.com/searchresults.html?aid=304142&label=gen173nr-1FCAEoggJCAlhYSDNiBW5vcmVmaDGIAQGYATG4AQrIAQXYAQHoAQH4AQKoAgM&sid=5cbc0943071c4be0f169e0311620a7b8&checkin_month=10&checkin_monthday=5&checkin_year=2016&checkout_month=10&checkout_monthday=6&checkout_year=2016&class_interval=1&dest_id=52&dest_type=country&group_adults=2&group_children=0&hlrd=0&label_click=undef&no_rooms=1&review_score_group=empty&room1=A%2CA&sb_price_type=total&score_min=0&src=searchresults&ss=Costa%20Rica&ssb=empty&ssne=Costa%20Rica&ssne_untouched=Costa%20Rica&nflt=ht_id%3D204%3Bht_id%3D206%3B&lsf=ht_id|206|91&unchecked_filter=hoteltype", # costa rica usd
        ]

    def __init__(self):

        self.profile = webdriver.FirefoxProfile("/home/simon/.mozilla/firefox/yt6zm4r7.default")
        self.driver = webdriver.Firefox(self.profile)


    def parse(self, response):

        self.driver.get( "http://www.booking.com/searchresults.html?aid=304142&label=gen173nr-1FCAEoggJCAlhYSDNiBW5vcmVmaDGIAQGYATG4AQrIAQXYAQHoAQH4AQKoAgM&sid=5cbc0943071c4be0f169e0311620a7b8&checkin_month=10&checkin_monthday=5&checkin_year=2016&checkout_month=10&checkout_monthday=6&checkout_year=2016&class_interval=1&dest_id=835&dest_type=region&group_adults=2&group_children=0&hlrd=0&label_click=undef&no_rooms=1&review_score_group=empty&room1=A%2CA&sb_price_type=total&score_min=0&src=searchresults&ss=Bali%2C%20Indonesia&ss_raw=bali&ssb=empty&ssne_untouched=Gili%20Islands&nflt=ht_id%3D204%3Bht_id%3D206%3B&lsf=ht_id|206|299&unchecked_filter=hoteltype" )

        # self.driver.implicitly_wait(40)

        page_num = 0

        while  ( page_num < 67 ):
            
            hxs = Selector(text=self.driver.page_source)

            while ( int(hxs.xpath('//li[@class="sr_pagination_item current"]/a/text()').extract()[0]) == page_num ) :

                hxs = Selector(text=self.driver.page_source)

            # for hotel in hxs.xpath('//h3[@class="sr-hotel__title  "]'):
            for hotel in hxs.xpath('//div[@class="sr_item_content sr_item_content_slider_wrapper"]'):

                request = Request(url="http://www.booking.com" + hotel.xpath('div/div/h3/a[@class="hotel_name_link url"]/@href').extract()[0], callback=self.parse_hotel)

                if ( len(hotel.xpath('div/div/table/tbody/tr/td/div/strong/b[contains(text(), "US$")]/text()').extract()) > 0 ) :

                    request.meta['price'] = hotel.xpath('div/div/table/tbody/tr/td/div/strong/b[contains(text(), "US$")]/text()').extract()

                elif ( len(hotel.xpath('div/div/div/div/div/div[contains(text(), "US$")]/text()').extract()) > 0 ) :

                    request.meta['price'] = hotel.xpath('div/div/div/div/div/div[contains(text(), "US$")]/text()').extract()

                # elif ( len(hotel.xpath('//span[@class="dod-banner-price__number"]/text()').extract()) > 0 ) :

                #     request.meta['price'] = hotel.xpath('//span[@class="dod-banner-price__number"]/text()').extract()

                # elif ( len(hotel.xpath('//div[@class="sr-soldout-price"]/text()').extract()) > 0 ) :

                #     request.meta['price'] = hotel.xpath('//div[@class="sr-soldout-price"]/text()').extract()

                else :

                    request.meta['price'] = '0'

                yield request
                # item = HotelscraperItem()

                # item['name'] = hotel.xpath('div/div/h3/a[@class="hotel_name_link url"]/@href').extract()

                # yield item
                # yield Request(url="http://www.booking.com" + hotel.xpath('//a[@class="hotel_name_link url"]/@href').extract()[0], callback=self.parse_hotel)

            self.driver.find_element_by_xpath( '//a[contains(text(), "Next page")]' ).click()

            self.driver.implicitly_wait(40)

            page_num = page_num + 1


        # for hotel in response.xpath('//h3[@class="sr-hotel__title  "]'):

        #     # item = HotelscraperItem()
        #     # item['name'] = hotel.xpath('a[@class="hotel_name_link url"]/@href').extract()
        #     # yield item

        #     yield Request(url="http://www.booking.com" + hotel.xpath('a[@class="hotel_name_link url"]/@href').extract()[0], callback=self.parse_hotel)

        # # if ( self.page_num < 1 ) :
        # # while ( len(response.xpath('//a[contains(text(), "Next page")]/@href').extract()) != 0 ) :

        # #     self.page_num = self.page_num + 1

        # if ( len(response.xpath('//a[contains(text(), "Next page")]/@href').extract()) > 0 ) :

        #      yield Request(url=response.xpath('//a[contains(text(), "Next page")]/@href').extract()[0], callback=self.parse)



    def parse_hotel(self, response):

        item = HotelscraperItem()

        item['name']  = response.xpath('//span[@id="hp_hotel_name"]/text()').extract()

        item['area']  = response.xpath('//span[@class="inline-block hp_address_subtitle jq_tooltip"]/text()').extract()

        if ( item['area'][0].find('Indonesia', 0) != -1 ) :
            item['country'] = "Indonesia"
        elif ( item['area'][0].find('Nicaragua', 0) != -1 ) :
            item['country'] = "Nicaragua"
        elif ( item['area'][0].find('Costa Rica', 0) != -1 ) :
            item['country'] = "Costa Rica"

        item['rooms'] = response.xpath('//p[@class="summary  hotel_meta_style"]/br/following-sibling::text()').extract()

        if ( len(response.xpath('//p[@class="summary  hotel_meta_style"]/br/following-sibling::a/text()').extract()) > 0 ):
            item['rooms'][0] = item['rooms'][0] + response.xpath('//p[@class="summary  hotel_meta_style"]/br/following-sibling::a/text()').extract()[0]


        if ( item['rooms'][0].find('Hotel Chain:', 0) != -1 ):

            item['chain']    = item['rooms'][0][item['rooms'][0].find('Hotel Chain:', 0) : len(item['rooms'][0])]
            item['rooms'][0] = item['rooms'][0][0 : item['rooms'][0].find('Hotel Chain:', 0) - 2]
        else:
            item['chain'] = "Independent"

        item['price'] = response.meta['price']

        yield item


