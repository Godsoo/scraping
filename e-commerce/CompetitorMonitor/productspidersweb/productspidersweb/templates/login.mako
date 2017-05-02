<html>
<head>
</head>
<body>
<h1>Login</h1>
<form method="post" action="${request.route_url('login')}">
    <label for="username">Username:</label>
    <input type="input" id="username" name="username" value="${username}" /><br />

    <label for="password">Password:</label>
    <input type="password" id="password" name="password" value="" /><br />

    <input type="submit" value="Login" />
</form>
<br/>
% for error in errors:
<div id="error_msg" style="color: red">${error}</div>
% endfor
</body>
</html>