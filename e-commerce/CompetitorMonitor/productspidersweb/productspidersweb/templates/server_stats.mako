<%inherit file="server_dash_base.mako"/>
<%block name="header">

<style type="text/css">
  #main-panel {
  margin-left: 100px;
  margin-right: 100px;
  height: 920px;
  }
  #live-panel {
  margin-top: 20px;
  margin-left: 10px;
  margin-right: 0px;
  height: 300px;
  float: left;
  width: 48%;
  }
  #historical-panel {
  margin-top: 20px;
  margin-left: 0;
  margin-right: 10px;
  height: 300px;
  float: right;
  width: 48%;
  }

  #detail-panel {
  margin-left: 10px;
  margin-right: 10px;
  height: 500px;
  float: left;
  width: 98%;
  }

  #live-stats-chart, #historical-stats-chart {
      height: 230px;
  }

</style>
<script>
$(function () {
    $.getJSON('/productspiders/current_server_stats.json', function (data) {
    $('#live-stats-chart').highcharts({
        credits: {
            enabled: false
        },
        chart: {
            type: 'column'
        },
        title: {
            text: ''
        },
        xAxis: {
            categories: data.categories
        },
        yAxis: {
            min: 0,
            title: {
                text: 'Number of Spiders'
            },
            stackLabels: {
                enabled: true,
                style: {
                    fontWeight: 'bold',
                    color: (Highcharts.theme && Highcharts.theme.textColor) || 'gray'
                }
            }
        },
        legend: {
            align: 'right',
            x: -30,
            verticalAlign: 'top',
            y: 25,
            floating: true,
            backgroundColor: (Highcharts.theme && Highcharts.theme.background2) || 'white',
            borderColor: '#CCC',
            borderWidth: 1,
            shadow: false
        },
        tooltip: {
            formatter: function () {
                return '<b>' + this.x + '</b><br/>' +
                    this.series.name + ': ' + this.y + '<br/>' +
                    'Total: ' + this.point.stackTotal;
            }
        },
        plotOptions: {
            column: {
                stacking: 'normal',
                dataLabels: {
                    enabled: true,
                    color: (Highcharts.theme && Highcharts.theme.dataLabelsColor) || 'white',
                    style: {
                        textShadow: '0 0 3px black'
                    }
                }
            }
        },
        series: [{
            name: 'Scheduled',
            data: data.scheduled,
            color: '#830002'
        }, {
            name: 'Running',
            data: data.running,
            color: '#e1dddd'
        }, {
            name: 'Finished',
            data: data.finished,
            color: '#9BBA4E'
        }]
    });
});});

    $.getJSON('/productspiders/historical_server_stats.json', function (data) {
        $('#historical-stats-chart').highcharts({
            credits: {
                enabled: false
            },
            chart: {
                type: 'area'
            },
            title: {
                text: ''
            },
            subtitle: {
                text: ''
            },
            xAxis: {
                type: 'datetime'
            },
            yAxis: {
                title: {
                    text: 'Number of spiders'
                }
            },
            tooltip: {
                shared: true
            },
            plotOptions: {
                area: {
                    stacking: 'normal',
                    lineColor: '#666666',
                    lineWidth: 1,
                    marker: {
                        lineWidth: 1,
                        lineColor: '#666666'
                    }
                }
            },
            series: [{
                name: 'Scheduled',
                data: data.scheduled,
                color: '#830002'
            }, {
                name: 'Running',
                data: data.running,
                color: '#e1dddd'
            }, {
                name: 'Finished',
                data: data.finished,
                color: '#9BBA4E'
            }]
        });
    });

</script>

</%block>


<div id="main-panel" class="panel panel-default">
  <div class="panel-heading">
      <h2 class="panel-title">Server Stats</h2>
  </div>
  <div id="live-panel" class="panel panel-primary">
    <div class="panel-heading">
      <h3 class="panel-title">Live Stats</h3>
    </div>
    <div class="panel-body">
      <div id="live-stats-chart">

      </div>
    </div>
  </div>
  <div id="historical-panel" class="panel panel-primary">
    <div class="panel-heading">
      <h3 class="panel-title">Hourly Stats</h3>
    </div>
    <div class="panel-body">
      <div id="historical-stats-chart">

      </div>
    </div>
  </div>

  <div id="detail-panel" class="panel panel-primary">
    <div class="panel-heading">
      <h3 class="panel-title">Scheduled and Running</h3>
    </div>
    <div class="panel-body">
      <table id="spiders_table" data-show-export="true" data-search="true" data-pagination="true" data-page-size="1000" data-height="400" class="table table-hover" data-toggle="table" data-url="current_spider_stats.json">
          <thead>
              <tr>
                <th data-field="pos">Pos</th>
                <th data-field="account">Account</th>
                <th data-field="spider">Spider</th>
                <th data-field="status">Status</th>
                <th data-field="server">Server</th>
                <th data-field="start_time">Start Time</th>
              </tr>
          </thead>
          <tbody>
          </tbody>
      </table>
    </div>
  </div>

</div>