from scrapex import *

s = Scraper(use_cache=True, retries=3, timeout=30, proxy_file='proxy_dana.txt')

logger = s.logger

site_name = 'copcopineus'
site_url = 'http://www.cop-copineus.com/'

if __name__ == '__main__':
	doc_site = s.load(site_url)
	products = []
	for category in doc_site.q('//ul/li[@id="menu-item-5533"]/ul/li/ul/li/a/@href'):
		category_url = str(category.nodevalue())
		logger.info('category -> ' + category_url)

		doc_category = s.load(category_url)
		while True:			
			for product in doc_category.q('//div[@class="product-thumb"]/a[@class="product-link"]/@href'):
				product_url = str(product.nodevalue())
				logger.info('product -> ' + product_url)

				doc_product = s.load(product_url)

				name = doc_product.x('//div[contains(@class, "summary-product entry-summary")]/h1[@itemprop="name"]/text()')
				price = doc_product.q('//div[contains(@class, "summary-product entry-summary")]/div[@itemprop="offers"]//span[@class="woocommerce-Price-amount amount"]//text()').join('')
				long_desc_list = [frag.nodevalue() for frag in doc_product.q('//div[contains(@class, "summary-product entry-summary")]/div[@itemprop="description"]//text()')]
				long_description = ' '.join(long_desc_list)
				# model_size = doc_product.x('//div[contains(@class, "summary-product entry-summary")]/div[@itemprop="description"]/div[@class="model-size"]/text()')
				# if (model_size is None) or (model_size == ''):
				# 	if len(long_desc_list) > 1:
				# 		if 'model' in long_desc_list[-2]:
				# 			model_size = long_desc_list[-2]
				# 		else:
				# 			model_size = ''
				# 	else:
				# 		model_size = ''
				model_size = common.DataItem(long_description).subreg('(The model is \d+ cm)')
				# color = '|'.join([frag.nodevalue() for frag in doc_product.q('//select[@id="pa_color"]/option[not(@value="")]/text()')])
				color = doc_product.q('//select[@id="pa_color"]/option[not(@value="")]/text()').join('|')
				# size = '|'.join([frag.nodevalue() for frag in doc_product.q('//select[@id="pa_size"]/option[not(@value="")]/text()')])
				size = doc_product.q('//select[@id="pa_size"]/option[not(@value="")]/text()').join('|')
				SKU = doc_product.x('//div[@class="product_meta"]//span[@itemprop="sku"]/text()')
				Availability = doc_product.x('//div[@class="product_meta"]//span[@itemprop="stock"]/text()')
				ShippingWeight = doc_product.x('//div[@class="product_meta"]//label[contains(text(), "Shipping Weight:")]/following-sibling::span/text()')
				# Categories = '|'.join([frag.nodevalue() for frag in doc_product.q('//div[@class="product_meta"]//label[contains(text(), "Categories:")]/../a/text()')])
				Categories = doc_product.q('//div[@class="product_meta"]//label[contains(text(), "Categories:")]/../a/text()').join('|')
				# photo_urls = '|'.join([frag.nodevalue() for frag in doc_product.q('//div[@class="thumbnail-image"]/a[@itemprop="image"]/@href')])
				photo_urls = doc_product.q('//div[@class="thumbnail-image"]/a[@itemprop="image"]/@href').join('|')

				for product in products:
					if product[13] == SKU:
						Categories = product[19] + '|' + Categories
						Categories = '|'.join(list(set(Categories.split('|'))))
						products.remove(product)
						logger.info('Duplicates -> ' + product_url)
						break
				products.append([  'name', name, 
								   'price', price, 
								   'long_description', long_description, 
								   'model_size', model_size, 
								   'color', color, 
								   'size', size, 
								   'SKU', SKU,
								   'Availability', Availability,
								   'ShippingWeight', ShippingWeight,
								   'Categories', Categories,
								   'photo_urls', photo_urls])

				# s.save(['name', name, 
				# 	   'price', price, 
				# 	   'long_description', long_description, 
				# 	   'model_size', model_size, 
				# 	   'color', color, 
				# 	   'size', size, 
				# 	   'SKU', SKU,
				# 	   'Availability', Availability,
				# 	   'ShippingWeight', ShippingWeight,
				# 	   'Categories', Categories,
				# 	   'photo_urls', photo_urls], 'result.csv')
				# break
			try:
				category_url = doc_category.x('//ul[@class="pagination"]/li/a[@class="next page-numbers"]/@href')
				if (category_url is None) or (category_url.strip() == ''):
					break
			except:
				break
			logger.info('page -> ' + category_url)
			doc_category = s.load(category_url)
			# break
		# break
	for product in products:
		s.save(product, 'result.csv')
