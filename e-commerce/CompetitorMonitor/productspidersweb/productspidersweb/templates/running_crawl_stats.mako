<html>
<head>
<script src="/productspiders/static/js/jquery.js"></script>
<link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.6/css/bootstrap.min.css" integrity="sha384-1q8mTJOASx8j1Au+a5WDVnPi2lkFfwwEAa8hDDdjZlpLegxhjVME1fgjWPGmkzs7" crossorigin="anonymous">

<!-- Optional theme -->
<link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.6/css/bootstrap-theme.min.css" integrity="sha384-fLW2N01lMqjakBkx3l/M9EahuwpSfeNvV63J5ezn3uZzapT0u7EYsXMjQV+0En5r" crossorigin="anonymous">

<!-- Latest compiled and minified JavaScript -->
<script src="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.6/js/bootstrap.min.js" integrity="sha384-0mSbJDEHialfmuBBQP6A4Qrprq5OVfW37PRR3j5ELqxss1yVqOtnepnHVP9aJ7xS" crossorigin="anonymous"></script>
<script src="https://code.highcharts.com/highcharts.js"></script>

<script type="text/javascript">
$(function () {

    
    var averages = JSON.parse('${products_per_minute}');
        
    $('#products_chart').highcharts({

        title: {
            text: 'Scraped products per minute'
        },

        xAxis: {
            type: 'datetime'
        },

        yAxis: {
            title: {
                text: null
            }
        },

        tooltip: {
            crosshairs: true,
            shared: true,
            valueSuffix: ''
        },

        legend: {
        },

        series: [{
            name: 'Scraped products per minute',
            data: averages,
            zIndex: 1,
            marker: {
                fillColor: 'white',
                lineWidth: 2,
                lineColor: Highcharts.getOptions().colors[0]
            }
        }]
    });

    var pages = JSON.parse('${pages_per_minute}');
        
    $('#pages_chart').highcharts({

        title: {
            text: 'Crawled pages per minute'
        },

        xAxis: {
            type: 'datetime'
        },

        yAxis: {
            title: {
                text: null
            }
        },

        tooltip: {
            crosshairs: true,
            shared: true,
            valueSuffix: ''
        },

        legend: {
        },

        series: [{
            name: 'Crawled pages per minute',
            data: pages,
            zIndex: 1,
            marker: {
                fillColor: 'white',
                lineWidth: 2,
                lineColor: Highcharts.getOptions().colors[0]
            }
        }]
    });
});
</script>
</head>
<body>
<div class="panel panel-info" style="width: 90%; margin: 0 auto;">
<div class="page-header">
  <h1>Showing stats for ${spider.name}: ${crawl.crawl_date}</h1>
</div>
<div class="panel panel-info">
<div class="panel-heading">Current running stats</div>
<div class="panel-body">
<p><b>Start time:</b> ${str(crawl.start_time).split('.')[0]} GMT</p>
<p><b>Total products scraped:</b> ${items}</p>
% if perc is not None:
<div class="progress" style="width: 300px">
  <div class="progress-bar" role="progressbar" aria-valuenow="${perc}" aria-valuemin="0" aria-valuemax="100" style="width: ${perc}%;">
    ${perc}% (Approx)
  </div>
</div>
% endif
<p><b>Total pages crawled:</b> ${pages}</p>
<p><b>Products scraped in last minute:</b> ${irate}</p>
<p><b>Pages crawled in last minute:</b> ${prate}</p>
</div>
</div>

<div class="panel panel-info">
<div id="products_chart">

</div>
</div>
<div class="panel panel-info">
<div id="pages_chart">

</div>
</div>
</div>
</body>
</html>