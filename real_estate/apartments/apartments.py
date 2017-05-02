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
    cur.execute("CREATE TABLE MarketRents(Id INT PRIMARY KEY AUTO_INCREMENT, ScrapeDateTime VARCHAR(25), TargetLat VARCHAR(15), TargetLng VARCHAR(15), PropertyName VARCHAR(50), PropertyAddress VARCHAR(50), PropertyLat VARCHAR(15), PropertyLng VARCHAR(15), ContactPhone VARCHAR(25), BedType VARCHAR(10), Bath VARCHAR(10), Floorplan VARCHAR(50), MinRent VARCHAR(10), MaxRent VARCHAR(10), Size VARCHAR(10), Amenities VARCHAR(2000))")

s = Scraper(use_cache=False, retries=3, timeout=30)
logger = s.logger

# apartments.py 40.78077 -73.96855 1500
# apartments.py 32.8185 -96.7296 0.1 2500
# apartments.py 32.8185 -96.7296 0.1 1000
# apartments.py 32.859795 -96.866549 0.03 1500

if __name__ == '__main__':

    if (len(sys.argv) < 5):
        print( '\n    Usage: apartments.py [targetLat] [targetLng] [radius as degree] [max price]' )
        print( '\n    e.g: apartments.py 40.78077 -73.96855 0.1 1500\n' )
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

        geocode_url = 'http://maps.googleapis.com/maps/api/geocode/json?latlng=%f,%f&sensor=false' % (targetLat, targetLng)
        doc_json = s.load_json(geocode_url)

        formatted_address = ''
        try:
            formatted_address = doc_json['results'][0]['formatted_address']
        except:
            logger.info('Bad lat/lng -> %f, %f' % targetLat, targetLng)
            exit()

        if ( re.search('USA$', formatted_address, re.S|re.I|re.M) is None ):
            logger.info('Outside of USA lat/lng -> %f, %f' % targetLat, targetLng)
            exit()

        formatted_address = re.sub('$[0-9]+\-[0-9]+',  '', formatted_address)
        formatted_address = re.sub('[0-9]+\,\sUSA',    '', formatted_address)
        formatted_address = re.sub('Unnamed[\w\s]+\,', '', formatted_address)
        formatted_address = formatted_address.split(',')[-2] + ', ' + formatted_address.split(',')[-1]

        logger.info('Search Address -> %s' % formatted_address)

        doc = s.load('https://www.apartments.com/')
        headers = {
                    'Host': 'www.apartments.com',
                    'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:51.0) Gecko/20100101 Firefox/51.0',
                    'Accept': 'application/json, text/javascript, */*; q=0.01',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Referer': 'https://www.apartments.com/',
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest' }

        geographysearch_url = 'https://www.apartments.com/services/geography/search/'
        geographysearch_payload = {"t":formatted_address, "l":[targetLng, targetLat]}
        doc_json = s.load_json(geographysearch_url, post=json.dumps(geographysearch_payload), headers=headers, merge_headers=True, ajax=True)

        # logger.info(doc_json)

        if ( len(doc_json) == 0 ):
            logger.info('No matching place -> ' + str(geographysearch_payload))
            exit()

        selected_place = doc_json[0]
        search_url = 'https://www.apartments.com/services/search/'
        search_payload = {
                          "Map": {
                            "Shape": None,
                            "BoundingBox": {
                              "UpperLeft": {
                                "Latitude": maxLat, # selected_place['BoundingBox']['UpperLeft']['Latitude'],
                                "Longitude": minLng, #selected_place['BoundingBox']['UpperLeft']['Longitude']
                              },
                              "LowerRight": {
                                "Latitude": minLat, # selected_place['BoundingBox']['LowerRight']['Latitude'],
                                "Longitude": maxLng, # selected_place['BoundingBox']['LowerRight']['Longitude']
                              }
                            }
                          },
                          "Geography": {
                            "ID": selected_place['ID'],
                            "Display": formatted_address,
                            "GeographyType": 2,
                            "Address": {
                              "City": formatted_address.split(',')[-2],
                              "State": formatted_address.split(',')[-1]
                            },
                            "Location": {
                              "Latitude": targetLat, # selected_place['Location']['Latitude'],
                              "Longitude": targetLng, # selected_place['Location']['Longitude']
                            },
                            "BoundingBox": {
                              "LowerRight": {
                                "Latitude": minLat, # selected_place['BoundingBox']['LowerRight']['Latitude'],
                                "Longitude": maxLng, # selected_place['BoundingBox']['LowerRight']['Longitude']
                              },
                              "UpperLeft": {
                                "Latitude": maxLat, # selected_place['BoundingBox']['UpperLeft']['Latitude'],
                                "Longitude": minLng, # selected_place['BoundingBox']['UpperLeft']['Longitude']
                              }
                            }
                          },
                          "Listing": {
                            "MinRentAmount": None,
                            "MaxRentAmount": maxPrice,
                            "MinBeds": None,
                            "MinBaths": None,
                            "PetFriendly": None,
                            "Style": None,
                            "Specialties": None,
                            "Ratings": None,
                            "Amenities": None,
                            "MinSquareFeet": None,
                            "MaxSquareFeet": None,
                            "GreenCertifications": None,
                            "Keywords": None
                          },
                          "Transportation": None,
                          "StateKey": None,
                          "Paging": {
                            "Page": None,
                            "CurrentPageListingKey": None
                          },
                          "SortOption": None,
                          "Mode": None,
                          "IsExtentLoad": None,
                          "IsBoundedSearch": None,
                          # "ResultSeed": 17389,
                          "SearchView": None,
                          "MapMode": None,
                          "Options": 1,
                          "SavedSearchKey": None }

        doc_json = s.load_json(search_url, post=json.dumps(search_payload), headers=headers, merge_headers=True, ajax=True)

        pin_counter = 0
        for pin in doc_json['PinsState']['Listings']:
            pin_url = re.sub('under\-' + str(maxPrice), pin['ListingId'], doc_json['UrlState']['Url'])
            # logger.info(pin_url)
            doc = s.load(pin_url)
            # logger.info(pin['ListingId'])

            address = ', '.join([doc.x('//span[@itemprop="address"]/meta[@itemprop="streetAddress"]/@content'), doc.x('//span[@itemprop="address"]/meta[@itemprop="addressLocality"]/@content'), doc.x('//span[@itemprop="address"]/meta[@itemprop="addressRegion"]/@content')]) + ' ' + doc.x('//span[@itemprop="address"]/meta[@itemprop="postalCode"]/@content')
            if ( address.replace(',', '').strip() == '' ):
                address = ', '.join([doc.x('//h2[@itemprop="address"]/span[@itemprop="streetAddress"]/text()'), doc.x('//h2[@itemprop="address"]/span[@itemprop="addressLocality"]/text()'), doc.x('//h2[@itemprop="address"]/span[@itemprop="addressRegion"]/text()')]) + ' ' + doc.x('//h2[@itemprop="address"]/span[@itemprop="postalCode"]/text()')

            amenities = ', '.join([amenity.x('text()').strip() for amenity in doc.q('//div[@data-analytics-name="amenities"]/section/div/h3[not(contains(text(), "Property Information") or contains(text(), "Pet Policy") or contains(text(), "Lease Length"))]/../ul/li')])
            contact_phone = doc.x('//span[@class="contactPhone"]/text()').strip()

            # for category in doc.q('//div[@data-tab-content-id="all"]/div/table[contains(@class, "availabilityTable")]/tbody/tr'):
            for category in doc.q('//div[@class="tabContent active"]/div/table[contains(@class, "availabilityTable")]/tbody/tr'):
                rent_val = category.x('td[@class="rent"]/text()').split('-')
                bed_type = category.x('td[@class="beds"]/span[@class="longText"]/text()').replace('Bedrooms', '').replace('Bedroom', '').strip()
                if ( bed_type == '' ):
                    logger.info(pin_url)
                    continue
                try:
                    minRent = int(re.sub('[^0-9]', '', rent_val[0].strip()))
                    maxRent = int(re.sub('[^0-9]', '', rent_val[1].strip())) if len(rent_val) > 1 else 0
                    if ( (minRent > maxPrice) or (maxRent > maxPrice) ):
                        continue
                except:
                    pass
                try:
                    propertyLat = float(doc.x('//meta[@property="place:location:latitude"]/@content'))
                    propertyLng = float(doc.x('//meta[@property="place:location:longitude"]/@content'))
                    if ( (propertyLat > maxLat) or (propertyLat < minLat) ):
                        continue
                    if ( (propertyLng > maxLng) or (propertyLng < minLng) ):
                        continue
                except:
                    pass
                size = re.sub('[^0-9^\-]', '', category.x('td[@class="sqft"]/text()')).strip().split('-')
                size = sum([int(val.strip()) for val in size]) / len(size)
                building_info = [ 'Scrape Date/Time', scrape_date,
                                  'Target Lat', targetLat, 'Target Lng', targetLng,
                                  'Property Name', doc.x('//h1[@itemprop="name"]/text()').strip(),
                                  'Property Address', address,
                                  'Property Lat', doc.x('//meta[@property="place:location:latitude"]/@content'), 'Property Lng', doc.x('//meta[@property="place:location:longitude"]/@content'),
                                  'Contact Phone', contact_phone if contact_phone != '' else 'not available',
                                  'Bed Type', bed_type,
                                  'Bath', re.sub('[^0-9]', '.5', category.x('td[@class="baths"]/span[@class="longText"]/text()').replace('Bathrooms', '').replace('Bathroom', '').strip()),
                                  'Floorplan', category.x('td[contains(@class, "name")]/text()').strip(),
                                  'Min Rent', rent_val[0].strip(),
                                  'Max Rent', ('$' + rent_val[1].strip()) if len(rent_val) > 1 else 'not available',
                                  # 'Size', re.sub('[^0-9^\,^\-]', '', category.x('td[@class="sqft"]/text()')).strip(),
                                  'Size', size,
                                  'Amenities', amenities
                                  ]
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
                logger.info(str(building_info))
                s.save(building_info, 'history.csv')
