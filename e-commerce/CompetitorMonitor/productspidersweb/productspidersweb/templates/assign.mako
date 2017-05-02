<div class="modal-dialog modal-sm">
  <div class="modal-content">
    <div class="modal-header">
      <button id="modalprdclose" type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>
      <h4 class="modal-title">Assign to developer</h4>
    </div>
    <div class="modal-body">
      <form id="assign-form" method="POST" action="${request.route_url('assign_issue', spider_id=site_id)}">
        <div class="form-group">
          <label class="control-label" for="dev_id">Developer</label>
          <select id="dev_id" name="dev_id">
            % for dev in developers:
                % if developer and dev['id'] == developer.id:
                <option value="${dev['id']}" selected>${dev['name']}</option>
                % else:
                <option value="${dev['id']}">${dev['name']}</option>
                % endif
            % endfor
          </select>
        </div>
        <input type="submit" value="Save" class="btn btn-primary" />
      </form>
    </div>
  </div>

  <script>
    $('#assign-form').submit(function(evt){
        evt.preventDefault();
        var action = $('#assign-form').attr('action');
        var dev_id = $('#assign-form option:selected').val();
        $.post(action, {'dev_id': dev_id}).done(function(data) {
            location.reload();
        });
    });
  </script>
</div>