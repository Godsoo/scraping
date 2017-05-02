# -*- coding: utf-8 -*-
"""
Helper functions to allow setting big site method dynamically.

WARNING!!! These function heavily use Python introspection and class manipulation.
Consider changing with caution.
"""
import logging

from scrapy.spider import BaseSpider
from scrapy import Spider
from scrapy import log

from product_spiders.custom_crawl_methods.utils import check_cls_has_attr, change_cls_method, \
    change_cls_base

logger = logging.getLogger(__name__)

_weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']


PARAMS = {
    'full_crawl_cron': {
        'title': 'When to do full run',
        'type': 'cron_day',
        'postprocess': lambda x: ' '.join(x.split()[2:])
    },
    'do_full_run_only_once': {
        'title': 'Do Full Run only once if multicrawling is enabled',
        'type': 'bool',
        'postprocess': None,
    }
    # 'full_crawl_day': {
    #     'title': "Do full run on",
    #     'type': "enum",
    #     'values': OrderedDict([(str(x), _weekdays[x]) for x in xrange(0, len(_weekdays))])
    # }
}


def log_msg(msg, level=log.DEBUG):
    msg = "[CustomCrawlMethod BigSiteMethod]:" + msg
    logger.log(level=level, msg=msg)


def make_bigsitemethod_spider(spcls, spmdl):
    if _bsm_check_cls_fits(spcls):
        log_msg("[%s] OK. Spider fits" % spcls.name)
        return _bsm_create_cls(spcls, spmdl)
    else:
        log_msg("[%s] ERROR. Spider does not fit" % spcls.name)


def check_fits_to_bigsitemethod(spcls):
    return _bsm_check_cls_fitting_errors(spcls)


def _check_cls_method_error(cls, methods_config):
    if 'replacements' in methods_config:
        for replacement, is_method in methods_config['replacements']:
            if check_cls_has_attr(cls, replacement, method=is_method, overriden=True):
                return None
    if not any([check_cls_has_attr(cls, method_name, method=True, overriden=True)
                for method_name in methods_config['methods']]):
        # log_msg("[%s] ERROR. Class method `%s` not found" % (cls.__name__, str(methods_config['methods'])))
        return "Class method `%s` not found" % str(methods_config['methods'])

    if 'requirements' in methods_config:
        for requirement, is_method in methods_config['requirements']:
            if not check_cls_has_attr(cls, requirement, method=is_method, overriden=True):
                # log_msg("[%s] ERROR. Requirement for class method `%s` not found: %s" % (cls.__name__, str(methods_config['methods']), requirement))
                return "Requirement for class method `%s` not found: %s" % (str(methods_config['methods']), requirement)
    return None


def _bsm_check_cls_overrides(cls):
     # should not override specific methods
    methods_should_not_be_changes = [
        '_metadata_enabled', '_get_prev_crawl_file', '_get_prev_crawl_meta_file', 'spider_idle', 'spider_closed',
        'full_run_required', '_get_matches_new_system_request', '_get_matches_old_system_request',
        'parse_matches_new_system', 'parse_matches_old_system', 'bsm_retry_download',
        # '_start_requests_full', '_start_requests_simple'
    ]
    overrides = []
    for method_name in methods_should_not_be_changes:
        if check_cls_has_attr(cls, method_name, method=True, overriden=True):
            # log_msg("[%s] ERROR. Method override found: %s" % (cls.__name__, method_name))
            overrides.append("Method override found: %s" % method_name)

    return overrides


def _bsm_check_cls_does_not_override_methods(cls):
    override_errors = _bsm_check_cls_overrides(cls)
    if override_errors:
        return False
    else:
        return True


def _bsm_check_cls_attributes(cls):
    errors = []
    # should have mandatory attributes (not methods)
    mandatory_attrs = ['name', 'allowed_domains', 'start_urls']
    for attr_name in mandatory_attrs:
        if not check_cls_has_attr(cls, attr_name, method=False, overriden=True):
            # log_msg("[%s] ERROR. Class attribute not found: %s" % (cls.__name__, attr_name))
            errors.append("Class attribute not found: %s" % attr_name)
    return errors


def _bsm_check_cls_has_mandatory_attributes(cls):
    attr_errors = _bsm_check_cls_attributes(cls)
    if attr_errors:
        return False
    else:
        return True


def _bsm_check_cls_methods(cls):
    # should have mandatory methods
    mandatory_methods = [
        {'methods': ['parse', 'parse_full'], 'replacements': [('start_requests', True), ], 'requirements': [('start_urls', False)]},
        {'methods': ['parse_product']}
    ]
    missing_methods = []
    for methods_config in mandatory_methods:
        error = _check_cls_method_error(cls, methods_config)
        if error:
            missing_methods.append(error)
    return missing_methods


def _bsm_check_cls_has_mandatory_methods(cls):
    missing_methods = _bsm_check_cls_methods(cls)
    if missing_methods:
        return False
    else:
        return True


def _bsm_check_cls_fitting_errors(spcls):
    """
    Checks if given spider class can be used with big site method and outputs list of errors if not
    """
    import product_spiders.base_spiders.amazonspider
    import product_spiders.base_spiders.legoamazon
    import product_spiders.base_spiders.amazonspider2.amazonspider
    import product_spiders.base_spiders.amazonspider2.legoamazonspider
    import product_spiders.spiders.lego_usa.lego_amazon_base_spider

    errors = []

    # more than one parent class
    if len(spcls.__bases__) > 1:
        errors.append("Class has more than one base: %s" % str(spcls.__bases__))

    classes = []
    for cls in spcls.mro():
        classes.append(cls)
        if cls == BaseSpider:  # we don't need bases beyond BaseSpider
            break
    bases = classes[1:]
    classes = classes[:-1]  # exclude BaseSpider

    # allow amazon base spider and lego amazon base spider, should work for both old and new base spider

    allowed_base_spiders = {
        BaseSpider,
        Spider,  # Scrapy 1.0 new base spider
        product_spiders.base_spiders.amazonspider.BaseAmazonSpider,
        product_spiders.base_spiders.legoamazon.BaseLegoAmazonSpider,
        product_spiders.base_spiders.amazonspider2.amazonspider.BaseAmazonSpider,
        product_spiders.base_spiders.amazonspider2.legoamazonspider.BaseLegoAmazonSpider,
        product_spiders.spiders.lego_usa.lego_amazon_base_spider.BaseLegoAmazonUSASpider
    }
    # parent class is not BaseSpider
    if not any([x in allowed_base_spiders for x in bases]) and not spcls.__base__ == BaseSpider:
        errors.append("Class has wrong bases: %s" % str(bases))

    method_errors = None
    for cls in classes:
        override_errors = _bsm_check_cls_overrides(cls)
        for error in override_errors:
            errors.append("Class %s error. %s" % (cls.__name__, error))

        # base_does_not_override = base_does_not_override and _bsm_check_cls_does_not_override_methods(cls)
        # base_has_mandatory_attrs = base_has_mandatory_attrs or _bsm_check_cls_has_mandatory_attributes(cls)
        _method_errors = set(_bsm_check_cls_methods(cls))
        if method_errors is None:  # only happens if cls is spider class
            method_errors = _method_errors
        else:  # for spider's parents - get only the same errors as in spider class
            method_errors = method_errors.intersection(_method_errors)

    for error in method_errors:
        errors.append(error)

    return errors


def _bsm_check_cls_fits(spcls):
    """
    Checks if given spider class can be used with big site method
    """
    errors = _bsm_check_cls_fitting_errors(spcls)
    if errors:
        for error in errors:
            log_msg("[%s] ERROR. %s" % (spcls.__name__, error))
        return False
    else:
        return True


def _bsm_create_cls(spcls, spmdl):
    # import here to avoid cyclic imports
    from product_spiders.base_spiders.bigsitemethodspider import BigSiteMethodSpider, get_class_module_root_path

    new_spcls = type(spcls.__name__ + "BigSiteMethod", (spcls, ), {})

    if hasattr(new_spcls, 'start_requests') and not new_spcls.start_requests == BaseSpider.start_requests:
        change_cls_method(new_spcls, 'start_requests', '_start_requests_full', BigSiteMethodSpider.start_requests)
    # override class parents
    change_cls_base(new_spcls, BigSiteMethodSpider)
    # fix root path, as it's only calculated properly on class creation when inherited traditionally
    new_spcls.root_path = get_class_module_root_path(spcls)
    # set website_id
    new_spcls.website_id = spmdl.website_id

    new_spcls.params = spmdl.crawl_method2.params

    return new_spcls
