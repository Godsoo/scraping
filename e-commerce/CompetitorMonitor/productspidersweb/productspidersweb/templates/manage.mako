<html>
<head>
    <script type="text/javascript" src="/productspiders/static/js/jquery-1.9.1.min.js"></script>
    <script type="text/javascript">
        function run_crawl() {
            $('#crawl_msg').text('Running crawl...');
            $.post('/productspiders/runcrawl', {spider: $('#spider').val()}, function (data) {
                $('#crawl_msg').text('Done.');
            });
        }

        function run_upload() {
            $('#upload_msg').text('Running upload...');
            $.post('/productspiders/runupload', {}, function (data) {
                $('#upload_msg').text('Done.');
            });

        }
    </script>
</head>
<body>
    <a href="${request.route_url('logout')}" title="Logout">Logout</a>
    <br /><br />
    <a href="${request.route_url('home')}" title="Home">Home</a>
	<h1>Manage</h1>
	<form>
        <a href="javascript:run_crawl();">Run crawl pass</a><br/>
        <label for="spider">Spider</label>
        <select id="spider" name="spider">
                <option value="" selected="selected">All</option>
            % for spider in spiders:
                <option value="${spider}">${spider}</option>
            % endfor
        </select>
	</form>
    <br/>
    <a href="javascript: run_upload();">Run upload</a>

    <br/>
    <div id="crawl_msg"></div>
    <div id="upload_msg"></div>
</body>
</html>