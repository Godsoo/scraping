<div class="modal-dialog">
  <div class="modal-content">
    <div class="modal-header">
      <button id="modalprdclose" type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>
      <h4 class="modal-title">Add Note</h4>
    </div>
    <div class="modal-body">
      <div class="notes-container well">
        <form method="POST" action="${request.route_url('spider_notes', spider_id=site_id)}">
          <textarea name="note" cols="50"></textarea>
          <br /><br />
          <input type="submit" value="Save" class="btn btn-primary" />
        </form>
      </div>
    </div>
  </div>
</div>