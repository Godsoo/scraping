<h2 class="sub-header">Users <button id="new-user-btn" type="button" class="btn btn-primary" style="float:right;">New</button></h2>

<div class="modal fade" id="new-user-modal" tabindex="-1" role="dialog" aria-hidden="true">
</div>

<div class="modal fade bs-example-modal-sm" id="modallgs" tabindex="-1" role="dialog" aria-hidden="true">
</div>

<div id="users"></div>

<script id="new-user-template" type="text/template">

    <%text>

    <div class="modal-dialog">
      <div class="modal-content">
        <div class="modal-header">
          <button id="modalprdclose" type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>
          <h4 class="modal-title"><strong><% if (user.id) {%>Edit <%- user.name %><%} else {%>New User<%}%></strong></h4>
        </div>
        <div class="modal-body">
          <form id="user-form" role="form" method="POST">
            <% if (user.id) { %>
            <input type="hidden" name="id" value="<%- user.id %>" />
            <% } %>
            <div class="form-group">
              <label class="control-label" for="name">Name</label>
              <input type="text" id="name" name="name" class="form-control input-nrm" value="<%- user.name %>" required>
            </div>
            <div class="form-group">
              <label class="control-label" for="username">Username</label>
              <input type="text" id="username" name="username" class="form-control input-nrm" value="<%- user.username %>" required>
            </div>
            <div class="form-group">
              <label class="control-label" for="email">Email</label>
              <input type="text" id="email" name="email" class="form-control input-nrm" value="<%- user.email %>" >
            </div>
            <% if (user.username == current_username || current_username == '__new__' || current_user.is_admin) { %>
                <div class="form-group">
                  <label class="control-label" for="password">Password</label>
                  <input type="password" id="password" name="password" class="form-control input-nrm" value="">
                </div>
            <% } %>
            <select name="groups" class="selectpicker" multiple title="Groups" data-live-search="true">
              <% _.each(groups, function(g) { %>
              <option value="<%- g %>" <% if (_.contains(user.groups, g)) { %>selected<% } %> ><%- g %></option>
              <% }); %>
            </select>
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

        $('#user-form').submit(function(event) {
            event.preventDefault();
            if ($(this).validator('validate')) {
                url = '/productspiders/admin_users_srv/';
                params = Utils.serializeForm('#user-form');
                if (params.id) {
                    url += params.id + '/';
                    params['_method'] = 'PUT';
                }
                Ajax.send_ajax('POST', url, params, function(response) {
                    if (response.status == 200) {
                        $('#new-user-modal').modal('toggle');
                        load_all_users();
                    } else {
                        alert('Sorry, an error occurred');
                    }
                }, true);
            }
        });
    </script>

    </%text>

</script>

<script id="users-template" type="text/template">

  <%text>

  <strong><i><%- users.length %></i> users found</strong>

  <br />

  <div class="table-responsive">
    <table class="table table-striped table-hover">
      <thead>
        <tr>
          <th>#</th>
          <th>Name</th>
          <th>Username</th>
          <th>Email</th>
          <th>Edit</th>
          <th>Delete</th>
        </tr>
      </thead>
      <tbody>
        <% _.each(users, function(s){ %>
        <tr>
          <td><%- s.id %></td>
          <td><a href="javascript: view_user_log(<%- s.id %>, 1, true, true);"><%- s.name %></a></td>
          <td><%- s.username %></td>
          <td><%- s.email %></td>
          <td>
            <a href="javascript: user_edit(<%- s.id %>);">Edit</a>
          </td>
          <td>
            <a href="javascript: user_delete(<%- s.id %>);">Delete</a>
          </td>
        </tr>
        <% }); %>
      </tbody>
    </table>

  </div>

  </%text>

</script>

<script>

    var users_tmp = _.template(
        $('#users-template').html()
    );

    var new_user_tmp = _.template(
        $('#new-user-template').html()
    );

    function load_all_users() {
        $.getJSON("/productspiders/admin_users_srv/", function(data) {
            $('#users').html(users_tmp({'users': data['data']['users']}));
        });
    }

    function user_edit(user_id) {
        $.getJSON("/productspiders/admin_users_srv/" + user_id + '/', function(data) {
            $('#new-user-modal').html(new_user_tmp({
                'current_user': data['data']['current_user'],
                'current_username': data['data']['current_user']['username'],
                'user': data['data']['user'],
                'groups': data['data']['groups']}));
            $('#new-user-modal').modal('toggle');
        });
    }

    function view_user_log(ref_id, page_no, user_log, toggle_modal) {
        if (user_log) {
            $('#modallgs').load('/productspiders/user_logs/' + ref_id + '?page=' + page_no);
        } else {
            $('#modallgs').load('/productspiders/spider_user_logs/' + ref_id + '?page=' + page_no);
        }
        if (toggle_modal) {
            $('#modallgs').modal('toggle');
        }
    }

    function user_delete(user_id) {
        Ajax.send_ajax('POST', '/productspiders/admin_users_srv/' + user_id + '/', {'_method': 'DELETE'}, function(response) {
            if (response.status == 200) {
                load_all_users();
            } else {
                alert('Sorry, an error occurred');
            }
        }, true);
    }

    $('#new-user-btn').click(function(){
        $.getJSON('/productspiders/admin_users_srv/', function(data) {
            var groups = data['data']['groups'];
            $('#new-user-modal').html(new_user_tmp({
                'user': {'groups': groups},
                'groups': groups,
                'current_user': data['data']['current_user'],
                'current_username': '__new__'}));
            $('#new-user-modal').modal('toggle');
        });
    });

    load_all_users();

</script>