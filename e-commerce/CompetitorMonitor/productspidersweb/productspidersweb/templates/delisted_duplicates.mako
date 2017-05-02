<%inherit file="base.html"/>

<%block name="content">

    <div class="modal fade" id="dialog" tabindex="-1" role="dialog" aria-hidden="true">
    </div>

    <div class="modal fade" id="fixer-dialog" tabindex="-1" role="dialog" aria-hidden="true">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <button id="modalprdclose" type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>
                    <h4 class="modal-title"><strong>Delisted Duplicates Fixer</strong></h4>
                </div>
                <div id="fixer-body" class="modal-body">
                </div>
            </div>
        </div>
    </div>

    <div class="container">
    <div class="row">
        <div class="col-md-12">
          <fieldset>
              <legend>Delisted Duplicate Errors
              <div style="float:right;margin:2px;">
		<button id="detector-btn" class="btn btn-warning" type="button">Detect</button>
		<button id="import-btn" class="btn btn-info" type="button">Import</button></div></legend>
              <div id="filter-bar"></div>
              <table id="tbl"
                 data-toggle="table"
                 data-url="delisted_duplicates.json"
                 data-toolbar="#filter-bar"
                 data-search="true"
                 data-show-toggle="true"
                 data-show-columns="true"
                 data-show-refresh="true"
                 data-pagination="true"
		 data-side-pagination="server"
                 data-page-size="50"
		 data-page-list="[5, 10, 20, 50, 100, 200]"
                 data-show-export="true"
                 class="table table-striped table-bordered table-condensed gray_table">
                  <thead>
                      <tr>
                          <th data-field="website_id" data-align="center" data-sortable="true">Website ID</th>
                          <th data-field="website_name" data-align="center" data-sortable="true">Website</th>
                          <th data-field="crawl_date" data-align="center" data-sortable="true">Crawl Date</th>
                          <th data-field="fixed" data-align="center" data-formatter="fix_formatter" >Fix</th>
			  <th data-field="fixed" data-align="center" data-formatter="export_formatter" >Export</th>
                      </tr>
                  </thead>
              </table>
         </fieldset>
       </div>
    </div>
    </div>

    <script id="detection-modal-template" type="text/template">

    <%text>

    <div class="modal-dialog">
      <div class="modal-content">
        <div class="modal-header">
          <button id="modalprdclose" type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>
          <h4 class="modal-title"><strong>Delisted Duplicates Detector</strong></h4>
        </div>
        <div id="detect-body" class="modal-body">
            <form id="detection-form" role="form" method="POST">
                <div class="form-group">
                    <select id="detection-spider" class="selectpicker" title="Spider">
                      <% _.each(websites, function(w) { %>
                      <option value="<%- w.id %>"><%- w.name %></option>
                      <% }); %>
                    </select>
                </div>
                <div class="form-group">
                    <select id="detection-field" class="selectpicker" multiple title="Fields" data-live-search="true">
                      <% _.each(field_names, function(p) { %>
                      <option value="<%- p %>"><%- p %></option>
                      <% }); %>
                    </select>
                </div>
                <div class="checkbox">
                  <label>
                    <input type="checkbox" id="ignore-case" />
                  <strong>Ignore case</strong></label>
                </div>
            </form>
            <button id="run-detector-btn" type="button" class="btn btn-primary btn-lg btn-block">Run</button>
            <button id="cancel-detector-btn" type="button" class="btn btn-default btn-lg btn-block">Cancel</button>
        </div>
      </div>
    </div>

    <script>

    $('.selectpicker').selectpicker();
    $('[data-toggle="tooltip"]').tooltip();

    function update_status(task_id) {
        var status_url = '/productspiders/delisted_duplicates_detector_status.json?id=' + task_id;
        $.getJSON(status_url, function(data) {
            var html_body = '<div class="progress">' +
                '<div class="progress-bar" role="progressbar" aria-valuenow="' + data['current'] + '" aria-valuemin="0" aria-valuemax="' + data['total'] + '" style="width: ' + data['current'] + '%;">' +
                    data['current'] + '% Complete' +
                '</div>' +
            '</div>';
            if (data['state'] != 'PENDING' && data['state'] != 'WORKING') {
                if (data['state'] == 'FAILURE') {
                    html_body += '<div class="alert alert-danger" role="alert">' + data['status'] + '</div>';
                } else if (data['state'] == 'SUCCESS') {
                    if (data['result'] > 0) {
                        html_body = '<p><mark>' + data['result'] + '</mark> issues have been added to the list.</p>';
                    } else {
                        html_body = 'No issues found';
                    }
                    $('#tbl').bootstrapTable('refresh');
                }
                $('#detect-body').html(html_body);
            } else {
	        html_body += '<div class="alert alert-info" role="alert">' + data['status'] + '</div>';
                $('#detect-body').html(html_body);
                setTimeout(function() {
                    update_status(task_id);
                }, 2000);
            }
        });
    }

    $('#run-detector-btn').click(function(){
        var params = [];
        params.push('website_id=' + $("#detection-spider" ).val());
        var fields = $( "#detection-field" ).val() || [];
        $.each(fields, function(fld_i, fld) {
            params.push('field_name=' + fld);
        });
        if ($('#ignore-case').prop('checked')) {
            params.push('ignore_case=1');
        }

        $.getJSON('/productspiders/run_delisted_duplicates_detector.json?' + params.join('&'), function(data){
            if (data['task_id'] != -1) {
                update_status(data['task_id']);
            }
        });
    });

    $('#cancel-detector-btn').click(function(){
        $('#dialog').modal('toggle');
    });

    </script>

    </%text>

    </script>

    <script id="import-modal-template" type="text/template">

    <%text>

    <div class="modal-dialog">
      <div class="modal-content">
        <div class="modal-header">
          <button id="modalprdclose" type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>
          <h4 class="modal-title"><strong>Delisted Duplicates Import</strong></h4>
        </div>
        <div id="import-body" class="modal-body">
            <p>Select and upload a CSV file with the following columns:</p>
            <p><strong>name, old_identifier, new_identifier, old_url, new_url</strong></p>
            <form id="detection-form" role="form" method="POST" enctype="multipart/form-data">
                <div class="form-group">
                    <select id="import-website" class="selectpicker" title="Spider">
                      <% _.each(websites, function(w) { %>
                      <option value="<%- w.id %>"><%- w.name %></option>
                      <% }); %>
                    </select>
                </div>
		<div class="form-group">
                    <input id="import-issues" type="file" name="issues" accept=".csv">
                </div>
            </form>
            <button id="run-import-btn" type="button" class="btn btn-primary btn-lg btn-block">Import</button>
        </div>
      </div>
    </div>

    <script>

    $('.selectpicker').selectpicker();
    $('[data-toggle="tooltip"]').tooltip();

    function update_status(task_id) {
        var status_url = '/productspiders/delisted_duplicates_import_status.json?id=' + task_id;
        $.getJSON(status_url, function(data) {
            var html_body = '<div class="progress">' +
                '<div class="progress-bar" role="progressbar" aria-valuenow="' + data['current'] + '" aria-valuemin="0" aria-valuemax="' + data['total'] + '" style="width: ' + data['current'] + '%;">' +
                    data['current'] + '% Complete' +
                '</div>' +
            '</div>';
            if (data['state'] != 'PENDING' && data['state'] != 'WORKING') {
                if (data['state'] == 'FAILURE') {
                    html_body += '<div class="alert alert-danger" role="alert">' + data['status'] + '</div>';
                } else if (data['state'] == 'SUCCESS') {
                    html_body = '<p>The file has been uploaded successfully</p>';
                    $('#tbl').bootstrapTable('refresh');
                }
                $('#import-body').html(html_body);
            } else {
	        html_body += '<div class="alert alert-info" role="alert">' + data['status'] + '</div>';
                $('#import-body').html(html_body);
                setTimeout(function() {
                    update_status(task_id);
                }, 2000);
            }
        });
    }

    $('#run-import-btn').click(function(){
        var website_id = $("#import-website" ).val();
	var issues_file = $("#import-issues" )[0].files[0];
        var form_data = new FormData();
        form_data.append('website_id', website_id);
        form_data.append('issues', issues_file);
        $.ajax({
            url: '/productspiders/run_delisted_duplicates_import',
            data: form_data,
            processData: false,
            contentType: false,
	    mimeType: 'multipart/form-data',
            type: 'POST',
	    dataType: 'json',
            success: function(data){
                if (data['task_id'] != -1) {
                    update_status(data['task_id']);
                }
            }
        });

        /*
        $.post('/productspiders/run_delisted_duplicates_import',
            form_data,
	    function(data){
                if (data['task_id'] != -1) {
                    update_status(data['task_id']);
                }
            });
	*/
        });

    </script>

    </%text>

    </script>

    <script>

    function fixer_update_status(task_id) {
        var status_url = '/productspiders/delisted_duplicates_fixer_status.json?id=' + task_id;
        $.getJSON(status_url, function(data) {
            var html_body = '<div class="progress">' +
                '<div class="progress-bar" role="progressbar" aria-valuenow="' + data['current'] + '" aria-valuemin="0" aria-valuemax="' + data['total'] + '" style="width: ' + data['current'] + '%;">' +
                    data['current'] + '% Complete' +
                '</div>' +
            '</div>';
            if (data['state'] != 'PENDING' && data['state'] != 'WORKING') {
                if (data['state'] == 'FAILURE') {
                    html_body += '<div class="alert alert-danger" role="alert">' + data['status'] + '</div>';
                } else if (data['state'] == 'SUCCESS') {
                    $('#tbl').bootstrapTable('refresh');
                }
                $('#fixer-body').html(html_body);
            } else {
	        html_body += '<div class="alert alert-info" role="alert">' + data['status'] + '</div>';
                $('#fixer-body').html(html_body);
                setTimeout(function() {
                    fixer_update_status(task_id);
                }, 2000);
            }
        });
    }

    function fix_issue(issue_id){
        var html_body = '<span style="color: blue;">Wait a moment please...</span>';
        $('#fixer-body').html(html_body);
        $('#fixer-dialog').modal('toggle');
        $.getJSON('/productspiders/run_delisted_duplicates_fixer.json?id=' + issue_id, function(data){
            if (data['task_id'] != -1) {
                fixer_update_status(data['task_id']);
            } else {
	        var html_body = '<span style="color: red;">Sorry an error has occurred</span>';
                $('#fixer-body').html(html_body);
            }
        });
    };

    function fix_formatter(value, row, index) {
        if (value) {
            return '<span style="color:red;">Fixed</span>';
	} else {
            return '<a href="javascript: fix_issue(' + row['id'] + ');">Run</a>';
        }
    }

    function export_formatter(value, row, index) {
        return '<a href="/productspiders/delisted_duplicates_errors.csv?id=' + row['id'] + '" title="Export" class="btn btn-default"><i class="glyphicon glyphicon-export icon-export"></i></a>';
    }

    function open_modal_detector() {
        var detector_modal_tmp = _.template(
            $('#detection-modal-template').html()
        );
        var detector_config_url = '/productspiders/delisted_duplicates_detector_config.json';
        $.getJSON(detector_config_url, function(data){
            $('#dialog').html(detector_modal_tmp(data));
            $('#dialog').modal('toggle');
        });
    }

    function open_modal_import() {

        var import_modal_tmp = _.template(
            $('#import-modal-template').html()
        );

        var import_config_url = '/productspiders/delisted_duplicates_import_config.json';
        $.getJSON(import_config_url, function(data){
            $('#dialog').html(import_modal_tmp(data));
            $('#dialog').modal('toggle');
        });

    }

    $('#detector-btn').click(open_modal_detector);
    $('#import-btn').click(open_modal_import);

    </script>

</%block>
