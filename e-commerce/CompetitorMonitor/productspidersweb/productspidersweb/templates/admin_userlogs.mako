<h2 class="sub-header">Activity Logs Report <button id="export-logs" type="button" class="btn btn-primary" style="float:right;">Export</button></h2>

<div class="well">

  <form id="maintenance-form">
  <div class="form-group">
    <div class="row">
      <div class="col-md-2">
        <input id="dtfrom" name="from_date" type="text" class="form-control" placeholder="Date From">
      </div>
      <div class="col-md-2">
        <input id="dtto" name="to_date" type="text" class="form-control" placeholder="Date To">
      </div>
      <div class="col-md-3">
        <select name="users" class="selectpicker" multiple title='All users' data-live-search="true">
          % for user in users:
          <option value="${user.username}">${user.name}</option>
          % endfor
        </select>
      </div>
      <div class="col-md-3">
        <select name="spiders" class="selectpicker" multiple title='All sites' data-live-search="true">
          % for spider in spiders:
          <option value="${spider.id}">${spider.name}</option>
          % endfor
        </select>
      </div>
      <div class="col-md-2">
          <button type="submit" class="btn btn-primary">Filter</button>
      </div>
    </div>
    </form>
  </div>

  <script>
    $('#dtfrom').datepicker({
      format: "dd/mm/yyyy",
    })

    $('#dtto').datepicker({
      format: "dd/mm/yyyy",
    })

    $('.selectpicker').selectpicker();
    $('.dropdown-toggle').dropdown(); // workaround for not visible dropdown menu after click

    $('#maintenance-form').submit(function(event) {
      event.preventDefault();
      load_all(1);
    });

  </script>

</div>

<div id="logs"></div>

<script id="logs-template" type="text/template">

  <%text>

  <strong><i><%- total %></i> logs found</strong>

  <br />

  <div class="table-responsive">
    <table class="table table-striped table-hover">
      <thead>
        <tr>
          <th>Date/Time</th>
	  <th>Account</th>
          <th>Site</th>
          <th>Priority</th>
          <th>User</th>
          <th>Activity</th>
        </tr>
      </thead>
      <tbody>
        <% _.each(user_logs, function(l){ %>
        <tr>
          <td><%- l.date_time %></td>
          <td><%- l.account_name %></td>
          <td><%- l.website_name %></td>
          <td><%- l.priority %></td>
          <td><%- l.user_name %></td>
          <td><%- l.activity %></td>
        </tr>
        <% }); %>
      </tbody>
    </table>

  </div>

  <div class="row">
    <div class="col-md-2"></div>
    <div class="col-md-10">
      <ul class="pagination">
        <% if (prev) { %>
        <li><a href="javascript: load_all(<%- prev %>);">&laquo;</a></li>
        <% } else { %>
        <li class="disabled"><a href="#">&laquo;</a></li>
        <% } %>
        <% _.each(pages, function(p){ %>
        <li <% if (p == page) { %>class="active"<% } %> > <a href="javascript: load_all(<%- p %>);"><%- p %></a></li>
        <% }); %>
        <% if (next) { %>
        <li><a href="javascript: load_all(<%- next %>);">&raquo;</a></li>
        <% } else { %>
        <li class="disabled"><a href="#">&raquo;</a></li>
        <% } %>
      </ul>
    </div>
  </div>

  </%text>

</script>

<script>

    var logs_tmp = _.template(
        $('#logs-template').html()
    );

    function load_all(p) {
        if ($('maintenance-form').validator('validate')) {
            url = '/productspiders/spiders_user_log_report_data.json';
            params = Utils.serializeForm('#maintenance-form');
            params['page'] = p;
            $.post(url, params, function(data) {
                $('#logs').html(logs_tmp(data['data']));
            }, 'json');
        }
    }

    $('#export-logs').click(function(){
        if ($('maintenance-form').validator('validate')) {
            url = '/productspiders/spiders_user_log_report_data.json';
            params = Utils.serializeForm('#maintenance-form');
            params['page'] = -1;
            $.post(url, params, function(data) {
                JSONToCSVConvertor(data, 'report_maintenance', true);
            }, 'json');
        }
    });

    load_all(1);

</script>