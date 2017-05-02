<html>
<head>
    <link rel="stylesheet" type="text/css" href="/productspiders/static/css/jquery.dataTables.css"/>
    <script type="text/javascript" src="/productspiders/static/js/jquery-1.9.1.min.js"></script>
    <script type="text/javascript" src="/productspiders/static/js/jquery.dataTables.1.9.0.js"></script>

    <script type="text/javascript">
        function disable_account(account) {
            $.post('/productspiders/disable_account', {account: account}, function (data) {
                location.reload();
            });
        }
        function enable_account(account) {
            $.post('/productspiders/enable_account', {account: account}, function (data) {
                location.reload();
            });
        }
        $(document).ready(function () {
            $('#accounts').dataTable({
                "bStateSave": true
            });
            $("#accounts_filter input").focus();
        });
    </script>
</head>
<body>
<a href="${request.route_url('logout')}" title="Logout">Logout</a>

<h1>Accounts</h1>
<table id="accounts" class="display">
    <thead>
    <tr>
        <td>Account</td>
        <td>Member ID</td>
        <td>Spiders</td>
        <td>Status</td>
        <td>Config</td>
        <td>Disable</td>
    </tr>
    </thead>

    <tbody>
        % for account in accounts:
            <tr>
                <td>${account['name']}</td>
                <td>${account['member_id']}</td>
                <td>
                    <a href="${request.route_url('list_account_spiders_old', account=account['name'])}">View Spiders</a>
                    (<a href="${request.route_url('list_account_spiders', account=account['name'])}">new</a>)
                </td>
                <td>
                    % if account.get('enabled'):
                        <div style="color: green">Enabled</div>
                    % else:
                        <div style="color: red">Disabled</div>
                    % endif
                </td>
                <td><a href="${request.route_url('config_account', account=account['name'])}">Config</a></td>
                <td>
                    % if account.get('enabled'):
                        <a href="javascript: disable_account('${account['name']}')">Disable account</a>
                    % else:
                        <a href="javascript: enable_account('${account['name']}')">Enable account</a>
                    % endif
                </td>
            </tr>
        % endfor
    </tbody>
</table>
<br/>
<a href="${request.route_url('list_all_spiders_old')}">View all spiders (old)</a>
<a href="${request.route_url('list_all_spiders_old', _query={'errors': 'possible'})}">View possible error spiders
    (old)</a>
<a href="${request.route_url('list_all_spiders_old', _query={'errors': 'real'})}">View real error spiders (old)</a>
<br/>
<a href="${request.route_url('list_all_spiders')}">View all spiders (new)</a>
<a href="${request.route_url('list_all_spiders', _query={'errors': 'possible'})}">View possible error spiders (new)</a>
<a href="${request.route_url('list_all_spiders', _query={'errors': 'real'})}">View real error spiders (new)</a>
<a href="/productspiders/manage">Manage</a>
<a href="/productspiders/crawls-stats">Crawls Stats</a>
<a href="/productspiders/proxies">Proxies</a>
<a href="/productspiders/spider_exceptions">Spider Exceptions</a>
<br/>
<a href="/productspiders/list_deleted_products">Deleted Products Review</a>
<a href="/productspiders/deleted_products_errors">Deleted Products Errors</a>
<a href="/productspiders/additional_fields_groups">Additional Fields Groups</a>
</body>
</html>
