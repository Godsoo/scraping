<%inherit file="base.html"/>

<%block name="content">
    <div class="modal fade bs-example-modal-sm" id="modalnts" tabindex="-1" role="dialog" aria-hidden="true">
    </div>

    <div class="modal fade bs-example-modal-sm" id="modaldsh" tabindex="-1" role="dialog" aria-hidden="true">
    </div>

    <div class="container">

        <div class="row">
            <div class="col-md-4">
                <div class="row">
                    <div class="col-md-6"></div>
                    <div class="col-md-6">
                        <div class="row">
                            <div class="col-md-12">
                                <strong><u>Possible Errors</u></strong>
                            </div>
                        </div>
                        <div class="row">
                            <div class="col-md-2"></div>
                            <div class="col-md-10">
                                <a href="${request.route_url('list_all_spiders', _query={'errors': 'possible'})}"><strong>${possible_count}</strong></a>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-md-4"></div>
            <div class="col-md-4">
                <div class="row">
                    <div class="col-md-6">
                        <div class="row">
                            <div class="col-md-12">
                                <strong><u>Real Errors</u></strong>
                            </div>
                        </div>
                        <div class="row">
                        <div class="col-md-2"></div>
                            <div class="col-md-10">
                                <a href="${request.route_url('list_all_spiders', _query={'errors': 'real'})}"><strong>${real_count}</strong></a>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-6"></div>
                </div>
            </div>
        </div>

        <hr />

        <div class="row">
            <div class="col-md-6">
                <table class="table table-striped table-bordered table-condensed gray_table">
                    <thead>
                        <tr>
                            <th>Error Type</th>
                            <th>#Number of Spiders</th>
                        </tr>
                    </thead>
                    <tbody>
                        % for error_type in error_types:
                        <tr>
                            <td>${error_type[0]}</td>
                            <td>${error_type[1]}</td>
                        </tr>
                        % endfor
                    </tbody>
                </table>
            </div>
            <div class="col-md-6">
                <table class="table table-striped table-bordered table-condensed gray_table">
                    <thead>
                        <tr>
                            <th>Developer</th>
                            <th>#Number of Spiders Assigned</th>
                        </tr>
                    </thead>
                    <tbody>
                        % for developer in developers:
                        <tr>
                            <td>${developer[0]}</td>
                            <td>${developer[1]}</td>
                        </tr>
                        % endfor
                    </tbody>
                </table>
            </div>
        </div>

        <div class="row">
            <div class="col-md-12">
              <div class="panel panel-primary">
                <div class="panel-heading" style="height: 50px;">
                  <h3 style="float:left;" class="panel-title"><i class="fa fa-bar-chart-o"></i> Number of Potential and Real Errors Logged Per Day</h3>
                  <div style="float:right">
                      <div style="float:left;">
                          <i>From:&nbsp;</i><input id="chrfd" type="text" size="10" class="datepicker-chr1" style="padding:1px;marging:1px;color:grey;" />
                      </div>
                      <div style="float:left;margin-left:25px;">
                          <i>To:&nbsp;</i><input id="chrtd" type="text" size="10" class="datepicker-chr1" style="padding:1px;marging:1px;color:grey;" />
                      </div>
                  </div>
                </div>
                <div class="panel-body">
                  <div id="chart1" style="height:150px;"></div>
                </div>
              </div>
            </div>
        </div>

        <div class="row">
            <div class="col-md-12">
              <div class="panel panel-primary">
                <div class="panel-heading" style="height: 50px;">
                  <h3 style="float:left;" class="panel-title"><i class="fa fa-bar-chart-o"></i> Total Number of Real Errors Per Day</h3>
                  <div style="float:right">
                      <div style="float:left;">
                          <i>From:&nbsp;</i><input id="chr2fd" type="text" size="10" class="datepicker-chr2" style="padding:1px;marging:1px;color:grey;" />
                      </div>
                      <div style="float:left;margin-left:25px;">
                          <i>To:&nbsp;</i><input id="chr2td" type="text" size="10" class="datepicker-chr2" style="padding:1px;marging:1px;color:grey;" />
                      </div>
                  </div>
                </div>
                <div class="panel-body">
                  <div id="chart2" style="height:150px;"></div>
                </div>
              </div>
            </div>
        </div>

        <div class="row">
          <div class="col-md-12">
            <fieldset>
                <legend>Last Updated</legend>
                <div id="filter-bar"></div>
                <table id="tbl"
                   data-toggle="table"
                   data-url="last_updated.json"
                   data-toolbar="#filter-bar"
                   data-show-toggle="true"
                   data-show-columns="true"
                   data-show-filter="true"
                   data-show-refresh="true"
                   data-pagination="true"
                   data-show-export="true"
                   class="table table-striped table-bordered table-condensed gray_table">
                    <thead>
                        <tr>
                            <th data-field="priority" data-formatter="priority_formatter" data-align="center" data-sortable="true">Priority</th>
                            <th data-field="account_name" data-align="center" data-sortable="true">Account</th>
                            <th data-field="site_name" data-formatter="site_name_formatter" data-align="center" data-sortable="true">Site</th>
                            <th data-field="last_updated" data-align="center" data-sortable="true">Last Updated</th>
                            <th data-field="status" data-align="center" data-sortable="true">Crawl Status</th>
                            <th data-field="real_error" data-align="center" data-sortable="true">Real Error</th>
                            <th data-field="duration_error_state" data-align="center">Duration in error state</th>
                            <th data-formatter="site_assign_formatter">Assign</th>
                            <th data-formatter="site_notes_formatter">Notes</th>
                        </tr>
                    </thead>
                </table>
            </fieldset>
        </div>
    </div>

    <div class="row">
      <div class="col-md-12">
        <fieldset>
            <legend>Disabled Sites</legend><a href="javascript: display_all_disabled_sites();" style="float:right;"><strong>View Hidden</strong></a>
            <table class="table table-striped table-bordered table-condensed gray_table" id="sd-table">
                <thead>
                    <tr>
                        <th>Account</th>
                        <th>Site</th>
                        <th>Auto Upload</th>
                        <th>Enabled</th>
                        <th>Last Updated</th>
                        <th>Notes</th>
                        <th>Hide</th>
                    </tr>
                </thead>
                <tbody id="dsbody">
                    % for site in disabled_sites:
                    <tr id="dsrow_${site['site_id']}">
                        <td>${site['account_name']}</td>
                        <td><a href="${request.route_url('list_crawls', spider_id=site['site_id'])}">${site['site_name']}</a></td>
                        % if site['auto_upload']:
                        <td><div class="text-center"><img src="/productspiders/static/images/tick.png" /></div></td>
                        % else:
                        <td><div class="text-center"><img src="/productspiders/static/images/cross.png" /></div></td>
                        % endif
                        % if site['enabled']:
                        <td><div class="text-center"><img src="/productspiders/static/images/tick.png" /></div></td>
                        % else:
                        <td><div class="text-center"><img src="/productspiders/static/images/cross.png" /></div></td>
                        % endif
                        <td>${site['last_updated'].strftime('%d/%m/%Y') if site['last_updated'] else ''}</td>
                        <td><a href="javascript: show_notes(${site['site_id']});">View</a></td>
                        <td><a href="javascript: hide_disabled(${site['site_id']});" class="disabled-button">Hide</a></td>
                    </tr>
                    % endfor
                </tbody>
            </table>
        </fieldset>
      </div>
    </div>

<script src="/productspiders/static/js/highcharts.js"></script>
<script type="text/javascript">

    function priority_formatter(value, row, index) {
        if (row['priority']) {
            return '<span style="color:green;text-align:center;">Yes</span>';
        } else {
            return '';
        }
    }

    function site_name_formatter(value, row, index) {
        return '<a target="_blank" href="/productspiders/spiders/' + row['site_id'] + '/crawls">' + row['site_name'] + '</a>';
    }

    function site_assign_formatter(value, row, index) {
        if (row['assign']) {
            return '<a style="color:green;" href="javascript: edit_assign(' + row['site_id'] + ');">#' + row['assign']['name'] + '</a>';
        } else {
            return '<a href="javascript: edit_assign(' + row['site_id'] + ');">Assign</a>';
        }
    }

    function site_notes_formatter(value, row, index) {
        return '<a href="javascript: show_notes(' + row['site_id'] + ');">View</a>';
    }

    function hide_disabled(site_id) {
        $.post('/productspiders/hide_disabled_site', {id: site_id})
            .done(function(data) {
                    $('#dsrow_' + site_id).hide();
                });
    }

    function show_disabled(site_id) {
        $.post('/productspiders/show_disabled_site', {id: site_id})
            .done(function(data) {
                    display_all_disabled_sites();
                });
    }

    function display_all_disabled_sites(){
        $.get('/productspiders/list_all_disabled_sites')
            .done(function(data) {
                    $('#dsbody').html('');
                    $.each(data,
                        function (key, val) {
                            var tr = $('<tr id="#dsrow_' + val.site_id + '"></tr>');
                            $('<td>' + val.account_name + '</td>').appendTo(tr);
                            $('<td>' + val.site_name + '</td>').appendTo(tr);
                            if (val.auto_upload) {
                                $('<td><div class="text-center"><img src="/productspiders/static/images/tick.png" /></div></td>').appendTo(tr);
                            } else {
                                $('<td><div class="text-center"><img src="/productspiders/static/images/cross.png" /></div></td>').appendTo(tr);
                            }
                            if (val.enabled) {
                                $('<td><div class="text-center"><img src="/productspiders/static/images/tick.png" /></div></td>').appendTo(tr);
                            } else {
                                $('<td><div class="text-center"><img src="/productspiders/static/images/cross.png" /></div></td>').appendTo(tr);
                            }
                            $('<td>' + val.last_updated + '</td>').appendTo(tr);
                            $('<td><a href="#">View</a></td>').appendTo(tr);
                            if (!val.hidden) {
                                $('<td><a href="javascript: hide_disabled(' + val.site_id + ');" class="disabled-button">Hide</a></td>').appendTo(tr);
                            } else {
                                $('<td><a href="javascript: show_disabled(' + val.site_id + ');" class="disabled-button">Show</a></td>').appendTo(tr);
                            }
                            tr.appendTo('#dsbody');
                        });
                });
    }

    function edit_assign(site_id){
        $('#modaldsh').load('/productspiders/assign_issue/' + site_id);
        $('#modaldsh').modal('toggle');
    }

    function show_notes(site_id){
        $('#modalnts').load('/productspiders/spider_notes/' + site_id);
        $('#modalnts').modal('toggle');
    }

    function draw_chart(from, to) {
        $.get('/productspiders/list_daily_errors/' + from + '/' + to)
            .done(function(data) {
                    $('#chart1').highcharts({
                        chart: {
                            type: "line"
                        },
                        title: {
                            text: ""
                        },
                        yAxis: {
                            min: 0,
                            minPadding: 0,
                            startOnTick: true,
                            title: {text: "# of errors"},
                        },
                        xAxis: {
                            categories: data.days,
                        },
                        tooltip: {
                            borderColor: 'black',
                            borderWidth: 3,
                            shared: true,
                        },
                        credits: {
                              enabled: false
                        },
                        series: [
                        {
                            name: "Real errors",
                            data: data.real,
                            color: 'red',
                        },
                        {
                            name: "Possible errors",
                            data: data.possible,
                            color: 'blue',
                        },
                        ]
                    });
                });
    }

    function draw_chart2(from, to) {
        $.get('/productspiders/list_total_real_errors/' + from + '/' + to)
            .done(function(data) {
                    $('#chart2').highcharts({
                        chart: {
                            type: "line"
                        },
                        title: {
                            text: ""
                        },
                        yAxis: {
                            min: 0,
                            minPadding: 0,
                            startOnTick: true,
                            title: {text: "# of errors"},
                        },
                        xAxis: {
                            categories: data.days,
                        },
                        tooltip: {
                            borderColor: 'black',
                            borderWidth: 3,
                            shared: true,
                        },
                        credits: {
                              enabled: false
                        },
                        series: [
                        {
                            name: "Real errors",
                            data: data.real,
                            color: 'red',
                        },
                        ]
                    });
                });
    }

    $(document).ready(function () {
        draw_chart('${from_day.strftime("%d/%m/%Y")}', '${to_day.strftime("%d/%m/%Y")}');
        $('#chrfd').val('${from_day.strftime("%d/%m/%Y")}');
        $('#chrtd').val('${to_day.strftime("%d/%m/%Y")}');

        draw_chart2('${from_day.strftime("%d/%m/%Y")}', '${to_day.strftime("%d/%m/%Y")}');
        $('#chr2fd').val('${from_day.strftime("%d/%m/%Y")}');
        $('#chr2td').val('${to_day.strftime("%d/%m/%Y")}');
    
        $('body').on('hidden.bs.modal', '.modal', function () {
            $(this).removeData('bs.modal');
        });

        $('.datepicker-chr1').datepicker({
            format: "dd/mm/yyyy",
        }).on('changeDate', function(ev) {
            from_date = $('#chrfd').val();
            to_date = $('#chrtd').val();
            if (from_date && to_date) {
                draw_chart(from_date, to_date);
            }
        });

        $('.datepicker-chr2').datepicker({
            format: "dd/mm/yyyy",
        }).on('changeDate', function(ev) {
            from_date = $('#chr2fd').val();
            to_date = $('#chr2td').val();
            if (from_date && to_date) {
                draw_chart2(from_date, to_date);
            }
        });

    });

</script>

</%block>
