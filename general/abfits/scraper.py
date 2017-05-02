# /mnt/hgfs/D/mine/scrape/job/Sudhanshu
# http://www.abfits.com/m-tops/?format=json

from bs4 import BeautifulSoup
import pandas as pd
from lxml import html
import lxml.etree as ET
import csv
import urllib3
import json
import requests
import sys

# python3 scraper.py mens-tops@http://www.abfits.com/m-tops/ mens-bottoms@http://www.abfits.com/mbottoms/ bags@http://www.abfits.com/bags/
# python3 scraper.py bags@http://www.abfits.com/bags/ mens-tops@http://www.abfits.com/m-tops/ mens-bottoms@http://www.abfits.com/mbottoms/

newjson = {'categories':[]}

def ExtractJSON(url, cat):

	categories_num = 0

	jsonurl = url + '?format=json'

	myjson = {}

	print( cat, ' ', jsonurl )

	#################   request with url    ##################

	myhtml = requests.get(jsonurl)

	# f = open(cat+'.json',"w") #opens file with name of "test.txt"
	# f.write(myhtml.text) 
	# f.close()

	# Load the parsed page into a JSON object.
	myjson = json.loads(myhtml.text)


	################    open with file      ##################

	# with open('abfits-m-tops.json') as f:
	# 	myjson = json.load(f)


	categories = myjson['collection']['categories']

	if ( categories ) :
		for category in categories :
			# print( category )
			newjson['categories'].append( {'title' : (cat + '/' + category), 
												'url' : url + '?category=' + category,
										   'products' : []} )

			categories_num = categories_num + 1


	if ( categories_num == 0 ) :

			newjson['categories'].append( {'title' : (cat), 
												'url' : url,
										   'products' : []} )


	items = myjson['items']

	for item in items :

		if ( 'categories' in item ) :

			product_index = 0

			for i in range(len(newjson['categories'])) :
			# for category in newjson[0]['categories'] :

				if ( ((categories_num == 0) and (len(item['categories']) == 0)) or 
				     ((categories_num != 0) and (len(item['categories']) != 0) and (newjson['categories'][i]['title'].find(item['categories'][0]) >= 0)) ) :

					p_images = {}

					p_variants = []

					if ( 'title' in item ) :
						p_title = item['title']
					else :
						p_title = None

					if ( 'excerpt' in item ) :
						p_description = item['excerpt']
					else :
						p_description = None

					if ( 'fullUrl' in item ) :
						p_url = url + item['fullUrl'][1:].split('/')[1]
					else :
						p_url = None


					if ( 'priceCents' in item ) :

						temp_price = item['priceCents']

						if ( temp_price == 0 ) :
							p_price = 0
						else :
							temp_price = str(temp_price)
							p_price = temp_price[0:(len(temp_price) - 2)] + '.' + temp_price[len(temp_price) - 2:]

					else :
						p_price = None


					if ( 'salePriceCents' in item ) :

						temp_price = item['salePriceCents']

						if ( temp_price == 0 ) :
							p_list_price = 0
						else :
							temp_price = str(temp_price)
							p_list_price = temp_price[0:(len(temp_price) - 2)] + '.' + temp_price[len(temp_price) - 2:]

					else :
						p_list_price = None

					if ( 'width' in item ) :
						p_width = item['width']
					else :
						p_width = None

					if ( 'height' in item ) :
						p_height = item['height']
					else :
						p_height = None

					if ( 'weight' in item ) :
						p_weight = item['weight']
					else :
						p_weight = None

					if ( 'len' in item ) :
						p_len = item['len']
					else :
						p_len = None



					if ( 'items' in item ) :

						inner_items = item['items']

						for j in range(len(inner_items)) :

							if ( 'assetUrl' in inner_items[j] ) :

								# p_images.append( { j + 1 : inner_items[j]['assetUrl'] } )
								p_images[j + 1] = inner_items[j]['assetUrl']

					if ( 'variants' in item ) :

						p_variants = item['variants']

						for j in range(len(p_variants)) :

							del p_variants[j]['unlimited']
							# del p_variants[j]['weight']
							# del p_variants[j]['width']
							# del p_variants[j]['height']
							# del p_variants[j]['len']
							del p_variants[j]['onSale']
							del p_variants[j]['optionValues']

							temp_price = p_variants[j]['price']

							if ( temp_price == 0 ) :
								p_variants[j]['price'] = 0
							else :
								temp_price = str(temp_price)
								p_variants[j]['price'] = temp_price[0:(len(temp_price) - 2)] + '.' + temp_price[len(temp_price) - 2:]

							if ( p_variants[j]['qtyInStock'] > 0 ) :
								p_variants[j]['in-stock'] = True
							else :
								p_variants[j]['in-stock'] = False

							del p_variants[j]['qtyInStock']


							if ( 'Size' in p_variants[j]['attributes'] ) :
								p_variants[j]['size'] = p_variants[j]['attributes']['Size']
							else :
								p_variants[j]['size'] = None

							del p_variants[j]['attributes']


							temp_price = p_variants[j]['salePrice']

							if ( temp_price == 0 ) :
								p_variants[j]['list-price'] = 0
							else :
								temp_price = str(temp_price)
								p_variants[j]['list-price'] = temp_price[0:(len(temp_price) - 2)] + '.' + temp_price[len(temp_price) - 2:]

							del p_variants[j]['salePrice']


							if ( 'color' not in p_variants[j] ) :
								p_variants[j]['color'] = None


						if ( len(p_variants) == 1 ) :

							newjson['categories'][i]['products'].append( {    'title' : p_title,
																			    'url' : p_url,
																		'description' : p_description,
																		     'images' : p_images,
																		   'variants' : []} )

							newjson['categories'][i]['products'][len(newjson['categories'][i]['products']) - 1].update( p_variants[0] )

						elif ( len(p_variants) > 0 ) :

							newjson['categories'][i]['products'].append( {    'title' : p_title,
																			    'url' : p_url,
																		'description' : p_description,
																		     'images' : p_images,
																		   'variants' : p_variants} )
						else :

							newjson['categories'][i]['products'].append( {    'title' : p_title,
																			    'url' : p_url,
																		'description' : p_description,
																			  'price' : p_price,
																		 'list-price' : p_list_price,
																		 	  'width' : p_width,
																		 	 'height' : p_height,
																		 	 'weight' : p_weight,
																		 	 	'len' : p_len,
																		     'images' : p_images,
																		   'variants' : []} )


					else :

						newjson['categories'][i]['products'].append( {    'title' : p_title,
																		    'url' : p_url,
																	'description' : p_description,
																		  'price' : p_price,
																	 'list-price' : p_list_price,
																	 	  'width' : p_width,
																	 	 'height' : p_height,
																	 	 'weight' : p_weight,
																	 	 	'len' : p_len,
																	     'images' : p_images} )




for arg in sys.argv[1:]:

	[cat, url] = arg.split("@")

	ExtractJSON( url, cat )

with open('combined', 'w') as outfile:
	json.dump(newjson, outfile)

outfile.close()
