<%inherit file="base.html"/>

<%block name="content">

    <div class="modal fade" id="dialog" tabindex="-1" role="dialog" aria-hidden="true">
      <div class="modal-dialog">
      <div class="modal-content">
        <div class="modal-header">
          <button id="modalprdclose" type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>
          <h4 class="modal-title"><strong>Task Status</strong></h4>
        </div>
        <div id="status-body" class="modal-body">
        </div>
      </div>
    </div>
    </div>

    <div class="container">
    <div class="row">
        <div class="col-md-12">
	  <form id="detection-form" class="form-inline" role="form" method="POST">
              <div class="form-group">
                    <select id="spider-id" class="selectpicker" title="Websites" data-live-search="true">
                      % for s in spiders:
                      <option value="${s.id}">${s.name}</option>
                      % endfor
                    </select>
                </div>
		<button id="detect" class="btn btn-primary">Detect</button>
		<button id="remove" class="btn btn-danger">Remove</button>
          </form>
          <fieldset>
              <legend>Duplicates</legend>
              <div id="filter-bar"></div>
              <table id="tbl"
                 data-toggle="table"
                 data-toolbar="#filter-bar"
                 data-search="true"
                 data-show-toggle="true"
                 data-show-columns="true"
                 data-show-refresh="true"
                 data-pagination="true"
                 data-page-size="50"
		 data-page-list="[5, 10, 20, 50, 100, 200]"
                 data-show-export="true"
                 class="table table-striped table-bordered table-condensed gray_table">
                  <thead>
                      <tr>
		          <th data-field="crawl_date" data-align="center" data-sortable="true">Crawl Date</th>
                          <th data-field="name" data-align="center" data-sortable="true">Product Name</th>
                          <th data-field="identifier" data-align="center" data-sortable="true">Identifier</th>
                          <th data-field="url" data-align="center" data-formatter="url_formatter" >Link</th>
                      </tr>
                  </thead>
              </table>
         </fieldset>
       </div>
    </div>
    </div>

    <script>

    function url_formatter(value, row, index) {
        return '<a href="' + value + '" target="_blank">View</a>';
    }

    $(document).ready(function(){
        $('.selectpicker').selectpicker();
	$('#tbl').bootstrapTable();
    });

    function update_detect_status(task_id) {
        var status_url = '/productspiders/remove_duplicates_status.json?id=' + task_id + '&detect=1';
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
		    $('#tbl').bootstrapTable('load', $.parseJSON(data['result']));
                    $('#tbl').bootstrapTable('hideLoading');
                }
                $('#status-body').html(html_body);
            } else {
	        html_body += '<div class="alert alert-info" role="alert">' + data['status'] + '</div>';
                $('#status-body').html(html_body);
                setTimeout(function() {
                    update_detect_status(task_id);
                }, 2000);
            }
        });
    }

    function update_remove_status(task_id) {
        var status_url = '/productspiders/remove_duplicates_status.json?id=' + task_id;
        $.getJSON(status_url, function(data) {
            var html_body = '<div class="progress">' +
                '<div class="progress-bar" role="progressbar" aria-valuenow="' + data['current'] + '" aria-valuemin="0" aria-valuemax="' + data['total'] + '" style="width: ' + data['current'] + '%;">' +
                    data['current'] + '% Complete' +
                '</div>' +
            '</div>';
            if (data['state'] != 'PENDING' && data['state'] != 'WORKING') {
                if (data['state'] == 'FAILURE') {
                    html_body += '<div class="alert alert-danger" role="alert">' + data['status'] + '</div>';
                }
                $('#status-body').html(html_body);
            } else {
	        html_body += '<div class="alert alert-info" role="alert">' + data['status'] + '</div>';
                $('#status-body').html(html_body);
                setTimeout(function() {
                    update_remove_status(task_id);
                }, 2000);
            }
        });
    }

    $('#remove').click(function(e){
        e.preventDefault();
        var params = [];
	var spider_id = $( "#spider-id" ).val();
	params.push('spider_id=' + spider_id);
        $.getJSON('/productspiders/run_remove_duplicates_task.json?' + params.join('&'), function(data){
            if (data['task_id'] != -1) {
	        $('#dialog').modal('toggle');
                update_remove_status(data['task_id']);
            }
        });
    });

    $('#detect').click(function(e){
        e.preventDefault();
        $('#tbl').bootstrapTable('showLoading');
        var params = [];
	var spider_id = $( "#spider-id" ).val();
	params.push('spider_id=' + spider_id);
	params.push('detect=1');
        $.getJSON('/productspiders/run_remove_duplicates_task.json?' + params.join('&'), function(data){
            if (data['task_id'] != -1) {
	        $('#dialog').modal('toggle');
                update_detect_status(data['task_id']);
            }
        });
    });

    </script>

</%block>
