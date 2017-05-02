<%inherit file="base.html"/>

<%block name="content">

    <div class="modal fade" id="dialog" tabindex="-1" role="dialog" aria-hidden="true">
    </div>

    <div class="container-fluid">
      <div class="row">
        <div class="col-sm-3 col-md-2 sidebar">
          <ul id="dsh-sidebar" class="nav nav-sidebar">
            <li><a href="javascript: load_section('${request.route_url('admin_default')}');">Default settings</a></li>
            <li><a href="javascript: load_section('${request.route_url('admin_users')}');">Users and Groups</a></li>
            <li><a href="javascript: load_devs();">Developers</a></li>
            <li><a href="javascript: load_section('${request.route_url('admin_maintenance')}');">Maintenance</a></li>
	    <li><a href="javascript: load_section('${request.route_url('admin_userlogs')}');">Activity Logs</a></li>
          </ul>
        </div>
        <div class="col-sm-9 col-sm-offset-3 col-md-10 col-md-offset-2 main">

             <div id="dsh-section">
               <h2 class="sub-header">Admin section</h2>
             </div>

        </div>
      </div>
    </div>

    <script type="text/javascript" src="/productspiders/static/js/jquery-1.9.1.min.js"></script>
    <script src="/productspiders/static/js/bootstrap.min.js"></script>
    <script type="text/javascript">

        function load_section(url) {
            $('#dsh-section').load(url);
        }

        function load_devs() {
            $.getJSON("/productspiders/assembla_authorized", function(data) {
                if (data['authorized']) {
                    load_section('${request.route_url('admin_devs')}');
                } else {
                    $('#dsh-section').html('<p>You need to login in assembla to use this section: <a href="${request.route_url('assembla_authorization')}">Click here to login</a>');
                }
            });
        }

        $(window).load(function() {
            $('#dsh-sidebar').find('li').click(function () {
                $('#dsh-sidebar').find('li').removeClass('active');
                $(this).addClass('active');
            });
        });

    </script>

</%block>