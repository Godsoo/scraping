from scrapex import *
import time
import sys
import json


def read_accounts():

	accounts = excellib.read_sheet(input_accounts_path, index=0, return_type='dict')	# sheet1 sheet

	# for account in accounts :
	# 	print account['ZipCode'] + ' ' + account['E-Mail'] + ' ' + account['E-Mail & Safeway Inc.Password']

	return accounts


def read_our_products():

	our_products = []

	products = excellib.read_sheet(input_products_path, index=2, return_type='dict')	# basket sheet

	for product in products :

		if ( product['Safeway_search_term'] and (product['Safeway_search_term'].strip() != '') ) :
			our_products.append( product )
			# print str(product['Safeway']) + ' ' + product['Safeway_search_term']

	# print our_products
	return our_products


def search_our_products():

	# account_num = 0

	for account in accounts :

		if login( account['E-Mail'], account['E-Mail & Safeway Inc.Password'] ) :

			# if ( account_num > 2 ) :
			# 	return

			# login( account['E-Mail'], account['E-Mail & Safeway Inc.Password'] )
			# print account['E-Mail'] + ' ' + account['E-Mail & Safeway Inc.Password']

			for product in our_products :

				# print product['Safeway_search_term'] + str(product['Safeway'])
				# print scrape_product( product['Safeway_search_term'], product['Safeway'] )

				price, note = scrape_product( product['Safeway_search_term'], product['Safeway'] )

				res = dict(
							zipcode    = account['ZipCode'],
							price      = price,
							note       = note,
							updated    = updated,
							product_id = product['Safeway'],
					)

				
				if _save_to_csv:
					s.save(res, 'history.csv')

				db.execute("insert into history (product_id, site_name, zipcode, store, price, note, updated) values(%s, %s, %s, %s, %s, %s, %s)", 
				 			(res['product_id'], site_name, res['zipcode'], '', res['price'], res['note'], res['updated'])
					)

				# price = price or None

				# db.execute("""insert into history (product_id, site_name, zipcode, store, price, note, updated)
				#  			values(%s, %s, %s, %s, %s, %s, %s)""", 
				#  			(product['Safeway'], site_name, account['ZipCode'], '', price, note, updated)
				# 	)

			# account_num = account_num + 1
		else :

			logger.warn( 'login failed -> id: %s, password: %s' % (account['E-Mail'], account['E-Mail & Safeway Inc.Password']) )


def parse_data(search_url, pid):

	doc 	    = s.load(search_url)
	no_of_pages = len(doc.q('//div[contains(@class,"id-productListTop")]//div[contains(@class,"id-productListPager")]//ol/li'))

	logger.info( "search_url: %s, SKU: %s" % (search_url, pid) )
	logger.info( "pages: %s"               % no_of_pages )

	page_url = search_url + '&Navigation=&ListType=Search&SortOrder=SearchRanking&Page='

	for i in range(no_of_pages):

		doc1 		 = s.load(page_url + '%s#' % i)
		product_list = doc1.q("//div[contains(@class,'id-productItems')]//div[contains(@class,'widget-content')]")

		logger.info("total products on this page: %s" % len(product_list))

		for product in product_list:

			product_data = json.loads(product.x("script"))
			product_id   = product_data['Id']

			# if pid == str(product_id):
			if pid == product_id:

				note          = 'success'
				product_price = product_data['Price']
				
				logger.info( 'PID: %s, SKU: %s, price: %s' % (pid, product_data['Id'], product_price) )

				return product_price, note
	else:

		if doc.x("//div[@class='widget-header']/h1"):
			note = 'invalid search term'
			return None, note

		note = 'no product associated with search term/pid'

		return None, note


def scrape_product(search_term, pid):

	search_url = 'https://shop.vons.com/ecom/search?source=searchBox&searchTerm=%s' % common.urlencode( search_term )
	data       = parse_data(search_url, pid)	
	return data


def login(username, password):

	signin_url = 'https://shop.safeway.com/ecom/account/sign-in'
	payload    = {
					'form'				 : 'SignIn',
					'SignIn.EmailAddress': username,
					'SignIn.Password'	 : password,
					'SignIn.RememberMe'	 : True,
	}

	doc = s.load(signin_url, post=payload)

	time.sleep(1)

	if doc.status.code == 200:
		login_flag = True
		logger.info('logged in -> id: %s, password: %s' %(username, password))
		logger.info('landing page: %s' % doc.status.final_url)
	else:
		logger.info('code: %s'  % doc.status.code)
		logger.info('Error: %s' % doc.status.error)
		login_flag = False

	return login_flag


# does not seem to work when set use_cache as True
# site is full of javascript
s = Scraper(use_cache=False, retries=3, timeout=30)

logger = s.logger

input_accounts_path = s.join_path('safeway_accounts.xlsx')
input_products_path = s.join_path('input.xlsx')

accounts     = []
our_products = []

updated = time.strftime('%Y-%m-%d %H:%M:%S')

site_name = 'safeway'

from db import DB
db = DB()

_save_to_csv = True

if __name__ == '__main__':

	accounts     = read_accounts()
	our_products = read_our_products()

	search_our_products()



