<%inherit file="base.html"/>

<%block name="content">
    <script>
        function check_form() {
            if (!$('#user_id').val() || !$('#account_id').val() || !('$spider_file').val()) {
                alert('There are missing required fields');
                return false;
            }
            return true;
        }

        function set_as_deployed(spider_upload_id) {

        }
    </script>
    <div class="container">
    <div class="row">
        <div class="col-md-12">
            <form method="post" accept-charset="utf-8" enctype="multipart/form-data" onsubmit="return check_form()">
              <fieldset>
                  <legend>Upload New Spider</legend>
                    <select id="account_id" name="account_id" class="form-control" style="width: 300px;">
                        <option value="">Account</option>
                        <option value="new_account">Account not created yet</option>
                        % for a in accounts:
                            <option value="${a.id}">${a.name}</option>
                        % endfor
                    </select>
                    <br/>
                    <select id="user_id" name="user_id" class="form-control" style="width: 300px;">
                        <option value="">Assign To</option>
                        % for u in users:
                            <option value="${u.id}">${u.name}</option>
                        % endfor
                    </select>
                    <br/>
                    <input name="spider_file" id="spider_file" type="file" class="file">
                    <br/>
                    <p>Notes:</p>
                    <textarea name="notes" rows="5" cols="60"></textarea>
                    <br/>
                    <button id="fixer-log-btn" class="btn btn-default" type="submit">Upload Spider</button>

             </fieldset>
            </form>
       </div>
    </div>
    </div>
    <div class="container">

    </div>
 <div class="container" style="margin-top: 10px">
    <div class="row">
        <div class="col-md-12">
          <fieldset>
              <legend>Uploaded spiders</legend>
                <div style="float:left;margin:2px;">

                </div>
              <table id="tbl" data-toggle="table">
                  <thead>
                      <tr>
                          <th>Account</th>
                          <th>Spider</th>
                          <th>Assigned to</th>
                          <th>Upload time</th>
                          <th>Deployment time</th>
                          <th>Status</th>
                          <th>&nbsp;</th>
                          <th>&nbsp;</th>
                      </tr>
                  </thead>
                  % for spider in spiders:
                      <tr>
                          <td>${spider.account.name if spider.account else 'New Account'}</td>
                          <td>${spider.spider_name}</td>
                          <td>${spider.user.name}</td>
                          <td>${str(spider.upload_time).split('.')[0]}</td>
                          <td>${str(spider.deployed_time or '').split('.')[0]}</td>
                          <td>${spider.status}</td>
                          <td>
                              % if spider.status == 'waiting' and user and user.id == spider.user.id:
                               <button id="" class="btn btn-default" onclick="if (confirm('Are you sure to set the spider as deployed?'))
                                       {window.location.href = '/productspiders/spider_upload_deployed?id=${spider.id}'}">Set as deployed</button>
                              % endif
                          </td>
                          <td>
                               <button id="" class="btn btn-default" onclick="window.open('/productspiders/download_spider_upload?id=${spider.id}', '_blank');">Download</button>
                          </td>
                      </tr>
                  % endfor
              </table>
         </fieldset>
       </div>
    </div>
    </div>

</%block>
