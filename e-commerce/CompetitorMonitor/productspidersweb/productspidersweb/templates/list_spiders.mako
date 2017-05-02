<html>
<head>
    <title>${account} spiders</title>
    <link rel="stylesheet" type="text/css" href="/productspiders/static/css/jquery.dataTables.css" />
    <script type="text/javascript" src="/productspiders/static/js/jquery-1.9.1.min.js"></script>
    <script type="text/javascript" src="/productspiders/static/js/jquery.dataTables.1.9.0.js"></script>

    <script type="text/javascript">
        $(document).ready(function() {
                $('#spiders').dataTable({"bStateSave": false});
        });
    </script>

  <script type="text/javascript">
    function set_crawl_valid(crawl_id) {
      $.post('/productspiders/set_valid', {crawl_id: crawl_id}, function (data) {
            if (data.error) {
                alert(data.error);
            }
            else {
              location.reload(true);
            }
      });
    }

    function delete_invalid_crawl(crawl_id) {
      $.post('/productspiders/delete_crawl', {crawl_id: crawl_id}, function (data) {
            location.reload(true);
      });
    }

    function upload_changes(spider_id, real_upload) {
      $.post('/productspiders/upload', {spider_id: spider_id, real_upload: real_upload}, function (data) {
            location.reload(true);
      });    
    }

    function show_errors(crawl_id) {
        $.getJSON('/productspiders/error_message/' + crawl_id, {}, function (data) {
           alert(data.error_message);
        });
    }

    function edit_assign(site_id) {
        $('#assign-edit-' + site_id).hide();
        $('#assign-save-' + site_id).show();
        $('#assigned-' + site_id).hide();
        $('#assign-' + site_id).show();
    }

    function save_assign(site_id) {
        var action = '/productspiders/assign_issue/' + site_id;
        var dev_id = $('#assign-' + site_id).val();
        $.post(action, {'dev_id': dev_id}).done(function(data) {
            $('#assign-' + site_id).hide();
            $('#assign-save-' + site_id).hide();
            if (data.developer) {
                $('#assigned-' + site_id).text(data['developer'].name);
            } else {
                $('#assigned-' + site_id).text('');
            }
            $('#assigned-' + site_id).show();
            if (data.developer) {
                $('#assign-edit-' + site_id).text('change');
            }
            $('#assign-edit-' + site_id).show();
        }).fail(function() {
            alert("An error has occurred");
        });
    }
  </script>
</head>
<body>
    <a href="${request.route_url('logout')}" title="Logout">Logout</a>
    <br /><br />
    <a href="${request.route_url('home')}" title="Home">Home</a>
	<h1>Spiders for ${account}</h1>
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
            <td>Method</td>
            <td>Automatic Upload</td>
			<td>Config</td>
            <td>View Logs</td>
            <td>Show errors</td>
            <td>Assigned</td>
            <td>Assign</td>
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

            <td>${spider.parse_method or ''}</td>

            <td>
                 % if spider.id and spider.automatic_upload:
                     <div style="color: green">Enabled</div>
                 % else:
                     <div style="color: red">Disabled</div>
                 % endif
            </td>

              <td><a href="${request.route_url('config_spider', account=account, spider=spider.name)}">Config</a></td>
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
              <td>
                  <select hidden id="assign-${spider.id}">
                      <option value="-1" ${'selected' if not spider.assigned_to_id else ''}>nobody</option>
                  % for dev in developers:
                      % if dev['id'] == spider.assigned_to_id:
                      <option value="${dev['id']}" selected>${dev['name']}</option>
                      % else:
                      <option value="${dev['id']}">${dev['name']}</option>
                      % endif
                  % endfor
                  </select>
                  <span id="assigned-${spider.id}">${spider.assigned_to_name or '' if spider.error and spider.error.status != 'fixed' else ''}</span>
              </td>
              <td>
                    % if spider.website_id:
                    <button id="assign-edit-${spider.id}" onclick="javascript: edit_assign(${spider.id});">${'change' if spider.error and spider.error.assigned_to_id and spider.error.status != 'fixed' else 'assign'}</button>
                    <button hidden style="display:none;" id="assign-save-${spider.id}" onclick="javascript: save_assign(${spider.id});">save</button>
                    % endif
              </td>
		  </tr>
		% endfor
        </tbody>
	</table>
</body>
</html>
