<h2 class="sub-header">Spider default settings</h2>

<div id="admin-default"></div>

<script id="admin-default-template" type="text/template">

    <%text>

    <form id="default-form" role="form" method="POST">
    <div class="alert alert-success" role="alert" id="success-alert">The data have been updated</div>
      <div class="checkbox">
         <label>
           <input type="checkbox" id="automatic_upload" name="automatic_upload" <% if (spider_default.automatic_upload) { %> checked="checked" <% } %> />
           <strong>Automatic Upload</strong></label>
      </div>
      <div class="checkbox">
         <label>
           <input type="checkbox" id="silent_updates" name="silent_updates" <% if (spider_default.silent_updates) { %> checked="checked" <% } %> />
           <strong>Silent updates</strong></label>
      </div>
      <div class="form-group">
        <label class="control-label" for="update_percentage_error">Max percentage of number of overall changes for a valid update</label>
        <input type="text" id="update_percentage_error" name="update_percentage_error" class="form-control input-nrm" value="<%- spider_default.update_percentage_error %>" required>
      </div>
      <div class="form-group">
        <label class="control-label" for="additions_percentage_error">Max percentage of number of additions for a valid update</label>
        <input type="text" id="additions_percentage_error" name="additions_percentage_error" class="form-control input-nrm" value="<%- spider_default.additions_percentage_error %>" required>
      </div>
      <div class="form-group">
        <label class="control-label" for="deletions_percentage_error">Max percentage of number of deletions for a valid update</label>
        <input type="text" id="deletions_percentage_error" name="deletions_percentage_error" class="form-control input-nrm" value="<%- spider_default.deletions_percentage_error %>" required>
      </div>
      <div class="form-group">
        <label class="control-label" for="price_updates_percentage_error">Max percentage of number of price updates for a valid update</label>
        <input type="text" id="price_updates_percentage_error" name="price_updates_percentage_error" class="form-control input-nrm" value="<%- spider_default.price_updates_percentage_error %>" required>
      </div>
      <div class="form-group">
        <label class="control-label" for="max_price_change_percentage">Max percentage price change for a single product</label>
        <input type="text" id="max_price_change_percentage" name="max_price_change_percentage" class="form-control input-nrm" value="<%- spider_default.max_price_change_percentage %>" required>
      </div>
      <div class="form-group">
        <label class="control-label" for="additional_changes_percentage_error">Max percentage of number of changes for additional fields</label>
        <input type="text" id="additional_changes_percentage_error" name="additional_changes_percentage_error" class="form-control input-nrm" value="<%- spider_default.additional_changes_percentage_error %>" required>
      </div>
      <div class="form-group">
        <label class="control-label" for="add_changes_empty_perc">Max percentage of changes to empty value for additional fields</label>
        <input type="text" id="add_changes_empty_perc" name="add_changes_empty_perc" class="form-control input-nrm" value="<%- spider_default.add_changes_empty_perc %>" required>
      </div>
      <div class="form-group">
        <label class="control-label" for="image_url_perc">Max percentage of Image URL changes</label>
        <input type="text" id="image_url_perc" name="image_url_perc" class="form-control input-nrm" value="<%- spider_default.image_url_perc %>" required>
      </div>
      <div class="form-group">
        <label class="control-label" for="category_change_perc">Max percentage of category changes</label>
        <input type="text" id="category_change_perc" name="category_change_perc" class="form-control input-nrm" value="<%- spider_default.category_change_perc %>" required>
      </div>
      <div class="form-group">
        <label class="control-label" for="sku_change_perc">Max percentage of SKU changes</label>
        <input type="text" id="sku_change_perc" name="sku_change_perc" class="form-control input-nrm" value="<%- spider_default.sku_change_perc %>" required>
      </div>
      <div class="form-group">
        <label class="control-label" for="stock_percentage_error">Max percentage of products moved to out of stock for a valid update</label>
        <input type="text" id="stock_percentage_error" name="stock_percentage_error" class="form-control input-nrm" value="<%- spider_default.stock_percentage_error %>" required>
      </div>
      <div class="form-group">
        <input type="submit" value="Save" class="btn btn-primary" />
      </div>
    </form>

    <script>

        <% if (updated) { %>
            $('#success-alert').show();
        <% } else { %>
            $('#success-alert').hide();
        <% } %>

        $('#default-form').submit(function(event) {
            event.preventDefault();
            if ($(this).validator('validate')) {
                url = '/productspiders/admin_default_srv/';
                params = Utils.serializeForm('#default-form');
                Ajax.send_ajax('POST', url, params, function(response) {
                    if (response.status == 200) {
                        load_default(true);
                    } else {
                        alert('Sorry, an error occurred');
                    }
                }, true);
            }
        });
    </script>

    </%text>

</script>

<script>

    var default_tmp = _.template(
        $('#admin-default-template').html()
    );

    function load_default(updated) {
        $.getJSON("/productspiders/admin_default_srv/", function(data) {
            $('#admin-default').html(default_tmp({'spider_default': data, 'updated': updated}));
        });
    }

    load_default(false);

</script>