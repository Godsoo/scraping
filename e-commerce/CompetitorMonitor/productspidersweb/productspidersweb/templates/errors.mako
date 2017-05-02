<html>
<head>
    <link href="/productspiders/static/bootstrap/css/bootstrap.min.css" rel="stylesheet">
    <script src="/productspiders/static/js/jquery.js"></script>
</head>
<body>
  <div><h1 style="display:inline;">Errors for ${spider_name}</h1>
    <strong style="float:right;margin:20px;color:red;font-size:18px;">${crawl_method}</strong>
      % if doc_url:
          <a href="${doc_url}" title="spider_doc" style="float:right; margin: 20px; font-size: 18px;">Spider doc</a>
      % endif
  </div>
  <hr />
  <div role="tabpanel">

      <ul class="nav nav-tabs" role="tablist">
        <li role="presentation" class="active"><a href="#all" aria-controls="home" role="tab" data-toggle="tab">All</a></li>
        % for error_group in error_groups:
            % if error_group['errors']:
            <li role="presentation"><a href="#${error_group['name'].replace(' ', '-').lower()}" aria-controls="profile" role="tab" data-toggle="tab">${error_group['name']}</a></li>
            % endif
        % endfor
        % if uncategorized_errors:
            <li role="presentation"><a href="#uncategorized" aria-controls="profile" role="tab" data-toggle="tab">Uncategorized</a></li>
        % endif
      </ul>

      <!-- Tab panes -->
      <div class="tab-content">
        <div role="tabpanel" class="tab-pane active" id="all">
            % for error in all_errors:
                % if error['severity_level'] == 1:
                <div class="alert alert-danger" role="alert">${error['message'] | n}</div>
                % elif error['severity_level'] == 2:
                <div class="alert alert-warning" role="alert">${error['message'] | n}</div>
                % else:
                <div class="alert alert-info" role="alert">${error['message'] | n}</div>
                % endif
            % endfor
        </div>
        % for error_group in error_groups:
        % if error_group['errors']:
        <div role="tabpanel" class="tab-pane" id="${error_group['name'].replace(' ', '-').lower()}">
            % for error in error_group['errors']:
                % if error['severity_level'] == 1:
                <div class="alert alert-danger" role="alert">${error['message'] | n}</div>
                % elif error['severity_level'] == 2:
                <div class="alert alert-warning" role="alert">${error['message'] | n}</div>
                % else:
                <div class="alert alert-info" role="alert">${error['message'] | n}</div>
                % endif
            % endfor
        </div>
        % endif
        % endfor
        <div role="tabpanel" class="tab-pane" id="uncategorized">
            % for error in uncategorized_errors:
                <div class="alert alert-info" role="alert">${error['message'] | n}</div>
            % endfor
        </div>
      </div>

    </div>

    <script src="/productspiders/static/bootstrap/js/bootstrap.min.js"></script>

</body>
</html>
