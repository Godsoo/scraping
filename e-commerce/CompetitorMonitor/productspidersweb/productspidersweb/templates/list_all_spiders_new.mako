<html>
<head>
<script type="text/javascript" src="/productspiders/static/js/knockout-2.2.1.js"></script>
<script type="text/javascript" src="/productspiders/static/js/underscore-1.3.3.js"></script>
<script type="text/javascript" src="/productspiders/static/js/jquery-1.9.1.min.js"></script>
<script type="text/javascript" src="/productspiders/static/js/jquery.simplemodal.1.4.4.js"></script>

<link rel="stylesheet" type="text/css" href="/productspiders/static/css/jquery.dataTables.css"/>
<script type="text/javascript" src="/productspiders/static/js/jquery.dataTables.1.9.0.js"></script>
<script type="text/javascript" src="/productspiders/static/js/jquery.form.js"></script>

<script type="text/javascript" src="/productspiders/static/assets/knockout.Extensions/cog.js"></script>
<script type="text/javascript" src="/productspiders/static/assets/knockout.Extensions/cog.utils.js"></script>
<script type="text/javascript" src="/productspiders/static/assets/knockout.Extensions/knockout.bindings.dataTables.js"></script>

<link rel="stylesheet" type="text/css" href="/productspiders/static/css/simplemodal.css"/>

<style type="text/css">

       .close {
          float: right;
          font-size: 21px;
          font-weight: bold;
          line-height: 1;
          color: #000;
          text-shadow: 0 1px 0 #fff;
          filter: alpha(opacity=20);
          opacity: .2;
        }
        .close:hover {
          color: #000;
          text-decoration: none;
          cursor: pointer;
          filter: alpha(opacity=50);
          opacity: .5;
        }

       .modal-backdrop {
          position: fixed;
          top: 0;
          right: 0;
          bottom: 0;
          left: 0;
          z-index: 1040;
          background-color: #000000;
        }

        .modal-backdrop.fade {
          opacity: 0;
        }

        .modal-backdrop,
        .modal-backdrop.fade.in {
          opacity: 0.8;
          filter: alpha(opacity=80);
        }

        .modal {
          position: fixed;
          top: 10%;
          left: 50%;
          z-index: 1050;
          width: 560px;
          margin-left: -280px;
          background-color: #ffffff;
          border: 1px solid #999;
          border: 1px solid rgba(0, 0, 0, 0.3);
          *border: 1px solid #999;
          -webkit-border-radius: 6px;
             -moz-border-radius: 6px;
                  border-radius: 6px;
          outline: none;
          -webkit-box-shadow: 0 3px 7px rgba(0, 0, 0, 0.3);
             -moz-box-shadow: 0 3px 7px rgba(0, 0, 0, 0.3);
                  box-shadow: 0 3px 7px rgba(0, 0, 0, 0.3);
          -webkit-background-clip: padding-box;
             -moz-background-clip: padding-box;
                  background-clip: padding-box;
        }

        .modal.fade {
          top: -25%;
          -webkit-transition: opacity 0.3s linear, top 0.3s ease-out;
             -moz-transition: opacity 0.3s linear, top 0.3s ease-out;
               -o-transition: opacity 0.3s linear, top 0.3s ease-out;
                  transition: opacity 0.3s linear, top 0.3s ease-out;
        }

        .modal.fade.in {
          top: 10%;
        }

        .modal-header {
          padding: 9px 15px;
          border-bottom: 1px solid #eee;
        }

        .modal-header .close {
          margin-top: 2px;
        }

        .modal-header h3 {
          margin: 0;
          line-height: 30px;
        }

        .modal-body {
          position: relative;
          max-height: 400px;
          padding: 15px;
          overflow-y: auto;
        }

        .modal-form {
          margin-bottom: 0;
        }

        .modal-footer {
          padding: 14px 15px 15px;
          margin-bottom: 0;
          text-align: right;
          background-color: #f5f5f5;
          border-top: 1px solid #ddd;
          -webkit-border-radius: 0 0 6px 6px;
             -moz-border-radius: 0 0 6px 6px;
                  border-radius: 0 0 6px 6px;
          *zoom: 1;
          -webkit-box-shadow: inset 0 1px 0 #ffffff;
             -moz-box-shadow: inset 0 1px 0 #ffffff;
                  box-shadow: inset 0 1px 0 #ffffff;
        }

        .modal-footer:before,
        .modal-footer:after {
          display: table;
          line-height: 0;
          content: "";
        }

        .modal-footer:after {
          clear: both;
        }

        .modal-footer .btn + .btn {
          margin-bottom: 0;
          margin-left: 5px;
        }

        .modal-footer .btn-group .btn + .btn {
          margin-left: -1px;
        }

        .modal-footer .btn-block + .btn-block {
          margin-left: 0;
        }

        .well {
             min-height: 20px;
             padding: 19px;
             margin-bottom: 20px;
             background-color: #f5f5f5;
             border: 1px solid #e3e3e3;
             -webkit-border-radius: 4px;
                -moz-border-radius: 4px;
                     border-radius: 4px;
             -webkit-box-shadow: inset 0 1px 1px rgba(0, 0, 0, 0.05);
                -moz-box-shadow: inset 0 1px 1px rgba(0, 0, 0, 0.05);
                     box-shadow: inset 0 1px 1px rgba(0, 0, 0, 0.05);
           }

           .well blockquote {
               border-color: #ddd;
               border-color: rgba(0, 0, 0, 0.15);
           }

           .well-large {
              padding: 24px;
              -webkit-border-radius: 6px;
                 -moz-border-radius: 6px;
                      border-radius: 6px;
            }

            .well-small {
              padding: 9px;
              -webkit-border-radius: 3px;
                 -moz-border-radius: 3px;
                      border-radius: 3px;
            }

            .btn {
              display: inline-block;
              *display: inline;
              padding: 4px 12px;
              margin-bottom: 0;
              *margin-left: .3em;
              font-size: 14px;
              line-height: 20px;
              color: #333333;
              text-align: center;
              text-shadow: 0 1px 1px rgba(255, 255, 255, 0.75);
              vertical-align: middle;
              cursor: pointer;
              background-color: #f5f5f5;
              *background-color: #e6e6e6;
              background-image: -moz-linear-gradient(top, #ffffff, #e6e6e6);
              background-image: -webkit-gradient(linear, 0 0, 0 100%, from(#ffffff), to(#e6e6e6));
              background-image: -webkit-linear-gradient(top, #ffffff, #e6e6e6);
              background-image: -o-linear-gradient(top, #ffffff, #e6e6e6);
              background-image: linear-gradient(to bottom, #ffffff, #e6e6e6);
              background-repeat: repeat-x;
              border: 1px solid #cccccc;
              *border: 0;
              border-color: #e6e6e6 #e6e6e6 #bfbfbf;
              border-color: rgba(0, 0, 0, 0.1) rgba(0, 0, 0, 0.1) rgba(0, 0, 0, 0.25);
              border-bottom-color: #b3b3b3;
              -webkit-border-radius: 4px;
                 -moz-border-radius: 4px;
                      border-radius: 4px;
              filter: progid:DXImageTransform.Microsoft.gradient(startColorstr='#ffffffff', endColorstr='#ffe6e6e6', GradientType=0);
              filter: progid:DXImageTransform.Microsoft.gradient(enabled=false);
              *zoom: 1;
              -webkit-box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.2), 0 1px 2px rgba(0, 0, 0, 0.05);
                 -moz-box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.2), 0 1px 2px rgba(0, 0, 0, 0.05);
                      box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.2), 0 1px 2px rgba(0, 0, 0, 0.05);
            }

            .btn-primary {
              color: #ffffff;
              text-shadow: 0 -1px 0 rgba(0, 0, 0, 0.25);
              background-color: #006dcc;
              *background-color: #0044cc;
              background-image: -moz-linear-gradient(top, #0088cc, #0044cc);
              background-image: -webkit-gradient(linear, 0 0, 0 100%, from(#0088cc), to(#0044cc));
              background-image: -webkit-linear-gradient(top, #0088cc, #0044cc);
              background-image: -o-linear-gradient(top, #0088cc, #0044cc);
              background-image: linear-gradient(to bottom, #0088cc, #0044cc);
              background-repeat: repeat-x;
              border-color: #0044cc #0044cc #002a80;
              border-color: rgba(0, 0, 0, 0.1) rgba(0, 0, 0, 0.1) rgba(0, 0, 0, 0.25);
              filter: progid:DXImageTransform.Microsoft.gradient(startColorstr='#ff0088cc', endColorstr='#ff0044cc', GradientType=0);
              filter: progid:DXImageTransform.Microsoft.gradient(enabled=false);
            }

            .btn-primary:hover,
            .btn-primary:focus,
            .btn-primary:active,
            .btn-primary.active,
            .btn-primary.disabled,
            .btn-primary[disabled] {
              color: #ffffff;
              background-color: #0044cc;
              *background-color: #003bb3;
            }
</style>

<link rel="stylesheet" type="text/css" href="/productspiders/static/css/notes.css"/>

<script type="text/javascript" src="/productspiders/static/js/spiders.js?version=1.3"></script>

<script type="text/javascript">
    var spiders_url = '${json_url |n}';

    var assembla_authorized;
    % if assembla_authorized:
    assembla_authorized = true;
    % else:
    assembla_authorized = false;
    % endif
    var developers = ${developers |n};
    var assembla_ticket_submit_url = '${assembla_ticket_submit_url |n}';

    var errors;
    % if show_errors:
    errors = '${show_errors}';
    % else:
    errors = false;
    % endif

    var view_model;
    var data_table;
    var data_table_options = {"iDisplayLength":100, "bStateSave":true};
    var assembla_config = {
        'authorized': assembla_authorized,
        'ticket_submit_url': assembla_ticket_submit_url
    };

    $(document).ready(function () {
        spiders_ko.init(spiders_url, errors, assembla_config, developers, $('#spiders'));
    });
    function view_notes(site_id) {
          $.modal.defaults.closeClass = "close";
          $('#modalnts').load('/productspiders/spider_notes/' + site_id);
          $('#modalnts').modal({overlayClose: true, close: true});
      }
         $(document).ready(function () {
          $('body').on('hidden.bs.modal', '.modal', function () {
              $(this).removeData('bs.modal');
          });
      });
</script>
</head>
<body>
<div class="modal fade bs-example-modal-sm" id="modalnts" style="display: none" tabindex="-1" role="dialog" aria-hidden="true"></div>

<template id="mark_real_modal">
    <div class="modal-dialog">
      <div style="float:left;width:100%;" class="modal-content">
        <div class="modal-header">
          <h4 class="modal-title">Error Type</h4>
        </div>
        <div style="float:left;width:95%;" class="modal-body">
          <div style="float:left;width:90%;" class="notes-container well">
            <form method="post" id="mark_real_form">
                <div class="input-group">
                    <select name="error_type">
                      % for error_type in error_types:
                      <option value="${error_type[0]}">${error_type[1]}</option>
                      % endfor
                    </select>
                </div>
                <div class="input-group" id="error_desc">
                    <label for="other_desc">Desc:&nbsp;</label><input type="text" id="other_desc" name="error_desc" />
                </div>
                <input type="submit" value="Save" class="btn btn-primary" />
            </form>
          </div>
        </div>
      </div>
    </div>
</template>

<a href="${request.route_url('logout')}" title="Logout">Logout</a>
<h1 data-bind="text: title()">Spiders</h1>
<div>
    % if show_errors:
        <a href="${request.route_url('list_all_spiders')}">View all spiders</a>
        % if show_errors == 'possible':
            <a href="${request.route_url('list_all_spiders', _query={'errors': 'real'})}">View spiders with real errors</a>
        % elif show_errors == 'real':
            <a href="${request.route_url('list_all_spiders', _query={'errors': 'possible'})}">View spiders with possible errors</a>
        % endif
        % if not assembla_authorized:
            <br />
            <a href="${assembla_authorization_url}">Login to Assembla</a>
        % endif
    % else:
        <a href="${request.route_url('list_all_spiders', _query={'errors': 'real'})}">View spiders with real errors</a>
        <a href="${request.route_url('list_all_spiders', _query={'errors': 'possible'})}">View spiders with possible errors</a>
    % endif
</div>
<br />
<div>
    <button data-bind="click: getData">Refresh</button>
</div>
<table id="spiders_ko" data-bind="dataTable: {
        dataSource: spiders,
        rowTemplate: 'spider_row',
        columns: [
            % if show_errors:
            'priority_possible_errors',
            'last_crawl_run_count',
            % endif
            'crawl_date',
            'account_name',
            'name',
            % if show_errors == 'real' or not show_errors:
                'website_id',
            % endif
            'crawls_url',
            'crawl_status',
            % if show_errors == 'possible':
            'products_count',
            % endif
            'is_valid',
            'is_valid',
            % if show_errors == 'real' or not show_errors:
                'is_valid',
                'account_enabled',
            % endif
            'enabled',
            'status',
            'parse_method',
            'upload_testing_account',
            'automatic_upload',
            'config_url',
            'logs_url',
            'errors_url',
            % if show_errors:
            'status',
            % if show_errors == 'real':
            'error_type',
            'error_type',
            'assigned_to_name',
            'assigned',
            //'website_id'
            % endif
            % endif
        ],
        options: {'iDisplayLength':25, 'bStateSave':true, 'bAutoWidth': false}
    }">
    <thead>
    <tr>
        % if show_errors:
        <td>Priority</td>
        <td>Run times</td>
        % endif
        <td style="width: 93px">Date</td>
        <td style="width: 100px">Account</td>
        <td>Spider</td>
        % if show_errors == 'real' or not show_errors:
            <td>Website ID</td>
        % endif
        <td>View Crawls</td>
        <td>Crawl Status</td>
        % if show_errors == 'possible':
        <td>Products</td>
        % endif
        <td>Validation</td>
        <td>Delete Crawl</td>
        % if show_errors == 'real' or not show_errors:
            <td>Upload</td>
            <td>Run</td>
        % endif
        <td>Account</td>
        <td>Status</td>
        <td>Method</td>
        <td>Testing</td>
        <td>Automatic Upload</td>
        <td>Config</td>
        <td>View logs</td>
        <td>Show errors</td>
        % if show_errors:
        <td>Error status</td>
        % if show_errors == 'real':
        <td>Error Type</td>
        <td>Change Type</td>
        <td>Assigned</td>
        <td>Assign</td>
##        <td>Upload fix</td>
        % endif
        % endif
    </tr>
    </thead>
    <tbody>
    </tbody>
</table>
<script type="text/html" id="spider_row">
    % if show_errors:
    <td style="text-align:center; width:5%;" data-bind="text: priority_possible_errors() ? 'Yes' : '', style: {color: priority_possible_errors() ? 'green' : 'red'}"></td>
    <td style="text-align:center; width:5%; font-weight:bold;" data-bind="text: last_crawl_run_count, style: {color: last_crawl_run_count() < 3 ? 'blue' : 'red'}"></td>
    % endif
    <td data-bind="text: crawl_date"></td>
    <td data-bind="text: account_name"></td>
    <td>
        <div data-bind="text: name"></div>
        <a data-bind="attr: {href: 'javascript: view_notes(' + id() +')'}" href="" style="text-decoration: none"><img src="/productspiders/static/images/note.png" style="float: left"/>(<span data-bind="text:notes_count"></span>)</a>
        <a data-bind="click: $root.show_doc, if: doc_url()" href="#" style="text-decoration: none">(?)</a>
    </td>
    % if show_errors == 'real' or not show_errors:
        <td data-bind="text: website_id"></td>
    % endif
    <td><a data-bind="click: $root.show_spider_crawls, if: crawls_url()" href="#">View Crawls</a></td>
    <td data-bind="text: crawl_status"></td>
    % if show_errors == 'possible':
    <td><span class="products-count" data-bind="text: products_count"></span></td>
    % endif
    <td>
        <a data-bind="click: $root.set_crawl_valid, if: set_valid_url()" href="#">Set valid</a>
        <a data-bind="click: $root.reupload, if: reupload_url()" href="#">Reupload</a>
    </td>
    <td><a data-bind="click: $root.delete_invalid_crawl, if: delete_crawl_url()" href="#">Delete invalid crawl</a>
    </td>
    % if show_errors == 'real' or not show_errors:
        <td><a data-bind="click: $root.upload_changes, if: upload_url()" href="#">Upload changes</a></td>
        <td><a data-bind="click: $root.run_spider, if: $root.runnable($data)" href="#">Run</a></td>
    % endif
    <td data-bind="text: account_status, style: {color: account_enabled() ? 'green' : 'red'}"></td>
    <td data-bind="text: status, style: {color: enabled() ? 'green' : 'red'}"></td>
    <td data-bind="text: parse_method"></td>
    <td data-bind="text: upload_testing_account() ? 'Yes' : 'No', style: {color: upload_testing_account() ? 'green' : 'red'}"></td>
    <td data-bind="text: automatic_upload_text, style: {color: automatic_upload() ? 'green' : 'red'}"></td>
    <td><a data-bind="click: $root.show_spider_config, if: config_url()" href="#">Config</a></td>
    <td><a data-bind="click: $root.show_spider_logs, if: logs_url()" href="#">View logs</a>
        <a data-bind="click: $root.show_latest_logs, if: logs_url()" href="#">(Latest)</a></td>
    <td><a data-bind="click: $root.show_spider_errors, if: errors_url()" href="#">Show errors</a></td>
    % if show_errors:
    <td><a data-bind="click: $root.change_error_status, text: $root.change_error_status_text()" href="#"></a></td>
    % if show_errors == 'real':
    <td data-bind="text: error_type, attr:{id: 'error_type_' + id()}"></td>
    <td>
        <button data-bind="click: $root.edit_error_type">Change</button>
    </td>
    <td>
        <span data-bind="visible: assigned(), text: assigned_to_name()"></span>
    </td>
    <td>
        <button data-bind="click: $root.edit_assigned_to, text: assigned() ? 'Change' : 'Assign'">Assign</button>
    </td>
##    <td>
##        <button data-bind="click: $root.upload_fix">Upload</button>
##    </td>
    % endif
    % endif
</script>
</body>
</html>
