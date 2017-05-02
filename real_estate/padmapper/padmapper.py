from scrapex import *
import time
import sys
import csv
import re
import json
import MySQLdb as mdb

con = mdb.connect('localhost', 'testuser', 'test623', 'testdb');
with con:
    cur = con.cursor()
    cur.execute("DROP TABLE IF EXISTS MarketRents")
    cur.execute("CREATE TABLE MarketRents(Id INT PRIMARY KEY AUTO_INCREMENT, ScrapeDateTime VARCHAR(25), TargetLat VARCHAR(15), TargetLng VARCHAR(15), PropertyName VARCHAR(50), PropertyAddress VARCHAR(50), PropertyLat VARCHAR(15), PropertyLng VARCHAR(15), ContactPhone VARCHAR(25), BedType VARCHAR(10), Bath VARCHAR(10), Floorplan VARCHAR(50), MinRent VARCHAR(10), MaxRent VARCHAR(10), Size VARCHAR(10), Amenities VARCHAR(200))")

s = Scraper(use_cache=False, retries=3, timeout=30)
logger = s.logger

if __name__ == '__main__':

    if (len(sys.argv) < 5):
        print( '\n    Usage: padmapper.py [targetLat] [targetLng] [radius as degree] [max price]' )
        print( '\n    e.g: padmapper.py 33.6 -117.6 0.1 2150\n' )
    else:
        scrape_date = time.strftime("%m/%d/%Y %H:%M:%S", time.gmtime())
        
        targetLat = float(sys.argv[1])
        targetLng = float(sys.argv[2])
        radius = float(sys.argv[3])

        maxPrice = int(sys.argv[4])

        minLng = targetLng - radius
        minLat = targetLat - radius
        maxLng = targetLng + radius
        maxLat = targetLat + radius

        apartments_url = 'https://www.padmapper.com/apartments/under-%d?box=%f,%f,%f,%f&property-categories=apartment,house' % (maxPrice, minLng, minLat, maxLng, maxLat)
        bundle_url = 'https://www.padmapper.com/api/t/1/bundle'
        listable_url = 'https://www.padmapper.com/api/t/1/pages/listables'
        building_url = 'https://www.padmapper.com/api/t/1/pages/buildings/'

        amenities = ["Known","On Site Laundry","Air Conditioning","Ceiling Fan","High Ceilings","Assigned Parking","Fireplace","Dishwasher","Balcony","Garden","Deck","Hardwood Floor","Carpet","Furnished","Central Heat","Walk In Closet","In Unit Laundry"]

        # to get the cookies like {"xz_token":"cc1uf32wce9.bwrcsju4a","csrf":"Q7sJjp9Ai9TesjIZEGxbtm77WKXrexMW"}
        logger.info('apartments_url -> %s' % apartments_url)
        doc = s.load(apartments_url)

        logger.info('bundle_url -> %s' % bundle_url)

        # {"xz_token":"cc1uf32wce9.bwrcsju4a","csrf":"Q7sJjp9Ai9TesjIZEGxbtm77WKXrexMW"}
        bundle_json = s.load_json(bundle_url)

        xz_token = bundle_json['xz_token']
        csrf = bundle_json['csrf']

        logger.info('xz_token -> %s, csrf -> %s' % (xz_token, csrf))

        offset = 0
        interval = 100
        results_num = 0

        headers = {'X-Zumper-XZ-Token': xz_token, 'X-CSRFToken': csrf, 'Content-Type': 'application/json;charset=utf-8',
                   'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:50.0) Gecko/20100101 Firefox/50.0',
                   'Host': 'www.padmapper.com', 'Accept': 'application/json, text/plain, */*', 'Accept-Language': 'en-US,en;q=0.5',
                   'Accept-Encoding': 'gzip, deflate, br', 'Referer': doc.status.final_url }

        while ( True ):
            listable_payload = {   "limit": interval,
                                "matching": 'true',
                                "maxPrice": maxPrice,
                                  "maxLat": maxLat,
                                  "minLat": minLat,
                                  "maxLng": maxLng,
                                  "minLng": minLng,
                                  "offset": offset, "propertyCategories": ["apartment","house"]}

            listable_json = s.load_json(listable_url, post=json.dumps(listable_payload), headers=headers, merge_headers=True)
            for building in listable_json['listables']:
                if ( (building['building_id'] is None) or (building['building_id'] == 0) ):
                    contact_phone = building['phone']
                    if ( (contact_phone is None) or (contact_phone == '') ):
                        contact_phone = 'not available'
                    building_info = [ 'Scrape Date/Time', scrape_date,
                                      'Target Lat', targetLat, 'Target Lng', targetLng,
                                      'Property Name', building['building_name'] if (building['building_name'] and (building['building_name'] != '')) else building['agent_name'],
                                      'Property Address', ', '.join([building['address'], building['city'], building['state']]),
                                      'Property Lat', building['lat'], 'Property Lng', building['lng'],
                                      'Contact Phone', contact_phone,
                                      'Bed Type', building['min_bedrooms'],
                                      'Bath', building['min_bathrooms'],
                                      'Floorplan', '',
                                      'Min Rent', building['min_price'],
                                      'Max Rent', building['max_price'] if building['max_price'] else 'not available',
                                      'Size', '',
                                      'Amenities', '' ]
                    with con:
                        cur = con.cursor()
                        cur.execute("INSERT INTO MarketRents(ScrapeDateTime, TargetLat, TargetLng, PropertyName, PropertyAddress, PropertyLat, PropertyLng, ContactPhone, BedType, Bath, Floorplan, MinRent, MaxRent, Size, Amenities) VALUES('%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s')" % 
                               (
                                building_info[1],                     # building_info['Scrape Date/Time'],
                                building_info[3], building_info[5],   # building_info['Target Lat'], building_info['Target Lng'],
                                building_info[7],                     # building_info['Property Name'],
                                building_info[9],                     # building_info['Property Address'],
                                building_info[11], building_info[13], # building_info['Property Lat'], building_info['Property Lng'],
                                building_info[15],                    # building_info['Contact Phone'],
                                building_info[17],                    # building_info['Bed Type'],
                                building_info[19],                    # building_info['Bath'],
                                building_info[21],                    # building_info['Floorplan'],
                                building_info[23],                    # building_info['Min Rent'],
                                building_info[25],                    # building_info['Max Rent'],
                                building_info[27],                    # building_info['Size'],
                                building_info[29],                    # building_info['Amenities'],
                                ))

                    s.save(building_info, 'history.csv')
                    logger.info(building_info)
                    continue
                building_json = s.load_json(building_url + str(building['building_id']), headers={'X-Zumper-XZ-Token': xz_token, 'X-CSRFToken': csrf}, merge_headers=True)

                property_name = building_json['name']
                property_address = ', '.join([building_json['address'], building_json['city'], building_json['state'], building_json['country']])
                property_lat = building_json['lat']
                property_lng = building_json['lng']
                contact_phone = building_json['phone']
                if ( (contact_phone is None) or (contact_phone == '') ):
                    contact_phone = 'not available'

                studios_num = 0
                one_bedrooms_num = 0
                two_bedrooms_num = 0
                thr_bedrooms_num = 0

                studios_min_price = 0
                studios_max_price = 0
                one_bedrooms_min_price = 0
                one_bedrooms_max_price = 0
                two_bedrooms_min_price = 0
                two_bedrooms_max_price = 0
                thr_bedrooms_min_price = 0
                thr_bedrooms_max_price = 0

                floorplan_listings = {'Studio': [], '1 Bedroom': [], '2 Bedroom': [], '3 Bedroom': []}

                for floorplan in building_json['floorplan_listings']:
                    if ( floorplan is None ):
                        continue
                    if ((floorplan['min_price'] != 0 ) and (floorplan['price'] != 0 ) and (floorplan['is_messageable'] == True)):
                        building_info = [ 'Scrape Date/Time', scrape_date,
                                          'Target Lat', targetLat, 'Target Lng', targetLng,
                                          'Property Name', property_name,
                                          'Property Address', property_address,
                                          'Property Lat', property_lat, 'Property Lng', property_lng,
                                          'Contact Phone', contact_phone,
                                          'Bed Type', 'Studio' if 'Studio' in floorplan['page_title'] else floorplan['bedrooms'],
                                          'Bath', floorplan['bathrooms'],
                                          'Floorplan', floorplan['title'],
                                          'Min Rent', floorplan['min_price'],
                                          'Max Rent', floorplan['max_price'] if floorplan['max_price'] else 'not available',
                                          'Size', floorplan['square_feet'],
                                          'Amenities', ', '.join([amenities[index] for index in floorplan['amenities']]) if floorplan['amenities'] else '' ]
                        with con:
                            cur = con.cursor()
                            cur.execute("INSERT INTO MarketRents(ScrapeDateTime, TargetLat, TargetLng, PropertyName, PropertyAddress, PropertyLat, PropertyLng, ContactPhone, BedType, Bath, Floorplan, MinRent, MaxRent, Size, Amenities) VALUES('%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s')" % 
                                   (
                                    building_info[1],                     # building_info['Scrape Date/Time'],
                                    building_info[3], building_info[5],   # building_info['Target Lat'], building_info['Target Lng'],
                                    building_info[7],                     # building_info['Property Name'],
                                    building_info[9],                     # building_info['Property Address'],
                                    building_info[11], building_info[13], # building_info['Property Lat'], building_info['Property Lng'],
                                    building_info[15],                    # building_info['Contact Phone'],
                                    building_info[17],                    # building_info['Bed Type'],
                                    building_info[19],                    # building_info['Bath'],
                                    building_info[21],                    # building_info['Floorplan'],
                                    building_info[23],                    # building_info['Min Rent'],
                                    building_info[25],                    # building_info['Max Rent'],
                                    building_info[27],                    # building_info['Size'],
                                    building_info[29],                    # building_info['Amenities'],
                                    ))

                        s.save(building_info, 'history.csv')
                        logger.info(building_info)
                results_num = results_num + 1
            if (len(listable_json['listables']) < interval):
                break
            offset = offset + interval

        # logger.info('############################')
        # logger.info('%d Results' % results_num)

