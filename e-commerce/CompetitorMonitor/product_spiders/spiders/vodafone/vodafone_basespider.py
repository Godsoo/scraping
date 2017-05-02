from scrapy.spider import BaseSpider

from scrapy import log


class VodafoneBaseSpider(BaseSpider):


    def get_normalized_name(self, device_name):
        
        device_name = device_name.lower()	
        if 'iphone 6 plus' in device_name:
            if '16' in device_name:
                phone_name = 'iPhone 6 Plus 16GB'
            elif '64' in device_name:
                phone_name = 'iPhone 6 Plus 64GB'
            elif '128' in device_name:
                phone_name = 'iPhone 6 Plus 128GB'
        elif 'iphone 6' in device_name:
            if '16' in device_name:
                phone_name = 'iPhone 6 16GB'
            elif '64' in device_name:
                phone_name = 'iPhone 6 64GB'
            elif '128' in device_name:
                phone_name = 'iPhone 6 128GB'
        else:
            if 'samsung galaxy s5' in device_name:
                phone_name = 'Samsung Galaxy S5'

        return phone_name
