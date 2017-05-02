<%inherit file="server_dash_base.mako"/>
<%block name="header">
<style>
    #main-panel-head {
        margin-bottom: 30px;
    }
    #main-panel {
    margin-left: 100px;
    margin-right: 100px;
    height: 600px;
    }
    .importer-panel {
      margin-left: 10px;
      margin-right: 10px;
      height: 500px;
      float: left;
      width: 98%;
    }
</style>
    <script>
        function remove_crawls() {
            var checked = $('#spiders_table tbody input:checked');
            var spiders = [];
            $.each(checked, function (i, e) {
                var s = $('td', $(e).parent().parent())[3].innerHTML;
                spiders.push(s);
            });
            if (spiders.length == 0) {
                alert('No spiders selected');
            } else if (confirm('Are you sure to delete the scheduled crawls for the selected spiders?')) {
                $.post('/productspiders/restart_scheduled.json', {spiders: JSON.stringify(spiders)},
                function () {location.reload();});
            }
        }

        function focus_iframe() {
            document.getElementById("iframe_modal").focus();
        }
        function show_modal_iframe(src, view_model, config) {
            if (config === undefined) {
                config = false;
            }
            var template = '' +
                '<div id="iframe_container">' +
                '   <button id="iframe_refresh">Refresh</button><br />' +
                '   <iframe id="iframe_modal" src="' + src + '" height="500" width="900" style="border:0">' +
                '</div>';
            $.modal(
                template,
                {
                    //closeHTML:"",
                    containerCss: {
                        backgroundColor: "#fff",
                        height: 550,
                        padding: 0,
                        width: 920
                    },
                    overlayClose: true,
                    onClose: function (dialog) {
            //            view_model.getData();
                        $.modal.close();
                    }
                }
            );
            $("#iframe_modal").load(function (event) {
                var self = this,
                    $form;

                setTimeout(focus_iframe, 150);

                if (config) {
                    $form = $(this).contents().find("form");
                    $($form).submit(function (event) {
                        $(self).load(function () {
                            $.modal.close();
                            view_model.getData();
                        });
                    });
                }
            });
            $("#iframe_refresh").click(function(e) {
                $("#iframe_modal").get(0).contentWindow.location.reload(true);
                e.preventDefault();
            });
        }

        function open_log_url(url) {
            show_modal_iframe(url);
        }

        function log_format(url) {
            return '<a href="javascript: open_log_url(\'' + url + '\')" class="glyphicon glyphicon-info-sign"></a>';
        }
    </script>
</%block>


<div id="main-panel" class="panel panel-default">
  <div class="panel-heading" id="main-panel-head">
      <h2 class="panel-title">Spiders Issues</h2>
  </div>
  <div id="scheduled-pannel" class="panel panel-primary importer-panel">
    <div class="panel-heading">
      <h3 class="panel-title">Spiders with scheduling issues</h3>
    </div>
    <div class="panel-body">
        <button id="remove" class="btn btn-danger" onclick="remove_crawls()">
            <i class="glyphicon glyphicon-remove"></i> Remove Crawl
        </button>
      <table id="spiders_table" data-search="true" data-pagination="true" data-page-size="1000" data-height="400" class="table table-hover" data-toggle="table" data-url="scheduled_issues.json">
          <thead>
              <tr>
                <th data-checkbox="true"></th>
                <th data-field="server">Server</th>
                <th data-field="account">Account</th>
                <th data-field="spider">Spider</th>
                <th data-field="url" data-formatter="log_format">Log</th>
              </tr>
          </thead>
          <tbody>
          </tbody>
      </table>
    </div>
  </div>


</div>
