<%inherit file="server_dash_base.mako"/>
<%block name="header">
<style>
    #main-panel-head {
        margin-bottom: 30px;
    }
    #main-panel {
    margin-left: 100px;
    margin-right: 100px;
    height: 1650px;
    }
    .importer-panel {
      margin-left: 10px;
      margin-right: 10px;
      height: 500px;
      float: left;
      width: 98%;
    }
</style>
</%block>


<div id="main-panel" class="panel panel-default">
  <div class="panel-heading" id="main-panel-head">
      <h2 class="panel-title">Importer Stats</h2>
  </div>
  <div id="changes-pannel" class="panel panel-primary importer-panel">
    <div class="panel-heading">
      <h3 class="panel-title">Price changes importer</h3>
    </div>
    <div class="panel-body">
      <table id="spiders_table" data-search="true" data-pagination="true" data-page-size="1000" data-height="400" class="table table-hover" data-toggle="table" data-url="importer_stats.json?type=changes">
          <thead>
              <tr>
                <th data-field="account">Account</th>
                <th data-field="website">Website</th>
                <th data-field="timestamp">Upload time</th>
                <th data-field="size">Size</th>
              </tr>
          </thead>
          <tbody>
          </tbody>
      </table>
    </div>
  </div>
  <div id="additional-changes-pannel" class="panel panel-primary importer-panel">
    <div class="panel-heading">
      <h3 class="panel-title">Additional changes importer</h3>
    </div>
    <div class="panel-body">
      <table id="spiders_table" data-search="true" data-pagination="true" data-page-size="1000" data-height="400" class="table table-hover" data-toggle="table" data-url="importer_stats.json?type=additional_changes">
          <thead>
              <tr>
                <th data-field="account">Account</th>
                <th data-field="website">Website</th>
                <th data-field="timestamp">Upload time</th>
                <th data-field="size">Size</th>
              </tr>
          </thead>
          <tbody>
          </tbody>
      </table>
    </div>
  </div>
  <div id="metadata-changes-pannel" class="panel panel-primary importer-panel">
    <div class="panel-heading">
      <h3 class="panel-title">Metadata changes importer</h3>
    </div>
    <div class="panel-body">
      <table id="spiders_table" data-search="true" data-pagination="true" data-page-size="1000" data-height="400" class="table table-hover" data-toggle="table" data-url="importer_stats.json?type=metadata_changes">
          <thead>
              <tr>
                <th data-field="account">Account</th>
                <th data-field="website">Website</th>
                <th data-field="timestamp">Upload time</th>
                <th data-field="size">Size</th>
              </tr>
          </thead>
          <tbody>
          </tbody>
      </table>
    </div>
  </div>

</div>