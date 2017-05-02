<html>
<head>
<script type="text/javascript" src="/productspiders/static/js/knockout-2.2.1.js"></script>
<script type="text/javascript" src="/productspiders/static/js/underscore-1.3.3.js"></script>
<script type="text/javascript" src="/productspiders/static/js/jquery-1.9.1.min.js"></script>
<script type="text/javascript" src="/productspiders/static/js/jquery.simplemodal.1.4.4.js"></script>

<link rel="stylesheet" type="text/css" href="/productspiders/static/css/jquery.dataTables.css"/>
<script type="text/javascript" src="/productspiders/static/js/jquery.dataTables.1.9.0.js"></script>
<script type="text/javascript" src="/productspiders/static/js/jquery.form.js"></script>

<script type="text/javascript" src="/productspiders/static/assets/knockout.Extensions/cog.js"></script>
<script type="text/javascript" src="/productspiders/static/assets/knockout.Extensions/cog.utils.js"></script>
<script type="text/javascript" src="/productspiders/static/assets/knockout.Extensions/knockout.bindings.dataTables.js"></script>

<link rel="stylesheet" type="text/css" href="/productspiders/static/css/simplemodal.css"/>

<script type="text/javascript" src="/productspiders/static/js/deleted_products.js"></script>

<script type="text/javascript">
    var drs_url = '${json_url |n}';

    var assembla_authorized;
    % if assembla_authorized:
    assembla_authorized = true;
    % else:
    assembla_authorized = false;
    % endif
    var assembla_users = ${assembla_users |n};
    var assembla_ticket_submit_url = '${assembla_ticket_submit_url |n}';

    var view_model;
    var data_table;
    var data_table_options = {"iDisplayLength":100, "bStateSave":true};
    var assembla_config = {
        'authorized': assembla_authorized,
        'users': assembla_users,
        'ticket_submit_url': assembla_ticket_submit_url
    };

    $(document).ready(function () {
        drs_ko.init(drs_url, assembla_config, $('#drs'));
    });
</script>
</head>
<body>
    <a href="${request.route_url('logout')}" title="Logout">Logout</a>
    <br /><br />
    <a href="${request.route_url('home')}" title="Home">Home</a>

<h1>Deleted products errors</h1>
<div>

        % if not assembla_authorized:
            <br />
            <a href="${assembla_authorization_url}">Login to Assembla</a>
        % endif

</div>
<br />
<div>
    <button data-bind="click: getData">Refresh</button>
</div>
<table id="drs_ko" data-bind="dataTable: {
        dataSource: drs,
        rowTemplate: 'dr_row',
        columns: [
            'found_date',
            'crawl_date',
            'account_name',
            'site',
            'total',
            'matched_count',
            'unmatched_count',
            'products_url',
            'total',
            'assigned_to',
            'assigned'
        ],
        options: {'iDisplayLength':25, 'bStateSave':true, 'bAutoWidth': false}
    }">
    <thead>
    <tr>
        <td>Found Date</td>
        <td>Crawl Date</td>
        <td>Account</td>
        <td>Spider</td>
        <td>Deleted Products</td>
        <td>Matched</td>
        <td>Unmatched</td>
        <td>Show products</td>
        <td>Mark as fixed</td>
        <td>Assigned</td>
        <td>Assign</td>
    </tr>
    </thead>
    <tbody>
    </tbody>
</table>
<script type="text/html" id="dr_row">
    <td data-bind="text: found_date"></td>
    <td data-bind="text: crawl_date"></td>
    <td data-bind="text: account_name"></td>
    <td data-bind="text: site"></td>
    <td data-bind="text: total"></td>
    <td data-bind="text: matched_count"></td>
    <td data-bind="text: unmatched_count"></td>
    <td><a data-bind="click: $root.show_products" href="#">Show products</a></td>
    <td><a data-bind="click: $root.mark_error_as_fixed" href="#">Mark as fixed</a></td>
    <td>
        <span data-bind="visible: assigned(), text: assigned_to()"></span>
    </td>
    <td>
        <button data-bind="click: $root.edit_assigned_to, text: assigned() ? 'Change' : 'Assign'">Assign</button>
    </td>
</script>
</body>
</html>
