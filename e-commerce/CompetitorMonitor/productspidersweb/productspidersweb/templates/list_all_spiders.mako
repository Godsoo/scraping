<html>
<head>
<script type="text/javascript" src="/productspiders/static/js/knockout-2.2.1.js"></script>
<script type="text/javascript" src="/productspiders/static/js/underscore-1.3.3.js"></script>
<script type="text/javascript" src="/productspiders/static/js/jquery-1.9.1.min.js"></script>
<script type="text/javascript" src="/productspiders/static/js/jquery.simplemodal.1.4.4.js"></script>

<link rel="stylesheet" type="text/css" href="/productspiders/static/css/jquery.dataTables.css"/>
<script type="text/javascript" src="/productspiders/static/js/jquery.dataTables.1.9.0.js"></script>

<script type="text/javascript" src="/productspiders/static/assets/knockout.Extensions/cog.js"></script>
<script type="text/javascript" src="/productspiders/static/assets/knockout.Extensions/cog.utils.js"></script>
<script type="text/javascript"
        src="/productspiders/static/assets/knockout.Extensions/knockout.bindings.dataTables.js"></script>

<style type="text/css">
    #simplemodal-overlay {
        background-color: #000;
    }

    #simplemodal-container {
        background-color: #333;
        border: 8px solid #444;
        padding: 12px;
    }

    #simplemodal-container a.modalCloseImg {
        background: url(/productspiders/static/images/x.png) no-repeat; /* adjust url as required */
        width: 25px;
        height: 29px;
        display: inline;
        z-index: 3200;
        position: absolute;
        top: -15px;
        right: -18px;
        cursor: pointer;
    }

    table.datatable td {
        padding: 3px 2px;
    }
</style>

<script type="text/javascript">
function set_crawl_valid(crawl_id, reload) {
    if (reload === undefined) {
        reload = true;
    }
    $.post('/productspiders/set_valid', {crawl_id:crawl_id}, function (data) {
        if (data.error) {
            alert(data.error);
        }
        else if (reload) {
            location.reload(true);
        }
    });
}

function delete_invalid_crawl(crawl_id, reload) {
    if (reload === undefined) {
        reload = true;
    }
    $.post('/productspiders/delete_crawl', {crawl_id:crawl_id}, function (data) {
        if (reload) {
            location.reload(true);
        }
    });
}

function upload_changes(spider_id, real_upload, reload) {
    if (reload === undefined) {
        reload = true;
    }
    $.post('/productspiders/upload', {spider_id:spider_id, real_upload:real_upload}, function (data) {
        if (reload) {
            location.reload(true);
        }
    });
}

function show_errors(crawl_id) {
    $.getJSON('/productspiders/error_message/' + crawl_id, {}, function (data) {
        alert(data.error_message);
    });
}

$(document).ready(function () {
    $('#spiders').dataTable({"iDisplayLength":100, "bStateSave":true});
    $("#spiders_filter input").focus();
});
</script>

</head>
<body>
<a href="${request.route_url('logout')}" title="Logout">Logout</a>
<h1>Spiders</h1>

<div>
    % if show_errors:
        <a href="${request.route_url('list_all_spiders_old')}">View all spiders</a>
        % if show_errors == 'possible':
            <a href="${request.route_url('list_all_spiders_old', _query={'errors': 'real'})}">View spiders with real errors</a>
        % elif show_errors == 'real':
            <a href="${request.route_url('list_all_spiders_old', _query={'errors': 'possible'})}">View spiders with possible errors</a>
        % endif
    % else:
        <a href="${request.route_url('list_all_spiders_old', _query={'errors': 'real'})}">View spiders with real errors</a>
        <a href="${request.route_url('list_all_spiders_old', _query={'errors': 'possible'})}">View spiders with possible errors</a>
    % endif
</div>
<table id="spiders">
    <thead>
    <tr>
        <td>Date</td>
        <td>Spider</td>
        <td>Website ID</td>
        <td>View Crawls</td>
        <td>Crawl Status</td>
        <td>Validation</td>
        <td>Delete Crawl</td>
        <td>Upload</td>
        <td>Status</td>
        <td>Account</td>
        <td>Automatic Upload</td>
        <td>Config</td>
        <td>View logs</td>
        <td>Show errors</td>
    </tr>
    </thead>
    <tbody>
            % for spider in spiders:
            <tr>
                <td>${spider.crawls[-1].crawl_date if spider.id and spider.crawls else ''}</td>
                <td>${spider.name}</td>
                <td>${spider.website_id or ''}</td>
            <td>
                % if spider.id:
                    <a href="${request.route_url('list_crawls', spider_id=spider.id)}">View Crawls</a>
                % endif
            </td>
                <td>${spider.crawls[-1].status if spider.id and spider.crawls else ''}</td>
            <td>
                % if spider.crawls and spider.crawls[-1].status == "errors_found":
                    <a href="javascript: set_crawl_valid(${spider.crawls[-1].id})">Set as valid</a>
                % endif
                % if spider.crawls and spider.crawls[-1].status == "upload_errors":
                  <a href="javascript: upload_changes(${crawl.id})">Reupload</a>
                % endif
            </td>
            <td>
                % if spider.crawls and spider.crawls[-1].status == "errors_found":
                    <a href="javascript: delete_invalid_crawl(${spider.crawls[-1].id})">Delete invalid crawl</a>
                % endif
            </td>
            <td>
                % if spider.crawls and spider.crawls[-1].status == "processing_finished":
                    <a href="javascript: upload_changes(${spider.id}, '1')">Upload Changes</a>
                % endif
            </td>
            <td>
                % if spider.id and spider.enabled:
                    <div style="color: green">Enabled</div>
                % else:
                    <div style="color: red">Disabled</div>
                % endif
            </td>
            <td>
                % if spider.id:
                    <p>${spider.account.name}</p>
                % endif
            </td>
            <td>
                % if spider.id and spider.automatic_upload:
                    <div style="color: green">Enabled</div>
                % else:
                    <div style="color: red">Disabled</div>
                % endif
            </td>

            <td>
                % if spider.account:
                    <a href="/productspiders/configspider/${spider.account.name}/${spider.name}">Config</a>
                % endif
            </td>

            <td>
                % if spider.id:
                    <a href="${spider.logs_url}">View Logs</a>
                % endif
            </td>
            <td>
                % if spider.crawls and spider.crawls[-1].status == "errors_found":
                    <a href="javascript: show_errors(${spider.crawls[-1].id});">Show errors</a>
                % endif
            </td>
            </tr>
            % endfor
    </tbody>
</table>
</body>
</html>
