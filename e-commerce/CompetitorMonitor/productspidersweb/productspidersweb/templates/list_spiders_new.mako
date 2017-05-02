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
    <script type="text/javascript"
            src="/productspiders/static/assets/knockout.Extensions/knockout.bindings.dataTables.js"></script>

    <link rel="stylesheet" type="text/css" href="/productspiders/static/css/simplemodal.css"/>
    <link rel="stylesheet" type="text/css" href="/productspiders/static/css/notes.css"/>

    <script type="text/javascript" src="/productspiders/static/js/spiders.js?version=1.3"></script>
    <style type="text/css">


   </style>

    <script type="text/javascript">
        var spiders_url = '${json_url |n}';

        var assembla_authorized;
        % if assembla_authorized:
            assembla_authorized = true;
        % else:
            assembla_authorized = false;
        % endif
        var developers = ${developers |n};
        var assembla_ticket_submit_url = '${assembla_ticket_submit_url |n}';

        var errors;
        % if show_errors:
            errors = '${show_errors}';
        % else:
            errors = false;
        % endif

        var view_model;
        var data_table;
        var data_table_options = {"iDisplayLength": 100, "bStateSave": true};
        var assembla_config = {
            'authorized': assembla_authorized,
            'ticket_submit_url': assembla_ticket_submit_url
        };

        $(document).ready(function () {
            spiders_ko.init(spiders_url, errors, assembla_config, developers, $('#spiders'));
        });

        function view_notes(site_id) {
          $.modal.defaults.closeClass = "close";
          $('#modalnts').load('/productspiders/spider_notes/' + site_id);
          $('#modalnts').modal({overlayClose: true, close: true});
      }
         $(document).ready(function () {
          $('body').on('hidden.bs.modal', '.modal', function () {
              $(this).removeData('bs.modal');
          });
      });
    </script>
</head>
<body>
<div class="modal fade bs-example-modal-sm" id="modalnts" style="display: none" tabindex="-1" role="dialog" aria-hidden="true"></div>
<a href="${request.route_url('logout')}" title="Logout">Logout</a>
<br/><br/>
<a href="${request.route_url('home')}" title="Home">Home</a>

<h1>Spiders for ${account}</h1>
<div>
% if show_errors:
    <a href="${request.route_url('list_account_spiders', account=account)}">View all spiders</a>
    % if show_errors == 'possible':
        <a href="${request.route_url('list_account_spiders', account=account, _query={'errors': 'real'})}">View spiders with real errors</a>
    % elif show_errors == 'real':
        <a href="${request.route_url('list_account_spiders', account=account, _query={'errors': 'possible'})}">View spiders with possible errors</a>
    % endif
    % if not assembla_authorized:
        <br />
        <a href="${assembla_authorization_url}">Login to Assembla</a>
    % endif
% else:
    <a href="${request.route_url('list_account_spiders', account=account, _query={'errors': 'real'})}">View spiders with real errors</a>
    <a href="${request.route_url('list_account_spiders', account=account, _query={'errors': 'possible'})}">View spiders with possible errors</a>
% endif
</div>
<br />
<div>
    <button data-bind="click: getData">Refresh</button>
</div>
<table id="spiders_ko" data-bind="dataTable: {
        dataSource: spiders,
        rowTemplate: 'spider_row',
        columns: [
            'crawl_date',
            'account_name',
            'name',
            'website_id',
            'crawls_url',
            'crawl_status',
            'is_valid',
            'is_valid',
            'is_valid',
            'account_enabled',
            'enabled',
            'status',
            'parse_method',
            'upload_testing_account',
            'automatic_upload',
            'config_url',
            'logs_url',
            'errors_url',
            % if show_errors:
                'status',
                % if show_errors == 'real':
                    'assigned_to',
                    'assigned',
                    //'website_id'
                % endif
            % endif
        ],
        options: {'iDisplayLength':25, 'bStateSave':true, 'bAutoWidth': false}
    }">
    <thead>
    <tr>
        <td style="width: 93px">Date</td>
        <td style="width: 100px">Account</td>
        <td>Spider</td>
        <td>Website ID</td>
        <td>View Crawls</td>
        <td>Crawl Status</td>
        <td>Validation</td>
        <td>Delete Crawl</td>
        <td>Upload</td>
        <td>Run</td>
        <td>Account</td>
        <td>Status</td>
        <td>Method</td>
        <td>Testing</td>
        <td>Automatic Upload</td>
        <td>Config</td>
        <td>View logs</td>
        <td>Show errors</td>
        % if show_errors:
            <td>Error status</td>
            % if show_errors == 'real':
                <td>Assigned</td>
                <td>Assign</td>
##                <td>Upload fix</td>
            % endif
        % endif
    </tr>
    </thead>
    <tbody>
    </tbody>
</table>
<script type="text/html" id="spider_row">
    <td data-bind="text: crawl_date"></td>
    <td data-bind="text: account_name"></td>
    <td>
        <div data-bind="text: name"></div>
        <a data-bind="attr: {href: 'javascript: view_notes(' + id() +')'}" href="" style="text-decoration: none"><img src="/productspiders/static/images/note.png" style="float: left"/>(<span data-bind="text:notes_count"></span>)</a>
        <a data-bind="click: $root.show_doc, if: doc_url()" href="#" style="text-decoration: none">(?)</a>
        <a data-bind="click: $root.show_running_stats, if: running_stats_url()" href="#" style="text-decoration: none">(s)</a>
    </td>
    <td data-bind="text: website_id"></td>
    <td><a data-bind="click: $root.show_spider_crawls, if: crawls_url()" href="#">View Crawls</a></td>
    <td data-bind="text: crawl_status"></td>
    <td>
        <a data-bind="click: $root.set_crawl_valid, if: set_valid_url()" href="#">Set valid</a>
        <a data-bind="click: $root.reupload, if: reupload_url()" href="#">Reupload</a>
    </td>
    <td><a data-bind="click: $root.delete_invalid_crawl, if: delete_crawl_url()" href="#">Delete invalid crawl</a>
    </td>
    <td><a data-bind="click: $root.upload_changes, if: upload_url()" href="#">Upload changes</a></td>
    <td><a data-bind="click: $root.run_spider, if: $root.runnable($data)" href="#">Run</a></td>
    <td data-bind="text: account_status, style: {color: account_enabled() ? 'green' : 'red'}"></td>
    <td data-bind="text: status, style: {color: enabled() ? 'green' : 'red'}"></td>
    <td data-bind="text: parse_method"></td>
    <td data-bind="text: upload_testing_account() ? 'Yes' : 'No', style: {color: upload_testing_account() ? 'green' : 'red'}"></td>
    <td data-bind="text: automatic_upload_text, style: {color: automatic_upload() ? 'green' : 'red'}"></td>
    <td><a data-bind="click: $root.show_spider_config, if: config_url()" href="#">Config</a></td>
    <td>
        <a data-bind="click: $root.show_spider_logs, if: logs_url()" href="#">View logs</a>
        <a data-bind="click: $root.show_latest_logs, if: logs_url()" href="#">(Latest)</a>
    </td>
    <td><a data-bind="click: $root.show_spider_errors, if: errors_url()" href="#">Show errors</a></td>
    % if show_errors:
        <td><a data-bind="click: $root.change_error_status, text: $root.change_error_status_text()" href="#"></a></td>
        % if show_errors == 'real':
            <td>
                <span data-bind="visible: assigned(), text: assigned_to_name()"></span>
            </td>
            <td>
                <button data-bind="click: $root.edit_assigned_to, text: assigned() ? 'Change' : 'Assign'">Assign</button>
            </td>
##            <td>
##                <button data-bind="click: $root.upload_fix">Upload</button>
##            </td>
        % endif
    % endif
</script>
</body>
</html>
