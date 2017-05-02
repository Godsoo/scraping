import sys
import ConfigParser
from flask import Flask
from flask import abort
from flask import request
from captcha import get_captcha_from_url


config = ConfigParser.RawConfigParser()
config.read('../config.ini')
API_KEY = config.get('captcha_service', 'api_key')

app = Flask(__name__)


@app.route("/get_captcha")
def get_captcha():
    api_key = request.args.get('api_key')

    if api_key != API_KEY:
    	abort(403)

    url = request.args.get('url')
    if not url:
    	abort(404)

    capt = get_captcha_from_url(url)
    return capt

if __name__ == "__main__":
    app.run(host='0.0.0.0')