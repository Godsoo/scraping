<h2 class="sub-header">Maintenance History <button id="export-issues" type="button" class="btn btn-primary" style="float:right;">Export</button></h2>

<div class="well">

  <form id="maintenance-form">
  <div class="form-group">
    <div class="row">
      <div class="col-md-2">
        <input id="dtfrom" name="from" type="text" class="form-control" placeholder="Date From">
      </div>
      <div class="col-md-2">
        <input id="dtto" name="to" type="text" class="form-control" placeholder="Date To">
      </div>
    </div>
    <br />
    <div class="row">
      <div class="col-md-2">
        <select name="spider" class="selectpicker" multiple title='All spiders' data-live-search="true">
          % for spider in spiders:
          <option value="${spider.id}">${spider.name}</option>
          % endfor
        </select>
      </div>
      <div class="col-md-2"></div>
      <div class="col-md-2">
        <select name="issue" class="selectpicker" multiple title='All issue types' data-live-search="true">
          % for issue in issues:
          <option value="${issue[0]}">${issue[1]}</option>
          % endfor
        </select>
      </div>
      <div class="col-md-2"></div>
      <div class="col-md-2">
        <select name="developer" class="selectpicker" multiple title='All developers' data-live-search="true">
          % for dev in developers:
          <option value="${dev.id}">${dev.name}</option>
          % endfor
        </select>
      </div>
      <div class="col-md-2"></div>
    </div>
    <div class="form-actions">
      <button style="margin-top:25px;" type="submit" class="btn btn-primary">Filter</button>
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
      load_all_issues(1);
    });

  </script>

</div>

<div id="issues"></div>

<script id="issues-template" type="text/template">

  <%text>

  <strong><i><%- total %></i> issues found</strong>

  <br />

  <div class="table-responsive">
    <table class="table table-striped table-hover">
      <thead>
        <tr>
          <th>Account</th>
          <th>Spider</th>
          <th>Issue</th>
          <th>Time Added</th>
          <th>Fixed</th>
          <th>Time Fixed</th>
          <th>Developer</th>
        </tr>
      </thead>
      <tbody>
        <% _.each(issues, function(i){ %>
        <tr>
          <td><%- i.account %></td>
          <td><%- i.spider %></td>
          <td><%- i.issue %></td>
          <td><%- i.time_added %></td>
          <td><%- i.fixed %></td>
          <td><%- i.time_fixed %></td>
          <td><%- i.developer %></td>
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
        <li><a href="javascript: load_all_issues(<%- prev %>);">&laquo;</a></li>
        <% } else { %>
        <li class="disabled"><a href="#">&laquo;</a></li>
        <% } %>
        <% _.each(pages, function(p){ %>
        <li <% if (p == page) { %>class="active"<% } %> > <a href="javascript: load_all_issues(<%- p %>);"><%- p %></a></li>
        <% }); %>
        <% if (next) { %>
        <li><a href="javascript: load_all_issues(<%- next %>);">&raquo;</a></li>
        <% } else { %>
        <li class="disabled"><a href="#">&raquo;</a></li>
        <% } %>
      </ul>
    </div>
  </div>

  </%text>

</script>

<script>

    var issues_tmp = _.template(
        $('#issues-template').html()
    );

    function load_all_issues(p) {
        if ($('maintenance-form').validator('validate')) {
            url = '/productspiders/admin_maintenance_srv/';
            params = Utils.serializeForm('#maintenance-form');
            params['page'] = p;
            $.post(url, params, function(data) {
                $('#issues').html(issues_tmp(data['data']));
            }, 'json');
        }
    }

    $('#export-issues').click(function(){
        if ($('maintenance-form').validator('validate')) {
            url = '/productspiders/admin_maintenance_srv/';
            params = Utils.serializeForm('#maintenance-form');
            params['page'] = -1;
            $.post(url, params, function(data) {
                JSONToCSVConvertor(data, 'report_maintenance', true);
            }, 'json');
        }
    });

    load_all_issues(1);

</script>