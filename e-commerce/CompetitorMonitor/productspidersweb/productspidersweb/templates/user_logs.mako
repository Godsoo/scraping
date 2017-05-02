<div class="modal-dialog">
  <div style="float:left;width:100%;" class="modal-content">
    <div class="modal-header">
      <button id="modalprdclose" type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>
      <h4 class="modal-title">User activity</h4>
    </div>
    <div id="wait" style="margin: auto;padding:5px;">
       <img src="/productspiders/static/images/ajax-loader.gif" />
    </div>
    <div style="float:left;width:95%;" class="modal-body">
      % if next_page or prev_page:
      <div style="width: 90%; padding: 0 2px 0 2px;">
          % if prev_page != 0:
          <a style="float: left;" href="javascript: view_user_log('${ref_id}', ${prev_page}, ${'true' if user_log else 'false'}, false);"> << prev </a>
          % endif
          % if next_page != 0:
          <a style="float: right;" href="javascript: view_user_log('${ref_id}', ${next_page}, ${'true' if user_log else 'false'}, false);"> next >> </a>
          % endif
      </div>
      % endif
      <div style="float:left;width:90%;" class="well">
        <div id="llogs">
            % for log in logs:
            <div style="float:left;width:100%;padding:1px;">
                % if user_log:
                <div style="float:left;width:100%;"><span style="font-size: 11px;"><b>DATE: ${log.date_time.strftime('%d/%m/%Y %H:%M')} SITE ${log.spider.name} ACTIVITY: ${log.activity}</b></span></div>
                % else:
                <div style="float:left;width:100%;"><span style="font-size: 11px;"><b>DATE: ${log.date_time.strftime('%d/%m/%Y %H:%M')} USER ${log.name} ACTIVITY: ${log.activity}</b></span></div>
                % endif
            </div>
            % endfor
        </div>
      </div>
    </div>
  </div>
</div>

<script>
    $(document).ajaxStart(function(){
      $("#llogs").html("");
      $("#wait").css("display","block");
    });
    $(document).ajaxComplete(function(){
      $("#wait").css("display","none");
    });
</script>