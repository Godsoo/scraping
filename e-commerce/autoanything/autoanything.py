from scrapex import *
import sys
import csv
import re
import json
import time

s = Scraper(use_cache=False, 
              retries=3, 
              timeout=30, 
           # proxy_file='proxy.txt'
              )
logger = s.logger

sr = 0

def save_product(product_info, filename):
    global sr
    sr = sr + 1
    row = [ "category_ids", "", 
            "sr", str(sr), 
            "type", "",
            "Brand", "",
            "name", product_info['name'],
            "attribute_set", "",
            "configurable_attributes", "",
            "sku", product_info['partnumber'],
            "original_sku", "",
            "vesbrand", "",
            "manufacturer", "",
            "price", product_info['regularprice'],
            "special_price", product_info['saleprice'],
            "jobber_price", "",
            "cost", "",
            "cta_year", product_info['year'],
            "cta_make", product_info['make'],
            "cta_model", product_info['model'],
            "cta_option1", product_info['option1'],
            "cta_option2", product_info['option2'],
            "cta_option3", product_info['option3'],
            "options_container", "",
            "description", "",
            "short_description", product_info['short_description'],
            "thumbnail", "",
            "small_image", "",
            "image", "",
            "qty", "",
            "is_in_stock", "",
            "use_config_manage_stock", "",
            "tax_class_id", "",
            "has_options", "",
            "required_options", "",
            "visibility", "",
            "weight", "",
            "simples_skus", "",
            "color", product_info['color'],
            "error", ""]
    s.save(row, filename)
    logger.info(product_info)

if __name__ == '__main__':
    # product_url = 'http://www.autoanything.com/air-intakes/61A2724A0A0.aspx'
    product_url = 'http://www.autoanything.com/nerf-bars/westin-3in-eseries-round-nerf-bars'
    # product_url = 'http://www.autoanything.com/deflectors/61A4927A0A0.aspx'

    product = s.load(product_url)
    filename = re.search('\/([\w\-]+)(\.aspx)?$', product_url).group(1) + '_' + time.strftime("%b%d%Y%H%M%S", time.gmtime()) + '.csv'

    title = product.x('//meta[@property="og:title"]/@content')
    price = product.x('//meta[@property="og:price"]/@content')

    param_script = re.search('window\.VEHICLE_SELECTOR_REFERENCE_TYPE = (.*)\;.*window\.VEHICLE_FORM_REFERENCE_ID = (.*)\;.*window\.IS_ONE_SELECT_VEHICLE_FORM', product.x('//script[contains(text(), "window.VEHICLE_SELECTOR_REFERENCE_TYPE")]/text()'), re.S|re.I|re.M)
    referenceType = param_script.group(1)
    referenceId = param_script.group(2)

    headers = {  'Host': 'www.autoanything.com',
                 'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:50.0) Gecko/20100101 Firefox/50.0',
                 'Accept': 'application/json, text/javascript, */*; q=0.01',
                 'Accept-Language': 'en-US,en;q=0.5',
                 'Accept-Encoding': 'gzip, deflate',
                 'Content-Type': 'application/json; charset=utf-8',
                 'X-Requested-With': 'XMLHttpRequest',
                 'Referer': product.url }

    make_url     = 'http://www.autoanything.com/services/VehicleService.svc/GetVehicleMakeList'
    model_url    = 'http://www.autoanything.com/services/VehicleService.svc/GetVehicleModelList'
    submodel_url = 'http://www.autoanything.com/services/ProductService.svc/GetSubmodelProductOptionList'
    groups_url   = 'http://www.autoanything.com/services/ProductService.svc/GetProductGroups'
    option_url   = 'http://www.autoanything.com/services/ProductService.svc/GetProductAttributeOptionList'
    variant_url  = 'http://www.autoanything.com/services/ProductService.svc/GetVariantPrice'
    ymmproduct_url = 'http://www.autoanything.com/services/ProductService.svc/GetYMMProductPrice'

    product_info = {  'name': title, 
                      'price': price, 
                      'regularprice': '', 
                      'saleprice': '', 
                      'year':'', 
                      'make': '', 
                      'model': '', 
                      'option1': '',
                      'option2': '',
                      'option3': '',
                      'partnumber': '',
                      'color': '',
                      'short_description': ''}

    for vehicleYear in product.q('//select[@id="vehicleYear"]')[0].q('option'):
        vehicleYearId = vehicleYear.x('@value')
        if ( vehicleYearId == '0' ):
        # if ( vehicleYearId != '2004' ):
            continue
        product_info['year'] = vehicleYearId
        make_payload = { "referenceId"  : referenceId,
                         "referenceType": referenceType,
                         "vehicleYearId": vehicleYearId }
        make_list = json.loads(s.load_html(url=make_url, post=json.dumps(make_payload), headers=headers))

        if ( len(make_list['d']['Payload']) == 0 ):
            save_product(product_info, filename)

        for VehicleMake in make_list['d']['Payload']:
            vehicleMakeId = VehicleMake['VehicleMakeId']
            product_info['make'] = VehicleMake['VehicleMakeName']
            model_payload = { "referenceId"  : referenceId,
                              "referenceType": referenceType,
                              "vehicleMakeId": vehicleMakeId,
                              "vehicleYearId": vehicleYearId }
            model_list = json.loads(s.load_html(url=model_url, post=json.dumps(model_payload), headers=headers))

            if ( len(model_list['d']['Payload']) == 0 ):
                save_product(product_info, filename)

            for VehicleModel in model_list['d']['Payload']:
                vehicleModelId = VehicleModel['VehicleModelId']
                product_info['model'] = VehicleModel['VehicleModelName']

                groups_payload = { "parentProductId": referenceId,
                                   "vehicleYearId": vehicleYearId,
                                   "vehicleMakeId": vehicleMakeId,
                                   "vehicleModelId": vehicleModelId,
                                   "chassisModelIdsList": [] }
                groups_list = json.loads(s.load_html(url=groups_url, post=json.dumps(groups_payload), headers=headers))

                if ( len(groups_list['d']['Payload']) == 0 ):
                    save_product(product_info, filename)

                for group in groups_list['d']['Payload']:
                    for product in group['ProductList']:
                        productId = product['ProductId']
                        for attrgroup in product['ProductAttributeGroupList']:
                            productAttributeGroupId = attrgroup['ProductAttributeGroupId']
                            productGroupName = attrgroup['ProductAttributeGroupDescription']
                            product_info['name'] = productGroupName
                            for attribute in attrgroup['ProductAttributeList']:
                                for option1 in attribute['ProductAttributeOptionList']:
                                    vehicleId = option1['Id']
                                    product_info['option1'] = option1['Name']
                                    product_info['partnumber'] = option1['PartNumber']
                                    product_info['regularprice'] = option1['RegularPrice']['CurrencyFormat']
                                    product_info['saleprice'] = option1['SalePrice']['CurrencyFormat']
                                    product_info['short_description'] = ', '.join([re.sub('\<[^\<]*\>', '', variant['ContentText']) for variant in option1['RelatedVariantContent']])

                                    option_payload = {  "productId": productId,
                                                        "vehicleYearId": vehicleYearId,
                                                        "vehicleMakeId": vehicleMakeId,
                                                        "vehicleModelId": vehicleModelId,
                                                        "vehicleId": vehicleId,
                                                        "firstAttributeId": vehicleId,
                                                        "secondAttributeId": '0',
                                                        "thirdAttributeId": '0',
                                                        "fourthAttributeId": '0',
                                                        "productAttributeGroupId": productAttributeGroupId,
                                                        "chassisModelIdsList":[] }
                                    option_list = json.loads(s.load_html(url=option_url, post=json.dumps(option_payload), headers=headers))

                                    for option2 in option_list['d']['Payload']['ProductAttributeOptionList']:
                                        product_info['option2'] = option2['Name']
                                        try:
                                            product_info['option3'] = re.search('\_([a-zA-Z]+)\.gif', option2['MediaFilenameColorSwatch'], re.M|re.S|re.I).group(1)
                                        except:
                                            pass
                                        product_info['partnumber'] = option2['PartNumber']
                                        product_info['regularprice'] = option2['RegularPrice']['CurrencyFormat']
                                        product_info['saleprice'] = option2['SalePrice']['CurrencyFormat']
                                        product_info['short_description'] = ', '.join([re.sub('\<[^\<]*\>', '', variant['ContentText']) for variant in option2['RelatedVariantContent']])

                                        save_product(product_info, filename)

                                        product_info['option2'] = ''
                                        product_info['option3'] = ''
                                        product_info['partnumber'] = ''
                                        product_info['regularprice'] = ''
                                        product_info['saleprice'] = ''
                                        product_info['short_description'] = ''

                                    product_info['option1'] = ''
                                    product_info['partnumber'] = ''
                                    product_info['regularprice'] = ''
                                    product_info['saleprice'] = ''
                                    product_info['short_description'] = ''
                            product_info['name'] = title
                product_info['model'] = ''
            product_info['make'] = ''
        # break

# if __name__ == '__main__':
#     # product = s.load('http://www.autoanything.com/tonneau-covers/60A4819A0A0.aspx')
#     # product = s.load('http://www.autoanything.com/deflectors/61A1051A0A0.aspx')
#     # product_url = 'http://m.autoanything.com/hitch-bed-accessories/60A3644A0A0.aspx'
#     # product_url = 'http://www.autoanything.com/air-intakes/61A2724A0A0.aspx'
#     product_url = 'http://www.autoanything.com/air-intakes/61A2724A0A0.aspx'

#     product = s.load(product_url)
#     filename = re.search('\/(\w+)\.aspx', product_url).group(1) + '.csv'

#     title = product.x('//meta[@property="og:title"]/@content')
#     price = product.x('//meta[@property="og:price"]/@content')

#     param_script = re.search('window\.VEHICLE_SELECTOR_REFERENCE_TYPE = (.*)\;.*window\.VEHICLE_FORM_REFERENCE_ID = (.*)\;.*window\.IS_ONE_SELECT_VEHICLE_FORM', product.x('//script[contains(text(), "window.VEHICLE_SELECTOR_REFERENCE_TYPE")]/text()'), re.S|re.I|re.M)
#     referenceType = param_script.group(1)
#     referenceId = param_script.group(2)

#     headers = {  'Host': 'www.autoanything.com',
#                  'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:50.0) Gecko/20100101 Firefox/50.0',
#                  'Accept': 'application/json, text/javascript, */*; q=0.01',
#                  'Accept-Language': 'en-US,en;q=0.5',
#                  'Accept-Encoding': 'gzip, deflate',
#                  'Content-Type': 'application/json; charset=utf-8',
#                  'X-Requested-With': 'XMLHttpRequest',
#                  'Referer': product.url }

#     make_url     = 'http://www.autoanything.com/services/VehicleService.svc/GetVehicleMakeList'
#     model_url    = 'http://www.autoanything.com/services/VehicleService.svc/GetVehicleModelList'
#     submodel_url = 'http://www.autoanything.com/services/ProductService.svc/GetSubmodelProductOptionList'
#     # variant_url  = 'http://www.autoanything.com/services/ProductService.svc/GetVariantPrice'
#     variant_url  = 'http://www.autoanything.com/services/ProductService.svc/GetYMMProductPrice'

#     product_info = {  'name': title, 
#                       'price': price, 
#                       'regularprice': '', 
#                       'saleprice': '', 
#                       'year':'', 
#                       'make': '', 
#                       'model': '', 
#                       'option1': '',
#                       'option2': '',
#                       'option3': '',
#                       'partnumber': '',
#                       'color': ''}

#     for vehicleYear in product.q('//select[@id="vehicleYear"]')[0].q('option'):
#         vehicleYearId = vehicleYear.x('@value')
#         if ( vehicleYearId == '0' ):
#             continue
#         # logger.info(vehicleYearId)
#         product_info['year'] = vehicleYearId
#         make_payload = { "referenceId"  : referenceId,
#                          "referenceType": referenceType,
#                          "vehicleYearId": vehicleYearId }
#         make_list = json.loads(s.load_html(url=make_url, post=json.dumps(make_payload), headers=headers))
#         # logger.info(make_list)

#         if ( len(make_list['d']['Payload']) == 0 ):
#             save_product(product_info, filename)
#             logger.info(product_info)

#         for VehicleMake in make_list['d']['Payload']:
#             vehicleMakeId = VehicleMake['VehicleMakeId']
#             product_info['make'] = VehicleMake['VehicleMakeName']
#             # logger.info(vehicleMakeId)
#             model_payload = { "referenceId"  : referenceId,
#                               "referenceType": referenceType,
#                               "vehicleMakeId": vehicleMakeId,
#                               "vehicleYearId": vehicleYearId }
#             model_list = json.loads(s.load_html(url=model_url, post=json.dumps(model_payload), headers=headers))
#             # logger.info(model_list)

#             if ( len(model_list['d']['Payload']) == 0 ):
#                 save_product(product_info, filename)
#                 logger.info(product_info)

#             for VehicleModel in model_list['d']['Payload']:
#                 vehicleModelId = VehicleModel['VehicleModelId']
#                 product_info['model'] = VehicleModel['VehicleModelName']
#                 # logger.info(vehicleModelId)

#                 submodel_payload = { "productId": referenceId, 
#                                      "vehicle": { "VehicleId":'0',
#                                                   "VehicleYearId" : vehicleYearId,
#                                                   "VehicleMakeId" : vehicleMakeId,
#                                                   "VehicleModelId": vehicleModelId} }
#                 submodel_list = json.loads(s.load_html(url=submodel_url, post=json.dumps(submodel_payload), headers=headers))
#                 # logger.info(submodel_list)

#                 if ( len(submodel_list['d']['Payload']) == 0 ):
#                     save_product(product_info, filename)
#                     logger.info(product_info)

#                 for Variant in submodel_list['d']['Payload']:
#                     variant_payload = {"variantId": Variant['VariantId']}
#                     product_info['option1'] = Variant['Description']
#                     product_info['partnumber'] = Variant['Diststock']

#                     variant_info = json.loads(s.load_html(url=variant_url, post=json.dumps(variant_payload), headers=headers))
#                     try:
#                         product_info['regularprice'] = variant_info['d']['Payload']['FormattedRegularPrice']
#                     except:
#                         pass
#                     try:
#                         product_info['saleprice']    = variant_info['d']['Payload']['FormattedSalePrice']
#                     except:
#                         pass

#                     save_product(product_info, filename)
#                     logger.info(product_info)
#                     # logger.info(regular_price + ' -> ' + sale_price)

#                     product_info['partnumber']   = ''
#                     product_info['option1']     = ''
#                     product_info['regularprice'] = ''
#                     product_info['saleprice']    = ''
#                 product_info['model'] = ''
#             product_info['make'] = ''
#         # break


    # logger.info(title)
    # logger.info(price)
    # logger.info(referenceType)
    # logger.info(referenceId)
    # {"referenceId":4819,"referenceType":1,"vehicleYearId":"2014"}
    # referenceId =  param_script

    