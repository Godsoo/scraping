from scrapex import *
import time
import sys
import json
import urlparse
import re


def set_session_zipcode(zipcode):
	"""
	in this function alone, all requests need to be cache-disabled (use_cache = False)

	"""

	s.clear_cookies()
	logger.info('loading register page...')
	url = 'https://www.wbmason.com/RegZipCode.aspx'
	html = s.load( url, use_cache = False )

	logger.info('setting zipcode: %s', zipcode)
	formdata = {
					'__EVENTTARGET'								: 'ctl00$ContentPlaceholder1$submitLinkButton',
					'__EVENTARGUMENT'							: '',
					'__COMPRESSEDVIEWSTATE'						: html.x('//input[@id="__COMPRESSEDVIEWSTATE"]/@value'),
					'__VIEWSTATE'								: html.x('//input[@id="__VIEWSTATE"]/@value'),
					'__EVENTVALIDATION'							: html.x('//input[@id="__EVENTVALIDATION"]/@value'),
					'ctl00$CartDropdown$SaveWorkFlowCart'		: '',
					'ctl00$txtGlobalSearch'						: 'Enter+Keyword',
					'ctl00$txtSubMenuGlobalSearch'				: 'Enter+Keyword',
					'ctl00$SubMenuCartDropdown$SaveWorkFlowCart': '',
					'ctl00$ContentPlaceholder1$txtZip'			: zipcode,
					'ctl00$ContentPlaceholder1$rblRegOptions'	: 'Option3',
					'ctl00$XPos'								: '',
					'ctl00$YPos'								: ''
	}

	html = s.load_html( url, ref=site_url, post=formdata, use_cache = False )

	check_url = 'http://www.wbmason.com/SearchResults.aspx?sc=BM&fi=1&fr=1&ps=0&av=0&Category=C000482&PCatID=C000458'
	html = s.load_html( check_url, ref=site_url, use_cache=False )

	if 'Please enter your delivery zip code:' in html:
		logger.warn('failed with status code: %s', html.status.code)	
		return False
	else:
		logger.info('success')
		return True


# get main and subcategory1 urls
def get_category_urls_at_landing_page():
	global products_ranking
	doc = s.load( site_url )
	q_sub_categories = doc.q('//table[contains(@id, "_dlSubTabItems")]/tr/td/a')
	for sub_category in q_sub_categories:
		get_product_urls( u'{}>{}'.format(sub_category.x('../../../../../../div/a/span[contains(@id, "_lblSubTab")]/text()'), sub_category.x('text()')), sub_category.x('@href'), 'subcat1' )
		get_subcategory2_urls( u'{}>{}'.format(sub_category.x('../../../../../../div/a/span[contains(@id, "_lblSubTab")]/text()'), sub_category.x('text()')), sub_category.x('@href') )

		logger.info( products_ranking )
		for product in products_ranking:
			get_product_info( product['product_url'], product['category'], product['subcat1_rank'], product['subcat2_rank'] )


def get_subcategory2_urls(subcategory1_name, subcategory1_url):
	doc = s.load( subcategory1_url )

	q_sub_categories = doc.q('//h3[contains(text(), "Refine Results")]/following-sibling::p[contains(text(), "Category")]/following-sibling::ul/li/a')
	for sub_category in q_sub_categories:
		get_product_urls( u'{}>{}'.format(subcategory1_name, sub_category.x('text()')), sub_category.x('@href'), 'subcat2' )

	if q_sub_categories:
		q_viewmore_categories = doc.q('//div[@id="divMore1"]/ul/li/a')
		for sub_category in q_viewmore_categories:
			get_product_urls( u'{}>{}'.format(subcategory1_name, sub_category.x('text()')), sub_category.x('@href'), 'subcat2' )

	# q_unitofmeasure = doc.q('//div[@class="search-leftcol"]/p[contains(text(), "Unit of Measure"]/following-sibling::ul/li/a')
	# for unitofmeasure in q_unitofmeasure:
	# 	get_product_urls( u'{}>{}'.format(subcategory1_name, 'Unit of Measure: ' + unitofmeasure.x('text()')), unitofmeasure.x('@href'), 'UnitofMeasure' )

	# q_gogreen = doc.q('//div[@class="search-leftcol"]/p[contains(text(), "Go Green"]/following-sibling::ul/li/a')
	# for gogreen in q_gogreen:
	# 	get_product_urls( u'{}>{}'.format(subcategory1_name, 'Go Green: ' + gogreen.x('text()')), gogreen.x('@href'), 'GoGreen' )


def get_product_urls(category_name, category_url, category_level):
	# global page_size_57_selected
	global products_ranking
	global page_size_57_refresh_count
	
	logger.info('category name: %s', category_name)
	logger.info('category url : %s', category_url)

	doc = s.load( category_url )
	# if page_size_57_selected == False:
	formdata = {
				'__EVENTTARGET'				: 'ctl00$ContentPlaceholder1$ProductList$SearchOptionsHeader$ddlResultsPerPage',
				'__EVENTARGUMENT'			: '',
				'__LASTFOCUS'				: doc.x('//input[@id="__LASTFOCUS"]/@value'),
				'__COMPRESSEDVIEWSTATE'		: doc.x('//input[@id="__COMPRESSEDVIEWSTATE"]/@value'),
				'__VIEWSTATE'				: doc.x('//input[@id="__VIEWSTATE"]/@value'),
				'ctl00$CartDropdown$SaveWorkFlowCart'			: '',
				'ctl00$txtGlobalSearch'							: 'Enter+Keyword',
				'ctl00$txtSubMenuGlobalSearch'					: 'Enter+Keyword',
				'ctl00$SubMenuCartDropdown$SaveWorkFlowCart'	: '',
				'ctl00$ContentPlaceholder1$LeftSideNav$rptAppliedFilters$ctl01$rptAppliedFilterValues$ctl01$hfClearFilterUrl': '',
				'ctl00$ContentPlaceholder1$LeftSideNav$txtRefineSearch'								: 'Refine+Search',
				'ctl00$ContentPlaceholder1$ProductList$CurrentListShown'							: '',
				'ctl00$ContentPlaceholder1$ProductList$SearchOptionsHeader$ddlSortByHeader'			: 'BM',
				'ctl00$ContentPlaceholder1$ProductList$SearchOptionsHeader$ddlResultsPerPage'		: '57',
				'ctl00$ContentPlaceholder1$ProductList$SearchOptionsHeader$ucAddtoListBulk$txtListname': '',
				'ctl00$ContentPlaceholder1$ProductList$SearchOptionsHeader$ucAddtoListBulk$ctl02'	: 'Personal',
				'ctl00$ContentPlaceholder1$ProductList$SearchOptionsFooter$ddlSortByHeader'			: 'BM',
				'ctl00$ContentPlaceholder1$ProductList$SearchOptionsFooter$ddlResultsPerPage'		: '57',
				'ctl00$ContentPlaceholder1$ProductList$SearchOptionsFooter$ucAddtoListBulk$txtListname': '',
				'ctl00$ContentPlaceholder1$ProductList$SearchOptionsFooter$ucAddtoListBulk$ctl02'	: 'Personal',
				'ctl00$XPos': '',
				'ctl00$YPos': '' }
	doc = s.load( category_url, ref=site_url, post=formdata )
	# page_size_57_selected = True
	logger.info('page size selected as 57')

	doc = s.load( category_url )

	ranking = 0

	page_counter = 0
	now_page = ''

	while True:
		product_urls = doc.q('//div[@id="ctl00_ContentPlaceholder1_ProductList_pnlProductsGrid"]/div/div/div/a[contains(@id, "_lnkItemDesc")]')
		logger.info('number of products: %s', len(product_urls))
		for product_url in product_urls:
			ranking = ranking + 1
			# logger.info( product_url.x('@href') )
			# logger.info( 'ranking : %d', ranking )
			product = {'product_url': product_url.x('@href'),
					  'category'	: category_name,
				      'subcat1_rank': str(ranking) if category_level == 'subcat1' else '',
				      'subcat2_rank': str(ranking) if category_level == 'subcat2' else ''}

			product_existing = False
			for i in range(len(products_ranking)):
				if products_ranking[i]['product_url'] == product['product_url']:

					if ( products_ranking[i]['subcat1_rank'] == '' ):
						products_ranking[i]['subcat1_rank'] = product['subcat1_rank']
					if ( products_ranking[i]['subcat2_rank'] == '' ):
						products_ranking[i]['subcat2_rank'] = product['subcat2_rank']

					product_existing = True
					break

			if product_existing == False:
				products_ranking.append( product )
		# break

		next_page = doc.x('//span[@class="visuallyHiddenElement" and contains(text(), "Forward")]/../@href')
		if next_page:
			if page_counter >= page_size_57_refresh_count:
				doc = s.load( now_page, ref=site_url, post=formdata )
				# page_size_57_selected = True
				logger.info('page size selected as 57')
				page_counter = 0
			now_page = urlparse.urljoin(site_url, next_page)
			doc = s.load( now_page )
			page_counter = page_counter + 1
		else :
			break

	return ranking


def get_product_info(product_url, category, subcat1_ranking, subcat2_ranking):
	
	global product_detail_fields

	# file_name = u'detail-{}.html'.format(ItemNumber)
	# if s.cache.exists(file_name=cache_filename):
	# 	# load from cache
	# 	doc = s.load(url=product_url, file_name=cache_filename)
	# else :
	# 	# new load
	# 	doc = s.load(product_url)
	# 	s.cache.write(file_name=cache_filename, data=doc.html())

	# doc = s.load(product_url, use_cache=True, file_name= file_name)	

	item_id = common.DataItem(product_url).subreg('ItemID=([^&]+)')
	if not item_id:
		logger.warn('no item_id: %s', product_url)
		return

	logger.info('detail url: %s', product_url)

	file_name = 'detail-%s.html' % item_id
	
	doc = s.load(product_url, file_name= file_name, contain='Product Details')

	# return #test



	ItemNumber 		 = doc.x('//span[@id="ctl00_ContentPlaceholder1_ucProductDetail_fvProductDetail_lblItemNumber"]/text()')
	Bullets_q 		 = doc.q('//div[@class="product-info"]/ul[@class="item-points"]/li')
	ProductDetails_q = doc.q('//div[@id="tab1_content"]//table/tr/td[@class="name"]')
	ManufacturerBullets_q = doc.q('//div[contains(@id, "wc-overview")]//div[@class="wc-rich-content-description"]/div/ul/li')

	# ProductDetails = []
	# for productdetail in ProductDetails_q:
	# 	ProductDetails.append( [productdetail.x('text()'), productdetail.x('following-sibling::td[@class="value"]/text()')] )

	ProductDetails = []
	for productdetail in ProductDetails_q:
		fieldname = productdetail.x('text()')

		# It would be better that this if statement should be commented after first extracting done.
		# This is just for extracting field names into variable 'product_detail_fields'
		if fieldname not in product_detail_fields:
			product_detail_fields.append( fieldname )

		ProductDetails.append( [fieldname, productdetail.x('following-sibling::td[@class="value"]/text()')] )

	ManufacturerBullets = []
	for manufacturerbullet in ManufacturerBullets_q:
		ManufacturerBullets.append( manufacturerbullet.x('text()') )

	Bullets = []
	for bullet in Bullets_q:
		Bullets.append( '' + bullet.nodevalue().strip() ) 

	MainCat = category.split('>')[0]
	SubCat1 = category.split('>')[1]
	try:
		SubCat2 = category.split('>')[2]
	except:
		SubCat2 = ''

	Images_q = doc.q('//div[@id="alternate-images"]/img[@src]')
	# logger.info( Images )
	img_filenames = []
	Images = []
	for i in range(len(Images_q)):
		img_src = Images_q[i].get('src').tostring()
		Images.append( img_src )
		img_filenames.append(u'{}-{}.{}'.format(ItemNumber, i + 1, re.search(r'.*\.(.*)', img_src, re.M|re.I).group(1)))
		s.save_link(urlparse.urljoin(site_url, img_src), dir='images', file_name=img_filenames[i])

	product_result = [   'Link'		  , product_url,
						 'MainCat'	  , MainCat,
						 'SubCat1'    , SubCat1,
						 'SubCat1_Ranking', subcat1_ranking,
						 'SubCat2'    , SubCat2,
						 'SubCat2_Ranking', subcat2_ranking,
						 'Brand'	  , doc.x('//span[@id="ctl00_ContentPlaceholder1_ucProductDetail_fvProductDetail_ucProductPopup_lblBrand"]/text()'),
						 'ItemNumber' , ItemNumber, 
						 'Title'	  , re.sub(r'[\s\s]+', ' ', doc.x('//div[@class="product-info"]/h3[@class="item-name"]/text()')), 
						 'Price'	  , re.sub(r'[\s\$]', '', doc.x('//div[@class="product-buy"]//span[@class="price"]/text()')), 
						 'ManufacturerOverview', doc.x('//div[contains(@id, "wc-overview")]//div[@class="wc-rich-content-description"]/div/text()'),
						 'Description', doc.x('//div[@id="tab2_content"]//span[@id="ctl00_ContentPlaceholder1_ucProductDetail_lblSellingCopy"]/text()'),
						 'img_filenames', img_filenames ]


	for i in range(max_bullets):
		product_result.append( u'Bullet {}'.format(i+1) )
		try:
			product_result.append( Bullets[i] )
		except:
			product_result.append( '' )

	for i in range(max_manufacturerbullets):
		product_result.append( u'Manufacturer Bullet {}'.format(i+1) )
		try:
			product_result.append( ManufacturerBullets[i] )
		except:
			product_result.append( '' )

	for i in range(max_images):
		product_result.append( u'Images {}'.format(i+1) )
		try:
			product_result.append( Images[i] )
		except:
			product_result.append( '' )

	for field in product_detail_fields:
		product_result.append( field )
		field_value = ''
		for prod in ProductDetails:
			if field in prod:
				if field == prod[0]:
					field_value = prod[1]
				else:
					field_value = prod[0]
				break
		product_result.append( field_value )

	s.save( product_result, 'history.csv' )

	# s.save( ['Link'		  , product_url,
	# 		 'MainCat'	  , MainCat,
	# 		 'SubCat1'    , SubCat1,
	# 		 'SubCat1_Ranking', subcat1_ranking,
	# 		 'SubCat2'    , SubCat2,
	# 		 'SubCat2_Ranking', subcat2_ranking,
	# 		 'Brand'	  , doc.x('//span[@id="ctl00_ContentPlaceholder1_ucProductDetail_fvProductDetail_ucProductPopup_lblBrand"]/text()'),
	# 		 'ItemNumber' , ItemNumber, 
	# 		 'Title'	  , re.sub(r'[\s\s]+', ' ', doc.x('//div[@class="product-info"]/h3[@class="item-name"]/text()')), 
	# 		 'Price'	  , re.sub(r'[\s\$]', '', doc.x('//div[@class="product-buy"]//span[@class="price"]/text()')), 
	# 		 'Bullets'	  , Bullets, 
	# 		 'ManufacturerOverview', doc.x('//div[contains(@id, "wc-overview")]//div[@class="wc-rich-content-description"]/div/text()'),
	# 		 'ManufacturerBullets', ManufacturerBullets,
	# 		 'Assortment' , doc.x('//div[@id="tab1_content"]//table[@class="content-table product-table"]/tr/td[@class="name" and contains(text(), "Assortment:")]/following-sibling::td'), 
	# 		 'Color(s)'	  , doc.x('//div[@id="tab1_content"]//table[@class="content-table product-table"]/tr/td[@class="name" and contains(text(), "Color(s):")]/following-sibling::td'), 
	# 		 'Description', doc.x('//div[@id="tab2_content"]//span[@id="ctl00_ContentPlaceholder1_ucProductDetail_lblSellingCopy"]/text()'),
	# 		 'ProductDetails', ProductDetails,
	# 		 'Images'	  , Images,
	# 		 'img_filenames', img_filenames ], 'history.csv' )
	

def test_get_category_urls_at_landing_page():
	global products_ranking
	doc = s.load( site_url )
	q_sub_categories = doc.q('//table[contains(@id, "_dlSubTabItems")]/tr/td/a')
	for sub_category in q_sub_categories:
		get_product_urls( u'{}>{}'.format(sub_category.x('../../../../../../div/a/span[contains(@id, "_lblSubTab")]/text()'), sub_category.x('text()')), sub_category.x('@href'), 'subcat1' )
		test_get_subcategory2_urls( u'{}>{}'.format(sub_category.x('../../../../../../div/a/span[contains(@id, "_lblSubTab")]/text()'), sub_category.x('text()')), sub_category.x('@href') )

		logger.info( products_ranking )
		for product in products_ranking:
			get_product_info( product['product_url'], product['category'], product['subcat1_rank'], product['subcat2_rank'] )

		return


def test_get_subcategory2_urls(subcategory1_name, subcategory1_url):
	doc = s.load( subcategory1_url )
	q_sub_categories = doc.q('//h3[contains(text(), "Refine Results")]/following-sibling::p[contains(text(), "Category")]/following-sibling::ul/li/a')
	for sub_category in q_sub_categories:
		get_product_urls( u'{}>{}'.format(subcategory1_name, sub_category.x('text()')), sub_category.x('@href'), 'subcat2' )

		return

# does not seem to work when set use_cache as True
# site is full of javascript
s = Scraper(
	use_cache=True, #enable cache globally
	retries=1, 
	timeout=60,
	# proxy_file = '/users/cung/scrape/proxy.txt'
	)

logger = s.logger

site_name = 'wbmason'
site_url = 'http://www.wbmason.com/'
# page_size_57_selected = True
products_ranking = []

max_bullets = 5
max_manufacturerbullets = 5
max_images = 5
product_detail_fields = []
page_size_57_refresh_count = 100

if __name__ == '__main__':

	if set_session_zipcode( '10001' ):
		# get_product_info( 'http://www.wbmason.com/ProductDetail.aspx?ItemID=AVE17012&uom=EA&COID=', 'a>b', '1', '1')
		get_category_urls_at_landing_page()

		# When first extracting done, all field names will be saved into 'product_detail_field_names.csv'
		# After that, this line should be commented.
		# All field names from 'product_detail_field_names.csv' should be copied into variable 'product_detail_fields' in the style of ['field_1', 'field_2', ..., 'field_n']
		s.save( product_detail_fields, 'product_detail_field_names.csv')
		# test_get_category_urls_at_landing_page() # extract first subcategory of first main category



