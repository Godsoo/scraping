<div class="modal-dialog">
  <div style="float:left;width:100%;" class="modal-content">
    <div class="modal-header">
      <button id="modalprdclose" type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>
      <h4 class="modal-title">Notes</h4>
    </div>
    <div style="float:left;width:95%;" class="modal-body">
      <div style="float:left;width:90%;" class="notes-container well">
        % for note in notes:
        <div style="float:left;width:100%;padding:5px;"><div style="float:left;width:80%;"><span style="font-size: 12px;"><span id="note_${note.id}"><i>${note.time_added.strftime('%d/%m/%Y %H:%M')}</i> | <strong id="note_text_${note.id}">${note.text}</strong></span></div><div style="float:right;"><a id="note_save_${note.id}" href="javascript: edit_note(${note.id}, this);">edit</a>&nbsp;&nbsp;<a href="javascript: delete_note(${note.id});">delete</a></div></div>
        % endfor
      </div>
    </div>
      <div class="modal-header">
      <h4 class="modal-title">Add Note</h4>
    </div>
    <div class="modal-body">
      <div class="notes-container well">
        <form>
          <textarea id="note" name="note" cols="50"></textarea>
          <br /><br />
          <input value="Save" class="btn btn-primary" onclick="javascript: add_note()"/>
        </form>
      </div>
    </div>
  </div>
</div>

<script>
    function edit_note(note_id) {
        note_text = $('#note_text_' + note_id).text();
        $('#note_' + note_id).html('<textarea style="width:80%;" name="note">' + note_text + '</textarea>');
        $('#note_save_' + note_id).attr('href', 'javascript: save_note(' + note_id + ');');
        $('#note_save_' + note_id).text('save');
    }

    function save_note(note_id) {
        $.post('${request.route_url('spider_notes', spider_id=site_id)}',
            {'id': note_id,
             'note': $('textarea[name="note"]').val(),
             '_method': 'PUT'})
            .done(function(data){
                $('#modalnts').html(data);
            });
    }

    function delete_note(note_id) {
        $.post('${request.route_url('spider_notes', spider_id=site_id)}',
            {'id': note_id,
             'note': '',
             '_method': 'DELETE'})
            .done(function(data){
                $('#modalnts').html(data);
            });
    }
    function add_note() {
        var note = $('#note').val();
        $.post('${request.route_url('spider_notes', spider_id=site_id)}', {note: note, 'Submit': 'save'},
                function (data) {$('#modalnts').html(data);})
    }
</script>