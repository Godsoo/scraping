<html>
<head>
    <script type="text/javascript" src="/productspiders/static/js/jquery-1.9.1.min.js"></script>

    <script type="text/javascript" src="/productspiders/static/js/jqcron/jqCron.js"></script>
    <script type="text/javascript" src="/productspiders/static/js/jqcron/jqCron.en.js"></script>
    <link type="text/css" href="/productspiders/static/js/jqcron/jqCron.css" rel="stylesheet" />
</head>
<body>
    <a href="${request.route_url('logout')}" title="Logout">Logout</a>
    <br /><br />
    <a href="${request.route_url('home')}" title="Home">Home</a>
	<h1>Configuration for ${spider.name}</h1>
	${renderer.begin(request.route_url('config_spider', account=account, spider=spider.name))}
	${renderer.csrf_token()}
	<div class="field">
    	 <label for="website_id" >Website ID</label><br/>
    	     ${renderer.text("website_id", size=6)}<br/>
    	     ${renderer.errorlist("website_id")}<br />
	 <label for="spider_cron_in" >Run crawl: </label>
	 <input type="hidden" name="crawl_cron" id="spider_cron_in" />
         <div id="spider_cron" style="white-space: normal"></div>
         <script type="text/javascript">
             var field_name = "spider_cron";
             var spider_cron_value = "${spider.crawl_cron if spider.crawl_cron else ''}";
	     $(function(){
	         $('#spider_cron').jqCron({
	             enabled_minute: false,
                     enabled_hour: false,
                     multiple_dom: true,
                     multiple_month: true,
                     multiple_dow: true,
                     multiple_time_hours: true,
                     multiple_mins: false,
                     multiple_time_minutes: false,
	             numeric_zero_pad: true,
	             default_period: 'day',
	             default_value: spider_cron_value,
                     bind_to: $('#spider_cron_in'),
                     bind_method: {
                         set: function($element, cron_val) {
                             $element.val(cron_val);
                         }
                     }
	         });
             });
         </script>
	 <br />
	 <label for="start_hour" >Crawl hour(0-23)</label><br/>
    	     ${renderer.text("start_hour", size=2)}<br/>
    	     ${renderer.errorlist("start_hour")}
         <label for="start_minute" >Crawl minute(0-59)</label><br/>
    	     ${renderer.text("start_minute", size=2)}<br/>
    	     ${renderer.errorlist("start_minute")}
	 <label for="upload_hour">Upload hour(0-23)</label><br/>
	     ${renderer.text("upload_hour", size=2)}<br/>
    	     ${renderer.errorlist("upload_hour")}
	 <br />
        <label for="timezone">Timezone</label>
        <select name="timezone">
            % for t in timezones:
                <option value="${t}" ${'selected' if spider.timezone == t else ''}>${t}</option>
            % endfor
        </select>
        <br/><br/>
         <label for="priority">Scheduler priority</label>
             ${renderer.text("priority", size=4)}<br />
             ${renderer.errorlist("priority")}<br />
         </label>
	     <label for="automatic_upload">Upload results automatically</label>
	     ${renderer.checkbox("automatic_upload")}<br/><br/>
	     ${renderer.errorlist("automatic_upload")}
        <label for="upload_testing_account">Upload results to testing account</label>
        ${renderer.checkbox("upload_testing_account")}<br/><br/>
        ${renderer.errorlist("upload_testing_account")}

        <label for="disable_cookies">Disable Cookies</label>
        ${renderer.checkbox("disable_cookies")}<br/><br/>
        ${renderer.errorlist("disable_cookies")}


	<fieldset style="width:50%;padding:5px;">
        <legend>Proxy Service</legend>
            <div>
                <label for="use_proxies">Enable Proxy Service</label>
                <input name="proxy_service_enabled" type="checkbox" value="1" ${'checked' if spider.proxy_service_enabled else ''} onchange="javascript: if ($(this).is(':checked')) {$('#proxy-service-config').show();} else {$('#proxy-service-config').hide();}" />
                ${renderer.errorlist("proxy_service_enabled")}
            </div>
            <div id="proxy-service-config" style="${'display:none;' if not spider.proxy_service_enabled else 'display:block;'}">
                <div style="padding:5px;">
                  <label for="proxy_service_target">Proxy Service Target</label>
		  <input name="proxy_service_target" type="text" value="${spider.proxy_service_target if spider.proxy_service_target else ''}" />
                   ${renderer.errorlist("proxy_service_target")}
                </div>
                <div style="padding:5px;">
                    <label for="proxy_service_profile">Proxy Service Profile</label>&nbsp;
                    <select id="proxy_service_profile" name="proxy_service_profile">
                        <option value=""></option>
                        % for proxy_service_profile in proxy_service['profiles']:
                        <option value="${proxy_service_profile['id']}" ${'selected' if spider.proxy_service_profile == proxy_service_profile['id'] else ''}>${proxy_service_profile['name']}</option>
                        % endfor
                    </select>
                    ${renderer.errorlist("proxy_service_profile")}
                </div>
                <div style="padding:5px;">
                    <label for="proxy_service_algorithm">Proxy Service next proxy select method</label>&nbsp;
                    <select id="proxy_service_algorithm" name="proxy_service_algorithm">
                        % for proxy_service_algorithm in proxy_service['algorithms']:
                        <option value="${proxy_service_algorithm[0]}" ${'selected' if spider.proxy_service_algorithm == proxy_service_algorithm[0] else ''}>${proxy_service_algorithm[1]}</option>
                        % endfor
                    </select>
                    ${renderer.errorlist("proxy_service_algorithm")}
                </div>
                <div style="padding:5px;">
                    <div>
                        <label for="proxy_service_types">Proxy Service Types</label>&nbsp;
                    </div>
                    <div>
                        <select id="proxy_service_types" multiple name="proxy_service_types">
                            % for proxy_service_type in proxy_service['types']:
                            <option value="${proxy_service_type['proxy_type']}" ${'selected' if spider.proxy_service_types and proxy_service_type['proxy_type'] in spider.proxy_service_types.split('|') else ''}>${proxy_service_type['proxy_type']}</option>
                            % endfor
                        </select>
                    </div>
                    ${renderer.errorlist("proxy_service_types")}
                </div>
                <div style="padding:5px;">
                    <div>
                        <label for="proxy_service_locations">Proxy Service Locations</label>&nbsp;
                    </div>
                    <div>
                        <select id="proxy_service_locations" multiple name="proxy_service_locations">
                            % for proxy_service_location in proxy_service['locations']:
                            <option value="${proxy_service_location['location']}" ${'selected' if spider.proxy_service_locations and proxy_service_location['location'] in spider.proxy_service_locations.split('|') else ''}>${proxy_service_location['location']}</option>
                            % endfor
                        </select>
                    </div>
                    ${renderer.errorlist("proxy_service_locations")}
                </div>
                <div style="padding:5px;">
                    <label for="proxy_service_length">List length (default: 10)</label>&nbsp;
                    ${renderer.text("proxy_service_length", size=2)}<br/>
                    ${renderer.errorlist("proxy_service_length")}
                </div>
             </div>
         </fieldset>
        <br/><br/>
        <label for="use_proxies">Enable proxy list</label>
         ${renderer.checkbox("use_proxies")}<br/><br/>
         ${renderer.errorlist("use_proxies")}
        <label for="proxy_list_id">Proxy List</label>
         % if spider_uses_proxymesh:
        <input type="hidden" name="proxy_list_id" value="${spider.proxy_list_id}" />
        <select id="proxy_list_id" disabled=>
            <option>Spider uses ProxyMesh proxy: ${spider_proxymesh_proxy_name}</option>
        </select>
         % else:
        <select name="proxy_list_id" id="proxy_list_id">
            <option></option>
            % for proxy_list in proxy_lists:
                % if proxy_list.id not in proxymesh_ids:
                    <option value="${proxy_list.id}" ${'selected' if spider.proxy_list_id == proxy_list.id else ''}>${proxy_list.name}</option>
                % endif
            % endfor
        </select>
         % endif
        <br/><br/>
        <label for="use_tor">Enable Tor</label>
        ${renderer.checkbox("use_tor")}
        ${renderer.errorlist("use_tor")}
	<br/><br/>

	<label for="enable_metadata">Enable Metadata</label>
         ${renderer.checkbox("enable_metadata")}<br/>
         ${renderer.errorlist("enable_metadata")}<br/>
        <label for="reviews_mandatory">Must collect reviews</label>
         ${renderer.checkbox("reviews_mandatory")}<br/>
         ${renderer.errorlist("reviews_mandatory")}<br/>
        <label for="immutable_metadata">Immutable metadata fields</label>
         ${renderer.text("immutable_metadata")}<br/>
         ${renderer.errorlist("immutable_metadata")}<br/>
        <label for="use_cache">Enable HTTP Caching <br />(warning: works incorrectly if website relies<br /> on cookies when deciding what to show)</label>
         ${renderer.checkbox("use_cache")}<br/>
         ${renderer.errorlist("use_cache")}<br/>
        <div id="cache_config_div">
          <div id="cache_expiration_div">
            <label for="cache_expiration">HTTP Caching expiration time (in hours)</label>
            ${renderer.text("cache_expiration", size=10)}<br/>
            ${renderer.errorlist("cache_expiration")}<br/>
          </div>
          <div id="cache_storage_div">
            <label for="cache_storage">Cache storage</label>
            <select name="cache_storage" id="cache_storage">
              <option value="">Default</option>
              % for key in cache_storages:
                  % if key == spider.cache_storage:
                      <option value="${key}" selected>${cache_storages[key]['title']}</option>
                  % else:
                      <option value="${key}">${cache_storages[key]['title']}</option>
                  % endif
              % endfor
            </select>
          </div>
        </div>
        <script type="text/javascript">
            function toggle_cache_expiration_div()
            {
                var use_cache = $("#use_cache").is(":checked");
                if (use_cache) {
                    $("#cache_config_div").show();
                }
                else {
                    $("#cache_config_div").hide();
                }
            }
            $("#use_cache").change(function() {
                toggle_cache_expiration_div();
            });
            toggle_cache_expiration_div();
        </script>
        <label for="enable_multicrawling">Enable Multicrawling</label>
         ${renderer.checkbox("enable_multicrawling")}<br/>
         ${renderer.errorlist("enable_multicrawling")}<br/>
        <label for="crawls_per_day" >Crawls per day</label><br/>
    	  ${renderer.text("crawls_per_day", size=2)}<br/>
    	  ${renderer.errorlist("crawls_per_day")}<br/>
        <br/>

        <label for="crawl_method">Crawl Method</label>
        <select name="crawl_method" id="crawl_method">
             <option></option>
             % for crawl_method_name in crawl_methods:
                 <option value="${crawl_method_name}" ${'selected' if spider.crawl_method2 and spider.crawl_method2.crawl_method == crawl_method_name else ''}>${crawl_method_name}</option>
             % endfor
        </select><br/><br/>
        ${renderer.errorlist("crawl_method")}
        <div class="crawl_method_check" style="display:${'block' if spider.crawl_method2 else 'none'};border: 1px dotted grey; padding: 1px; padding-bottom: 10px; margin-bottom: 15px"
             id="crawl_method_check_div">
            <button id="crawl_method_check">Check if spider fits</button>
            <span id="crawl_method_fits"></span>
            <div id="crawl_method_errors" style="color:red; font-size:80%; line-height: 2px"></div>
            % for crawl_method_name in crawl_methods:
                % if crawl_method_name in crawl_method_params:
                    <div class="crawl_method_params" style="display:${'block' if spider.crawl_method2 and spider.crawl_method2.crawl_method == crawl_method_name else 'none'};"
                        id="${crawl_method_name}_div">
                        <p>${crawl_method_name} params:</p>
                        % for field, field_data in crawl_method_params[crawl_method_name].items():
                            <label for="${crawl_method_name}_${field}">${field_data['title']}:</label>
                            % if field_data['type'] == 'enum':
                                <select name="${crawl_method_name}_${field}" id="${crawl_method_name}_${field}">
                                    % for value, value_title in field_data['values'].items():
                                        <option value="${value}" ${'selected' if spider.crawl_method2 and spider.crawl_method2.params.get(field) == value else ''}>${value_title}</option>
                                    % endfor
                                </select>
                            % elif field_data['type'] == 'cron_day':
                                <input type="hidden" name="${crawl_method_name}_${field}" id="${crawl_method_name}_${field}_cron_in" />
                                <div id="${crawl_method_name}_${field}_cron" style="white-space: normal"></div>
                                <script type="text/javascript">
                                    var field_name = "${crawl_method_name}_${field}";
                                    var value = "* * ${spider.crawl_method2.params.get(field, '') if spider.crawl_method2 else ''}";
                                    $(document).ready(function() {
                                        $('#' + field_name + '_cron').jqCron({
                                            enabled_minute: false,
                                            enabled_hour: false,
                                            multiple_dom: true,
                                            multiple_month: true,
                                            multiple_dow: true,
                                            multiple_time_hours: true,

                                            multiple_mins: false,
                                            multiple_time_minutes: false,

                                            numeric_zero_pad: true,

                                            default_period: 'week',
                                            default_value: value,

                                            bind_to: $('#' + field_name + '_cron_in'),
                                            bind_method: {
                                                set: function($element, value) {
                                                    $element.val(value);
                                                }
                                            }
                                        }); // apply cron with default options
                                    });
                                </script>
			    % elif field_data['type'] == 'bool':
			        <input name="${crawl_method_name}_${field}" id="${crawl_method_name}_${field}" ${'checked' if spider.crawl_method2 and spider.crawl_method2.params.get(field, '') else ''} type="checkbox" />
                            % else:
                                <input name="${crawl_method_name}_${field}" id="${crawl_method_name}_${field}" value="${spider.crawl_method2.params.get(field, '') if spider.crawl_method2 else ''}" />
                            % endif
                        % endfor
                    </div>
                % endif
            % endfor
        </div>
        <script type="text/javascript">
            $("#crawl_method").change(function() {
                var crawl_method = $("#crawl_method").val();
                $(".crawl_method_params").hide();
                $("#" + crawl_method + "_div").show();
                if (crawl_method) {
                    $("#crawl_method_check_div").show();
                }
                else {
                    $("#crawl_method_check_div").hide();
                }
            });
            function check_spider_fits() {
                var crawl_method = $("#crawl_method").val();
                var url = "${request.route_url('check_crawl_method', account=account, spider=spider.name)}";
                url = url + '?method=' + crawl_method;
                $("#crawl_method_errors").empty();
                $("#crawl_method_fits").css('color', 'yellow');
                $("#crawl_method_fits").text('Checking...');
                $.ajax(
                    url,
                    {
                        success: function(data) {
                            if (data.status) {
                                $("#crawl_method_fits").css('color', 'green');
                                $("#crawl_method_fits").text('Fits!');
                            }
                            else {
                                $("#crawl_method_fits").css('color', 'red');
                                $("#crawl_method_fits").text('Does not fit');

                                if (data.errors) {
                                    $.each(data.errors, function(idx, el) {
                                        var escaped = $('<div/>').text(el).html();
                                        $("#crawl_method_errors").append($("<p>" + escaped + "</p>"));
                                    })
                                }
                            }
                        },
                        error: function(xhr, data) {
                            $("#crawl_method_fits").css('color', 'red');
                            $("#crawl_method_fits").text('Error checking crawl method: ' + xhr.responseText);
                        }
                    }
                );
            }
            $("#crawl_method_check").click(function(event) {
                check_spider_fits();
                event.preventDefault();
            });
            % if spider.crawl_method2:
                check_spider_fits();
            % endif
        </script>

        <label for="concurrent_requests">Concurrent Requests</label>
         ${renderer.text("concurrent_requests", size=3)}<br/><br/>
         ${renderer.errorlist("concurrent_requests")}
        <label for="worker_server_id">Worker server</label>
        <select name="worker_server_id" id="worker_server_id">
            <option value="" ${'selected' if spider.worker_server_id is None else ''}>No preference (any available)</option>
            % for worker_server in worker_servers:
	        % if worker_server.enabled:
                <option value="${worker_server.id}" ${'selected' if spider.worker_server_id == worker_server.id else ''}>${worker_server.name}</option>
		% endif
            % endfor
        </select><br/><br/>

        <label for="additional_fields_group_id">Additional fields group</label>
        <select name="additional_fields_group_id" id="additional_fields_group_id">
            <option></option>
            % for additional_fields_group in additional_fields_groups:
                <option value="${additional_fields_group.id}" ${'selected' if spider.additional_fields_group_id == additional_fields_group.id else ''}>${additional_fields_group.name}</option>
            % endfor
        </select><br/><br/>
	<fieldset><legend>Errors detection config</legend>
        <label for="silent_updates">Silent updates when old or new price is 0</label>
        ${renderer.checkbox("silent_updates")}<br/><br/>
        ${renderer.errorlist("silent_updates")}
	<label for="update_percentage_error">Max percentage of number of overall changes for a valid update</label><br/>
	${renderer.text("update_percentage_error", size=6)}<br/>
    	 ${renderer.errorlist("update_percentage_error")}
         <label for="additions_percentage_error">Max percentage of number of additions for a valid update</label><br/>
         ${renderer.text("additions_percentage_error", size=6)}<br/>
         ${renderer.errorlist("additions_percentage_error")}
         <label for="deletions_percentage_error">Max percentage of number of deletions for a valid update</label><br/>
         ${renderer.text("deletions_percentage_error", size=6)}<br/>
         ${renderer.errorlist("deletions_percentage_error")}
         <label for="price_updates_percentage_error">Max percentage of number of price updates for a valid update</label><br/>
         ${renderer.text("price_updates_percentage_error", size=6)}<br/>
         ${renderer.errorlist("price_updates_percentage_error")}
        <label for="max_price_change_percentage">Max percentage price change for a single product</label><br/>
         ${renderer.text("max_price_change_percentage", size=6)}<br/>
         ${renderer.errorlist("max_price_change_percentage")}
        <label for="additional_changes_percentage_error">Max percentage price of number of changes for additional fields</label><br/>
         ${renderer.text("additional_changes_percentage_error", size=6)}<br/>
         ${renderer.errorlist("additional_changes_percentage_error")}
        <label for="stock_percentage_error">Max percentage of products moved to out of stock for a valid update</label><br/>
         ${renderer.text("stock_percentage_error", size=6)}<br/>
         ${renderer.errorlist("stock_percentage_error")}
	<label for="add_changes_empty_perc">Max percentage of changes to empty value for additional fields</label><br/>
         ${renderer.text("add_changes_empty_perc", size=6)}<br/>
        ${renderer.errorlist("add_changes_empty_perc")}
	<label for="image_url_perc">Max percentage of Image URL changes</label><br/>
         ${renderer.text("image_url_perc", size=6)}<br/>
        ${renderer.errorlist("image_url_perc")}
	<label for="category_change_perc">Max percentage of category changes</label><br/>
         ${renderer.text("category_change_perc", size=6)}<br/>
        ${renderer.errorlist("category_change_perc")}
	<label for="sku_change_perc">Max percentage of SKU changes</label><br/>
         ${renderer.text("sku_change_perc", size=6)}<br/>
         ${renderer.errorlist("sku_change_perc")}
        <label for="check_deletions">Check Deletions</label>
         ${renderer.checkbox("check_deletions")}<br/>
         ${renderer.errorlist("check_deletions")}<br/>
	<label for="ignore_identifier_changes">Ignore identifier changes</label>
        ${renderer.checkbox("ignore_identifier_changes")}<br/>
        ${renderer.errorlist("ignore_identifier_changes")}<br/>
	<label for="ignore_connection_errors">Ignore connection errors</label>
        ${renderer.checkbox("ignore_connection_errors")}<br/>
        ${renderer.errorlist("ignore_connection_errors")}<br/>
	<label for="ignore_additional_changes">Ignore additional change fields (Separated by "|")</label>
        ${renderer.text("ignore_additional_changes")}<br/>
        ${renderer.errorlist("ignore_additional_changes")}<br/>
	<label for="priority_spider">Priority spider</label>
        ${renderer.checkbox("priority_possible_errors")}<br/>
        ${renderer.errorlist("priority_possible_errors")}<br />
	<label for="automatic_retry_enabled">Automatic retry enabled</label>
        ${renderer.checkbox("automatic_retry_enabled")}<br/>
        ${renderer.errorlist("automatic_retry_enabled")}<br/>
	<label for="automatic_retries_max">Max retries number (Automatic retry)</label>
        ${renderer.text("automatic_retries_max")}<br/>
        ${renderer.errorlist("automatic_retries_max")}<br/>
	</fieldset>
	<br />
	<label for="price_conversion_rate">Price conversion rate</label><br/>
         ${renderer.text("price_conversion_rate", size=6)}<br/>
         ${renderer.errorlist("price_conversion_rate")}<br />
         <label for="enabled">Enabled</label>
         ${renderer.checkbox("enabled")}<br/>
         ${renderer.errorlist("enabled")}
          <h3>Email notification receivers(Comma separated)</h3>
         % for status in statuses:
           <label for="${status}_emails">${statuses_labels[status]}</label><br/>
           ${renderer.text(status + "_emails", size=30)}<br/>
           ${renderer.errorlist(status + "_emails")}
         % endfor
         <label for="not_uploaded_alert_receivers">Spider has not uploaded for 2 or more days</label><br />
         ${renderer.text("not_uploaded_alert_receivers", size=30)}<br/>
         ${renderer.errorlist("not_uploaded_alert_receivers")}
    </div>

    <br />

    <div class="buttons">
        ${renderer.submit("submit", "Submit")}
	</div>
	${renderer.end()}
</body>
</html>
