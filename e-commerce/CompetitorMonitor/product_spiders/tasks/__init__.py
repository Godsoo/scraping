import sys
import os.path

here = os.path.abspath(os.path.dirname(__file__))
product_spiders_root = os.path.dirname(here)
project_root = os.path.dirname(product_spiders_root)
productspidersweb_root = os.path.join(project_root, 'productspidersweb')
sys.path.append(product_spiders_root)
sys.path.append(productspidersweb_root)

from default import (
    restart_tor,
    crawler_report,
    sites_not_uploaded,
    sites_not_uploaded_account,
    sites_not_uploaded_account_2,
    check_failing_proxies_alert,
    send_bsm_missing_full_run_alert,
    send_bsm_missing_full_run_one_month_alert,
)
from fixer import (
    fix_delisted_duplicates,
    detect_duplicates,
    import_delisted_duplicates_issues,
    admin_detect_duplicates_task,
    admin_remove_duplicates_task,
)
from reports import (
    send_enabled_accounts_report,
)
from screenshots import (
    take_screenshot,
)
