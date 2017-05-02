<h2 class="sub-header">Developers <button id="new-dev-btn" type="button" class="btn btn-primary" style="float:right;">New</button></h2>

<div class="modal fade" id="new-dev-modal" tabindex="-1" role="dialog" aria-hidden="true">
</div>

<div class="modal fade bs-example-modal-sm" id="modallgs" tabindex="-1" role="dialog" aria-hidden="true">
</div>

<div id="devs"></div>

<script id="new-dev-template" type="text/template">

    <%text>

    <div class="modal-dialog">
      <div class="modal-content">
        <div class="modal-header">
          <button id="modalprdclose" type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>
          <h4 class="modal-title"><strong><% if (dev.id) {%>Edit <%- dev.name %><%} else {%>New Developer<%}%></strong></h4>
        </div>
        <div class="modal-body">
          <form id="dev-form" role="form" method="POST">
            <% if (dev.id) { %>
            <input type="hidden" name="id" value="<%- dev.id %>" />
            <% } %>
            <div class="form-group">
              <label class="control-label" for="name">Name</label>
              <input type="text" id="name" name="name" class="form-control input-nrm" value="<%- dev.name %>" required>
            </div>
            <div class="form-group">
              <label class="control-label" for="assembla_id">Assembla user</label>
              <select id="assembla_id" name="assembla_id">
                <% _.each(assembla_users, function(p) { %>
                <option value="<%- p.id %>" <% if (dev.assembla_id == p.id) { %>selected<% } %> ><%- p.name %></option>
                <% }); %>
              </select>
            </div>
            <div class="checkbox">
              <label>
                <input type="checkbox" id="active" name="active" <% if (dev.active) { %> checked="checked" <% } %> />
              <strong>Active</strong></label>
            </div>
            <br />
            <br />
            <div class="form-group">
              <input type="submit" value="Save" class="btn btn-primary" />
            </div>
          </form>
        </div>
      </div>
    </div>

    <script>
        $('.selectpicker').selectpicker();
        $('.dropdown-toggle').dropdown(); // workaround for not visible dropdown menu after click

        $('#dev-form').submit(function(event) {
            event.preventDefault();
            if ($(this).validator('validate')) {
                url = '/productspiders/admin_devs_srv/';
                params = Utils.serializeForm('#dev-form');
                if (params.id) {
                    url += params.id + '/';
                    params['_method'] = 'PUT';
                }
                Ajax.send_ajax('POST', url, params, function(response) {
                    if (response.status == 200) {
                        $('#new-dev-modal').modal('toggle');
                        load_all_devs();
                    } else {
                        alert('Sorry, an error occurred');
                    }
                }, true);
            }
        });
    </script>

    </%text>

</script>

<script id="devs-template" type="text/template">

  <%text>

  <strong><i><%- devs.length %></i> devs found</strong>

  <br />

  <div class="table-responsive">
    <table class="table table-striped table-hover">
      <thead>
        <tr>
          <th>#</th>
          <th>Name</th>
          <th>Active</th>
          <th>Edit</th>
          <th>Delete</th>
        </tr>
      </thead>
      <tbody>
        <% _.each(devs, function(s){ %>
        <tr>
          <td><%- s.id %></td>
          <td><%- s.name %></td>
          <td><%- s.active %></td>
          <td>
            <a href="javascript: dev_edit(<%- s.id %>);">Edit</a>
          </td>
          <td>
            <a href="javascript: dev_delete(<%- s.id %>);">Delete</a>
          </td>
        </tr>
        <% }); %>
      </tbody>
    </table>

  </div>

  </%text>

</script>

<script>

    var devs_tmp = _.template(
        $('#devs-template').html()
    );

    var new_dev_tmp = _.template(
        $('#new-dev-template').html()
    );

    function load_all_devs() {
        $.getJSON("/productspiders/admin_devs_srv/", function(data) {
            $('#devs').html(devs_tmp({'devs': data['data']['devs']}));
        });
    }

    function dev_edit(dev_id) {
        $.getJSON("/productspiders/admin_devs_srv/" + dev_id + '/', function(data) {
            $('#new-dev-modal').html(new_dev_tmp({
                'dev': data['data']['dev'],
                'assembla_users': data['data']['assembla_users']}));
            $('#new-dev-modal').modal('toggle');
        });
    }

    function view_dev_log(ref_id, page_no, dev_log, toggle_modal) {
        if (dev_log) {
            $('#modallgs').load('/productspiders/dev_logs/' + ref_id + '?page=' + page_no);
        } else {
            $('#modallgs').load('/productspiders/spider_dev_logs/' + ref_id + '?page=' + page_no);
        }
        if (toggle_modal) {
            $('#modallgs').modal('toggle');
        }
    }

    function dev_delete(dev_id) {
        Ajax.send_ajax('POST', '/productspiders/admin_devs_srv/' + dev_id + '/', {'_method': 'DELETE'}, function(response) {
            if (response.status == 200) {
                load_all_devs();
            } else {
                alert('Sorry, an error occurred');
            }
        }, true);
    }

    $('#new-dev-btn').click(function(){
        $.getJSON('/productspiders/assembla_users/', function(data) {
            var assembla_users = data['assembla_users'];
            $('#new-dev-modal').html(new_dev_tmp({
                'dev': {},
                'assembla_users': assembla_users}));
            $('#new-dev-modal').modal('toggle');
        });
    });

    load_all_devs();

</script>