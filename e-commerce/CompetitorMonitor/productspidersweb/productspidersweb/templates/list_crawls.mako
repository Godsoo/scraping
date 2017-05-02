<html>
<head>

   <title>${spider.name} crawls</title>
    <script>
        function open_new_tab(url) {
          var win = window.open(url, '_blank');
          win.focus();
        }
    </script>
   <style type="text/css">
        table {
              font-size: 15px;
        }
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

   <script type="text/javascript" src="/productspiders/static/js/jquery-1.9.1.min.js"></script>

   <script type="text/javascript">
   	   function delete_crawls(spider_id, delete_last_one) {
	            if (confirm("Are you sure?")) {
	   	    $.post('/productspiders/delete_crawls', {spider_id: spider_id,
                                                     delete_last_one: delete_last_one}, function (data) {
                       location.reload();
                    });
	           }
	   }

	  function delete_crawl(crawl_id) {
	   if (confirm("Are you sure?")) {
	   $.post('/productspiders/delete_crawl', {crawl_id: crawl_id}, function (data) {
            location.reload();
	   });    
	   }
	   }

      function delete_changes(crawl_id) {
           if (confirm("Are you sure?")) {
           $.post('/productspiders/delete_changes', {crawl_id: crawl_id}, function (data) {
                  location.reload();
           });
           }
      }

       function upload_changes(crawl_id) {
           if (confirm("Are you sure?")) {
               $.post('/productspiders/upload_crawl', {crawl_id: crawl_id}, function (data) {
                           location.reload(true);
                     });
           }
       }

      function compute_changes(crawl_id) {
         if (confirm("Are you sure?")) {
             $.post('/productspiders/compute_changes', {crawl_id: crawl_id}, function (data) {
                         location.reload(true);
                   });
         }
      }

      function compute_all_changes(spider_id) {
          if (confirm("Are you sure?")) {
               $.post('/productspiders/compute_changes', {spider_id: spider_id}, function (data) {
                           location.reload(true);
                     });
           }
      }

      function set_skus_ids(crawl_id) {
          if (confirm("Are you sure?")) {
                 $.post('/productspiders/setids', {crawl_id: crawl_id}, function (data) {
                    location.reload(true);
                 });
          }
      }

      function view_notes(site_id) {
          $('#modalnts').load('/productspiders/spider_notes/' + site_id);
          $('#modalnts').modal('toggle');
      }

      function view_logs(site_id) {
          $('#modalnts').load('/productspiders/spider_user_logs/' + site_id);
          $('#modalnts').modal('toggle');
      }

      function view_user_log(ref_id, page_no, user_log, toggle_modal) {
        if (user_log) {
            $('#modalnts').load('/productspiders/user_logs/' + ref_id + '?page=' + page_no);
        } else {
            $('#modalnts').load('/productspiders/spider_user_logs/' + ref_id + '?page=' + page_no);
        }
        if (toggle_modal) {
            $('#modalnts').modal('toggle');
        }
    }

      function new_note(site_id) {
         $('#modalnts').load('/productspiders/add_note/' + site_id);
         $('#modalnts').modal('toggle');
      }

      $(document).ready(function () {
          $('body').on('hidden.bs.modal', '.modal', function () {
              $(this).removeData('bs.modal');
          });
      });

   </script>

</head>
<body>
    <div class="modal fade bs-example-modal-sm" id="modalnts" tabindex="-1" role="dialog" aria-hidden="true">
    </div>
    <a href="${request.route_url('logout')}" title="Logout">Logout</a>
    <br /><br />
    <a href="${request.route_url('home')}" title="Home">Home</a>
    <div style="width:100%;float:left;">
        <div style="float:left;">
	        <h1>Crawls for ${spider.name}</h1>
	    </div>
	    <div style="float:right;">
	        <a href="javascript: view_notes(${spider.id});" style="float:right;">View Notes</a><br />
            <a href="javascript: new_note(${spider.id});" style="float:right;">Add Note</a><br />
            <a href="javascript: view_user_log(${spider.id}, 1, null, true);" style="float:right;">View Logs</a>
        </div>
    </div>
	<table border="1">
	<tr>
		<td>Date</td>
    <td>Started</td>
    <td>Finished</td>
    <td>Time taken</td>
		<td>Status</td>
    <td>Server</td>
		<td>Products</td>
		<td>View Changes</td>
    <td>View Additions</td>
    <td>View Deletions</td>
    <td>View Updates</td>
    <td>View additional changes</td>
    <td>Reupload</td>
    <td>Compute Changes</td>
		<td>Delete</td>
	  <td>&nbsp;</td>
	  <td>&nbsp;</td>
    <td>&nbsp;</td>
  </tr>
	% for crawl in spider.crawls:
	  <tr>
		<td>${crawl.crawl_date}</td>
    <td>${str(crawl.started)}
    </td>
    <td>${str(crawl.ended)}</td>
    <td>${str(crawl.time_taken)}</td>
  	<td>${crawl.status}</td>
    <td>${crawl.worker_server}</td>
		<td><a href="/productspiders/products_paged/${crawl.id}">${crawl.products_count}</a></td>
		<td><a href="/productspiders/changes_paged/${crawl.id}">${crawl.changes_count}</a></td>
    <td><a href="/productspiders/additions_paged/${crawl.id}">${crawl.additions_count}</a></td>
    <td><a href="/productspiders/deletions_paged/${crawl.id}">${crawl.deletions_count}</a></td>
    <td><a href="/productspiders/updates_paged/${crawl.id}">${crawl.updates_count}</a></td>
    <td><a href="/productspiders/additional_changes_paged/${crawl.id}">${crawl.additional_changes_count}</a></td>
    <td>
    % if crawl.status == "upload_finished" or crawl.status == "upload_errors":
      <a href="javascript: upload_changes(${crawl.id})">Reupload</a>
    % endif
    </td>
    <td><a href="javascript: compute_changes(${crawl.id})">Compute Changes</a></td>
    
	  <td><a href="javascript: delete_crawl(${crawl.id})">Delete</a></td>
    
	  <td><a href="/productspiders/meta/${crawl.id}">Metadata</a></td>
	  <td><a href="/productspiders/meta/changes/${crawl.id}">Metadata Changes</a></td>
      <td><a href="javascript: open_new_tab('/productspiders/last_log_file?spider=${spider.name}&crawl_id=${crawl.id}')">Log</a></td>
	  </tr>
	% endfor


	</table>
	<a href="javascript: delete_crawls(${spider.id}, 1)">Delete all crawls</a><br/>
    <a href="javascript: delete_crawls(${spider.id}, 0)">Delete all crawls except last one</a><br/>
    <a href="javascript: compute_all_changes(${spider.id})">Compute changes for all crawls</a>

    <script src="/productspiders/static/js/bootstrap.min.js"></script>

</body>
</html>
