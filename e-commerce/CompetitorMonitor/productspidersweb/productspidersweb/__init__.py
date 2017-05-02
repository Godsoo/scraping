from pyramid.config import Configurator
from sqlalchemy import engine_from_config
from pyramid.session import UnencryptedCookieSessionFactoryConfig

import security
import productspidersweb.views
import productspidersweb.server_stats_views
import productspidersweb.spider_doc_views
from productspidersweb.models import initialize_sql

def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    try:
        engine = engine_from_config(settings, 'sqlalchemy.', connect_args={'application_name': 'webapp'})
        initialize_sql(engine)
    except TypeError:
        engine = engine_from_config(settings, 'sqlalchemy.')
        initialize_sql(engine)
    settings['mako.directories'] = 'productspidersweb:templates'
    session_factory = UnencryptedCookieSessionFactoryConfig('session')
    config = Configurator(settings=settings, session_factory=session_factory)
    config.scan()

    config.include('pyramid_mako')

    config.add_static_view('/productspiders/static', 'productspidersweb:static', cache_max_age=3600)

    config.add_route('home', '/productspiders')

    config.add_route('dashboard', '/productspiders/accounts')
    config.add_route('admin', '/productspiders/admin')
    config.add_route('admin_proxy', '/productspiders/admin_proxy')
    config.add_route('admin_default', '/productspiders/admin_default')
    config.add_route('admin_users', '/productspiders/admin_users')
    config.add_route('admin_devs', '/productspiders/admin_devs')
    config.add_route('admin_maintenance', '/productspiders/admin_maintenance')
    config.add_route('assembla_authorized', '/productspiders/assembla_authorized')

    config.add_route('admin_proxy_srv', '/productspiders/admin_proxy_srv/')
    config.add_route('admin_default_srv', '/productspiders/admin_default_srv/')
    config.add_route('admin_user_srv', '/productspiders/admin_users_srv/{user_id}/')
    config.add_route('admin_users_srv', '/productspiders/admin_users_srv/')
    config.add_route('admin_dev_srv', '/productspiders/admin_devs_srv/{dev_id}/')
    config.add_route('admin_devs_srv', '/productspiders/admin_devs_srv/')
    config.add_route('assembla_users', '/productspiders/assembla_users/')
    config.add_route('admin_maintenance_srv', '/productspiders/admin_maintenance_srv/')

    config.add_route('list_accounts', '/productspiders/crawlers')
    config.add_route('list_account_spiders', '/productspiders/accounts/{account}/spiders')
    config.add_route('list_account_spiders_old', '/productspiders/accounts/{account}/spiders_old')
    config.add_route('list_account_spiders_json', '/productspiders/accounts/{account}/spiders.json')
    config.add_route('config_account', '/productspiders/accounts/{account}/config')

    config.add_route('list_all_spiders', '/productspiders/spiders')
    config.add_route('list_all_spiders_old', '/productspiders/spiders_old')
    config.add_route('list_all_spiders_json', '/productspiders/spiders.json')
    config.add_route('last_updated_websites_json', '/productspiders/last_updated.json')
    config.add_route('config_spider', '/productspiders/spiders/{account}/{spider}/config')
    config.add_route('list_crawls', '/productspiders/spiders/{spider_id:\d+}/crawls')
    config.add_route('upload_spider_source', '/productspiders/spiders/{spider_id:\d+}/upload-source')
    config.add_route('additional_changes', '/productspiders/additional_changes/{crawl_id:\d+}')
    config.add_route('additional_changes_paged', '/productspiders/additional_changes_paged/{crawl_id:\d+}')

    config.add_route('list_products', '/productspiders/products/{crawl_id:\d+}')
    config.add_route('download_products', '/productspiders/download_products/{crawl_id:\d+}')
    config.add_route('list_changes', '/productspiders/changes/{crawl_id:\d+}')
    config.add_route('list_additions', '/productspiders/additions/{crawl_id:\d+}')
    config.add_route('list_deletions', '/productspiders/deletions/{crawl_id:\d+}')
    config.add_route('list_updates', '/productspiders/updates/{crawl_id:\d+}')
    config.add_route('list_products_paged', '/productspiders/products_paged/{crawl_id:\d+}')
    config.add_route('list_changes_paged', '/productspiders/changes_paged/{crawl_id:\d+}')
    config.add_route('list_additions_paged', '/productspiders/additions_paged/{crawl_id:\d+}')
    config.add_route('list_deletions_paged', '/productspiders/deletions_paged/{crawl_id:\d+}')
    config.add_route('list_updates_paged', '/productspiders/updates_paged/{crawl_id:\d+}')
    config.add_route('set_crawl_valid', '/productspiders/set_valid')
    config.add_route('delete_crawl', '/productspiders/delete_crawl')
    config.add_route('delete_crawls', '/productspiders/delete_crawls')
    config.add_route('upload_changes', '/productspiders/upload')
    config.add_route('upload_crawl_changes', '/productspiders/upload_crawl')
    config.add_route('delete_changes', '/productspiders/delete_changes')
    config.add_route('compute_changes', '/productspiders/compute_changes')
    config.add_route('manage', '/productspiders/manage')
    config.add_route('run_crawl', '/productspiders/runcrawl')
    config.add_route('run_upload', '/productspiders/runupload')
    config.add_route('set_ids', '/productspiders/setids')
    config.add_route('get_error_message', '/productspiders/error_message/{crawl_id:\d+}')
    config.add_route('show_errors', '/productspiders/errors/{crawl_id:\d+}')
    config.add_route('metadata', '/productspiders/meta/{crawl_id:\d+}')
    config.add_route('metadata_changes', '/productspiders/meta/changes/{crawl_id:\d+}')
    config.add_route('set_updates_silent', '/productspiders/set_updates_silent')
    config.add_route('hide_disabled_site', '/productspiders/hide_disabled_site')
    config.add_route('show_disabled_site', '/productspiders/show_disabled_site')
    config.add_route('assign_issue', '/productspiders/assign_issue/{spider_id:\d+}')
    config.add_route('spider_notes', '/productspiders/spider_notes/{spider_id:\d+}')
    config.add_route('spider_user_logs', '/productspiders/spider_user_logs/{spider_id:\d+}')
    config.add_route('user_logs', '/productspiders/user_logs/{user_id:\d+}')
    config.add_route('add_note', '/productspiders/add_note/{spider_id:\d+}')
    config.add_route('list_all_disabled_sites', '/productspiders/list_all_disabled_sites')
    config.add_route('list_daily_errors', '/productspiders/list_daily_errors/{from:\d+/\d+/\d+}/{to:\d+/\d+/\d+}')
    config.add_route('list_total_real_errors', '/productspiders/list_total_real_errors/{from:\d+/\d+/\d+}/{to:\d+/\d+/\d+}')
    config.add_route('show_doc', '/productspiders/accounts/{account}/spiders/{spider}/doc')
    config.add_route('edit_rating', '/productspiders/accounts/{account}/spiders/{spider}/edit_rating')

    config.add_route('disable_account', '/productspiders/disable_account')
    config.add_route('enable_account', '/productspiders/enable_account')

    config.add_route('change_spider_error_status', '/productspiders/change-spider-error-status')
    config.add_route('save_spider_error_assignment', '/productspiders/save-spider-error-assignment')

    config.add_route('assembla_callback', '/productspiders/assembla-callback')

    config.add_route('assembla_authorization', '/productspiders/assembla/authorize')
    config.add_route('assembla_ticket_submit', '/productspiders/assembla/ticket-submit')
    config.add_route('assembla_ticket_get', '/productspiders/assembla/ticket-get')
    config.add_route('assembla_load_spec_from_ticket', '/productspiders/assembla/assembla-load-spec-from-ticket')

    config.add_route('login', '/productspiders/login')
    config.add_route('logout', '/productspiders/logout')

    config.add_route('get_websites_real_errors', '/productspiders/get_websites_real_errors.json')
    config.add_route('get_priority_spiders', '/productspiders/get_priority_spiders.json')
    config.add_route('get_website_last_crawl_date', '/productspiders/get_website_last_crawl_date.json')
    config.add_route('get_website_metadata_status', '/productspiders/get_website_metadata_status.json')
    config.add_route('get_website_crawl_status', '/productspiders/get_website_crawl_status.json')
    config.add_route('get_website_crawl_data', '/productspiders/get_website_crawl_data.json')
    config.add_route('get_website_crawl_results', '/productspiders/get_website_crawl_results.csv')
    config.add_route('get_website_crawl_metadata_results', '/productspiders/get_website_crawl_metadata_results.json')
    config.add_route('get_website_crawl_metadata_results_jsonl', '/productspiders/get_website_crawl_metadata_results.jsonl')
    config.add_route('get_account_last_updated', '/productspiders/get_account_last_updated.json')

    config.add_route('check_account_status', '/productspiders/get_account_status.json')
    config.add_route('check_website_status', '/productspiders/get_website_status.json')

    # API for FMS and Visual tool
    config.add_route('create_local_spider', '/productspiders/create_local_spider.json')
    config.add_route('delete_local_spider', '/productspiders/delete_local_spider.json')
    config.add_route('setup_spider', '/productspiders/setup_spider.json')
    config.add_route('setup_spider2', '/productspiders/setup_spider2.json')
    config.add_route('update_setuped_spider2', '/productspiders/update_setuped_spider2.json')
    config.add_route('update_spider_status', '/productspiders/update_spider_status.json')
    config.add_route('update_account_status', '/productspiders/update_account_status.json')

    # API for matching system
    config.add_route('matching.get_accounts_json', '/productspiders/matching/accounts.json')
    config.add_route('matching.get_spiders_json', '/productspiders/matching/spiders.json')
    config.add_route('matching.get_spider_crawls_json', '/productspiders/matching/accounts/{member_id:\d+}/spiders/{website_id:\d+}/crawls.json')
    config.add_route('matching.get_last_crawls_json', '/productspiders/matching/last_crawls.json')
    config.add_route('matching.get_crawl_results_csv', '/productspiders/matching/crawls/{crawl_id:\d+}.csv')
    config.add_route('matching.get_crawl_changes_csv', '/productspiders/matching/crawl_changes/{crawl_id:\d+}.csv')

    # api for Tor instances
    config.add_route('renew_tor_ip', '/productspiders/renew_tor_ip.json')

    config.add_route('crawls_stats', '/productspiders/crawls-stats')
    config.add_route('spiders_stats', '/productspiders/spiders-stats')
    config.add_route('list_proxy_lists', '/productspiders/proxies')
    config.add_route('config_proxy_list', '/productspiders/proxy_list')
    config.add_route('delete_proxy_list', '/productspiders/delete_proxy_list')

    config.add_route('list_deleted_products', '/productspiders/list_deleted_products')
    config.add_route('deletion_review_bad_delete', '/productspiders/deletion_review_bad_delete')
    config.add_route('deletion_review_good_delete', '/productspiders/deletion_review_good_delete')
    config.add_route('deleted_products_errors', '/productspiders/deleted_products_errors')
    config.add_route('deleted_products_mark_as_fixed', '/productspiders/deleted_products_mark_as_fixed')
    config.add_route('show_deleted_products', '/productspiders/show_deleted_products')
    config.add_route('deleted_products_errors_json', '/productspiders/deleted_products_errors_json')
    config.add_route('save_deletions_error_assignment', '/productspiders/save_deletions_error_assignment')
    config.add_route('assembla_deletions_ticket_get', '/productspiders/assembla/deletions-ticket-get')
    config.add_route('assembla_deletions_ticket_submit', '/productspiders/assembla/deletions-ticket-submit')


    config.add_route('list_worker_servers', '/productspiders/workers')
    config.add_route('config_worker_server', '/productspiders/worker_server')
    config.add_route('delete_worker_server', '/productspiders/delete_worker_server')

    config.add_route('list_additional_fields_groups', '/productspiders/additional_fields_groups')
    config.add_route('config_additional_fields_group', '/productspiders/additional_fields_group')
    config.add_route('delete_additional_fields_group', '/productspiders/delete_additional_fields_group')

    config.add_route('set_starred_error', '/productspiders/set_starred')

    config.add_route('check_crawl_method', '/productspiders/spiders/{account}/{spider}/check_crawl_method')

    config.add_route('spider_exceptions', '/productspiders/spider_exceptions')
    config.add_route('exception_log', '/productspiders/exception_log')

    config.add_route('delisted_duplicates', '/productspiders/delisted_duplicates')
    config.add_route('delisted_duplicates_data', '/productspiders/delisted_duplicates.json')
    config.add_route('run_delisted_duplicates_fixer', '/productspiders/run_delisted_duplicates_fixer.json')
    config.add_route('delisted_duplicates_fixer_status', '/productspiders/delisted_duplicates_fixer_status.json')
    config.add_route('delisted_duplicates_detector_config', '/productspiders/delisted_duplicates_detector_config.json')
    config.add_route('run_delisted_duplicates_detector', '/productspiders/run_delisted_duplicates_detector.json')
    config.add_route('delisted_duplicates_detector_status', '/productspiders/delisted_duplicates_detector_status.json')
    config.add_route('delisted_duplicates_export_errors_csv', '/productspiders/delisted_duplicates_errors.csv')
    config.add_route('delisted_duplicates_import_config', '/productspiders/delisted_duplicates_import_config.json')
    config.add_route('run_delisted_duplicates_import', '/productspiders/run_delisted_duplicates_import')
    config.add_route('delisted_duplicates_import_status', '/productspiders/delisted_duplicates_import_status.json')

    config.add_route('remove_duplicates', '/productspiders/remove_duplicates')
    config.add_route('run_remove_duplicates_task', '/productspiders/run_remove_duplicates_task.json')
    config.add_route('remove_duplicates_status', '/productspiders/remove_duplicates_status.json')

    config.add_route('spiders_upload', '/productspiders/spiders_upload')
    config.add_route('download_spider_upload', '/productspiders/download_spider_upload')
    config.add_route('spider_upload_deployed', '/productspiders/spider_upload_deployed')

    config.add_route('admin_userlogs', '/productspiders/admin_userlogs')
    config.add_route('spiders_user_log_report_data', '/productspiders/spiders_user_log_report_data.json')

    config.add_route('get_accounts_crawls_stats', '/productspiders/get_accounts_crawls_stats.json')
    config.add_route('get_spiders_crawls_stats', '/productspiders/get_spiders_crawls_stats.json')
    config.add_route('get_spiders_upload_stats', '/productspiders/get_spiders_upload_stats.json')
    config.add_route('get_crawlers_weekly_report', '/productspiders/get_crawlers_weekly_report.json')

    config.add_route('get_latest_scrapy_stats', '/productspiders/get_latest_scrapy_stats')

    config.add_route('server_stats', '/productspiders/server_stats')
    config.add_route('current_server_stats', '/productspiders/current_server_stats.json')
    config.add_route('current_spider_stats', '/productspiders/current_spider_stats.json')
    config.add_route('historical_server_stats', '/productspiders/historical_server_stats.json')
    config.add_route('app_stats', '/productspiders/app_stats')
    config.add_route('importer_stats', '/productspiders/importer_stats.json')
    config.add_route('spider_issues', '/productspiders/spider_issues')
    config.add_route('scheduled_issues', '/productspiders/scheduled_issues.json')
    config.add_route('restart_scheduled', '/productspiders/restart_scheduled.json')

    config.add_route('last_log_file', '/productspiders/last_log_file')

    config.add_route('spider_events', '/productspiders/spider_events')
    config.add_route('additional_changes_stats', '/productspiders/additional_changes_stats')
    config.add_route('get_running_crawl_stats', '/productspiders/running_crawl_stats')

    config.include(security.add_authorization)

    return config.make_wsgi_app()
