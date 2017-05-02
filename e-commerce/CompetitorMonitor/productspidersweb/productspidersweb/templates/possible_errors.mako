<%inherit file="base.html"/>

<%block name="content">

    <style>
    
    hr {
        margin: 5px !important;
    }
    
    </style>

    <script>

    /*********************************
     * iframes
     *********************************/

    function show_modal_iframe(title, src, config) {
        if (config === undefined) {
            config = false;
        }

        $("#dialog").html('' +
            '<div class="modal-content">' +
            '<div class="modal-header">' +
            '  <button id="modalprdclose" type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>' +
            '  <span class="modal-title"><h4><strong>' + title + '</strong></h4></span>' +
            '</div>' +
            '<div class="modal-body">' +
            '<div id="iframe_container">' +
            '</div>' +
            '</div>' +
            '</div>');

        $("#iframe_container").load(src.replace(/ /g, '%20'), function () {

            if (config) {
                $("#iframe_container form").submit(function (event) {
                    event.preventDefault();
                    var params = $(this).serialize();
                    $.ajax({
                      type: "POST",
                      url: $(this).attr('action'),
                      data: params,
                      success: function() {
                        $('#dialog').modal('toggle');
                      }
                    });
                });
            }
        });

        $('#dialog').modal('toggle');
    }
    </script>

    <div class="modal fade" id="dialog" tabindex="-1" role="dialog" aria-hidden="true">
    </div>

    <div style="margin:5px;">

    <div id="filter-bar"></div>
    <table id="tbl"
       data-toggle="table"
       data-url="possible_errors.json"
       data-toolbar="#filter-bar"
       data-show-toggle="true"
       data-show-columns="true"
       data-show-filter="true"
       data-show-refresh="true"
       data-pagination="true"
       data-show-export="true"
       class="table table-striped table-bordered table-condensed gray_table"
       style="font-size:12px;">
        <thead>
            <tr>
                <th data-field="priority_possible_errors" data-formatter="priority_formatter" data-align="center" data-sortable="true">Priority</th>
                <th data-field="last_crawl_run_count" data-formatter="run_times_formatter" data-align="center" data-sortable="true">Run times</th>
                <th data-field="crawl_date" data-align="center" data-sortable="true">Date</th>
                <th data-field="account_name" data-formatter="account_formatter" data-sortable="true">Account</th>
                <th data-field="name" data-formatter="spider_formatter" data-sortable="true">Spider</th>
                <th data-field="crawls_count" data-formatter="crawls_formatter" data-align="center" data-sortable="true">Crawls</th>
                <th data-field="products_count" data-formatter="products_formatter" data-align="center" data-sortable="true">Products</th>
                <th data-field="errors_count" data-formatter="errors_formatter" data-align="center" data-sortable="true">Errors</th>
                <th data-field="parse_method" data-align="center" data-sortable="true">Crawl Method</th>
                <th data-field="automatic_upload" data-formatter="automatic_upload_formatter" data-align="center">Automatic Upload</th>
                <th data-formatter="crawl_actions_formatter" data-align="center">Crawl Actions</th>
                <th data-formatter="spider_actions_formatter" data-align="center">Spider Actions</th>
                <th data-formatter="validation_formatter" data-align="center">Validation</th>
            </tr>
        </thead>
    </table>

    </div>

    <script id="errors-template" type="text/template">

        <%text>

        <div class="errors-dialog">
          <div style="float:left;width:100%;" class="modal-content">
            <div class="modal-header">
              <button id="modalprdclose" type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>
              <span class="modal-title"><b><i><%- errors.length %> errors found</i></b></span>
            </div>
            <div class="modal-body">
              <div>
                <% _.each(errors, function(e){ %>
                  <p><%- e.alert_msg %></p>
                <% }); %>
              </div>
            </div>
          </div>
        </div>

        </%text>

    </script>

    <script>

    function priority_formatter(value, row, index) {
        if (row['priority_possible_errors']) {
            return '<span style="color:green;text-align:center;">Yes</span>';
        } else {
            return '';
        }
    }

    function run_times_formatter(value, row, index) {
        if (row['last_crawl_run_count'] > 2) {
            return '<span style="color:red;">' + row['last_crawl_run_count'] + '</span>';
        } else {
            return '<span style="color:blue;">' + row['last_crawl_run_count'] + '</span>';
        }
    }

    function account_formatter(value, row, index) {
        if (row['account_enabled']) {
            return '<span style="color:green;">' + row['account_name'] + '</span>';
        } else {
            return '<span style="color:red;">' + row['account_name'] + '</span>';
        }
    }

    function spider_formatter(value, row, index) {
        if (row['enabled']) {
            return '<span style="color:green;">' + row['name'] + '</span>';
        } else {
            return '<span style="color:red;">' + row['name'] + '</span>';
        }
    }

    function errors_formatter(value, row, index){
        var title = "'Errors for " + row['name'] + "'";
        return '<a style="color:red;" href="javascript: show_modal_iframe(' + title + ',' + "'" + row['errors_url'] + "'" + ');">' + row['errors_count'] + '</a>';
    }

    function crawls_formatter(value, row, index) {
        var title = "'Crawls for " + row['name'] + "'";
        return '<a href="javascript: show_modal_iframe(' + title + ',' + "'" + row['crawls_url'] + "'" + ');">' + row['crawls_count'] + '</a>';
    }

    function products_formatter(value, row, index) {
        var title = "'Products for " + row['name'] + "'";
        return '<a href="javascript: show_modal_iframe(' + title + ',' + "'" + row['products_url'] + "'" + ');">' + row['products_count'] + '</a>';
    }

    function automatic_upload_formatter(value, row, index) {
        if (row['automatic_upload']) {
            return '<span style="color:green;">Enabled</span>';
        } else {
            return '<span style="color:red;">Disabled</span>';
        }
    }

    function crawl_actions_formatter(value, row, index) {
        return '<a href="javascript: re_run(' + row['crawl_id'] + ');">Re-run</a>';
    }

    function spider_actions_formatter(value, row, index) {
        var title = "'Config " + row['name'] + "'";
        var html = '<a href="javascript: show_modal_iframe(' + title + ',' + "'" + row['config_url'] + "'" + ', true);">Config</a>';
        html += '<hr />';
        title = "'Logs for " + row['name'] + "'";
        html += '<a href="javascript: show_modal_iframe(' + title + ',' + "'" + row['logs_url'] + "'" + ');">View logs</a>';
        return html;
    }

    function validation_formatter(value, row, index) {
        var html = '<a href="javascript: set_valid(' + row['crawl_id'] + ');">Set valid</a>';
        html += '<hr />';
        html += '<a href="javascript: mark_as_error(' + row['crawl_id'] + ');">Mark as real error</a>';
        return html;
    }

    function show_errors(crawl_id){
        var errors_tmp = _.template(
            $('#errors-template').html()
        );
        $.getJSON('/productspiders/crawl_errors/' + crawl_id, function(data) {
            $('#dialog').html(errors_tmp(data));
            $('#dialog').modal('toggle');
        });
    }

    function set_valid(crawl_id) {
        $('#tbl').bootstrapTable('remove', {'field': 'crawl_id', 'values': [crawl_id]});
    }

    </script>

</%block>