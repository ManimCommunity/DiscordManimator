import base64
import requests
from flask import Flask, request, jsonify, abort, g, Response
from flask_cors import CORS
import io
import time
import json
from hashlib import sha256
import hmac
import logging
import os

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from google.oauth2.service_account import Credentials
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.discovery import build

from profanity import profanity
from better_profanity import profanity as profanityb

from deta import Deta
import time

import http.client

'''
import newrelic.agent
newrelic.agent.initialize('newrelic.ini')
'''


app = Flask(__name__)

CORS(app, resources={r"/generate-image": {"origins": ["https://01d284.myshopify.com", "https://itomato.cloud"]}, r"/upload": {"origins": ["https://01d284.myshopify.com", "https://itomato.cloud"]}, r"/generate-mockup": {"origins": ["https://01d284.myshopify.com", "https://itomato.cloud"]}, r"/order-paid": {"origins": ["https://01d284.myshopify.com", "https://itomato.cloud"]}, r"/get-last-order": {"origins": ["https://01d284.myshopify.com", "https://itomato.cloud"]}}, expose_headers=['X-RateLimit-Limiter'])

'''
# Initialize DetaStorage custom class
class DetaStorage:
    def __init__(self, deta_project_key, base_name):
        self.deta = Deta(deta_project_key)
        self.base = self.deta.Base(base_name)

    def get(self, key):
        item = self.base.get(key)
        return item["value"] if item else None

    def set(self, key, value, expire_in=None):
        self.base.put({"key": key, "value": value}, expire_in=expire_in)

    def incr(self, key, amount, maximum, expire_in=None):
        item = self.base.get(key)
        if item:
            value = min(item["value"] + amount, maximum)
            self.base.put({"key": key, "value": value}, expire_in=expire_in)
        else:
            value = min(amount, maximum)
            self.base.put({"key": key, "value": value}, expire_in=expire_in)
        return value

    def expire(self, key, seconds):
        item = self.base.get(key)
        if item:
            # Set the new expiry time based on the current time + seconds
            expire_at = int(time.time()) + seconds
            self.base.update({"expire_at": expire_at}, key)

'''

'''
# Create a logger object
logger = logging.getLogger('flask-limiter')

# Set the level of the logger. This can be DEBUG, INFO, WARNING, ERROR, or CRITICAL
logger.setLevel(logging.DEBUG)

# Create a stream handler for the logger
handler = logging.StreamHandler()

# Set the level of the stream handler. This can be DEBUG, INFO, WARNING, ERROR, or CRITICAL
handler.setLevel(logging.DEBUG)

# Create a formatter and add it to the handler
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

# Add the handler to the logger
logger.addHandler(handler)

# Now, you can log messages using logger.debug(), logger.info(), logger.warning(), logger.error(), and logger.critical()
# For example:
logger.debug('This is a debug message')
'''

def get_remote_address():
    if 'X-Forwarded-For' in request.headers:
        # The 'X-Forwarded-For' header can contain multiple IP addresses,
        # so we take the first one which is the public IP address
        return request.headers.getlist("X-Forwarded-For")[0].rpartition(' ')[-1]
    else:
        return request.remote_addr


'''

'''

@app.route('/', methods=['GET'])
def root():
    return jsonify({'status': 'server online!'})

@app.route('/generate-image', methods=['POST'])
@limiter1.limit("5/month")
def buffer():
    data = request.get_json()
    text = data.get('text')
    g.limiter = 'limiter1 - minutes'
    return generate_image(text)

@limiter1.limit("1/minute")
def generate_image(text):
    if profanity.contains_profanity(text) or profanityb.contains_profanity(text):
        with app.app_context():
            return jsonify({'error': 'Inappropriate language is not allowed'}), 422
    base64_image = buttonPress(text)
    updated_base64_image = "empty"
    try:
        mockup_url, public_url = upload_full(base64_image)
        print(public_url)
    except Exception as error:
        message = str(error)
        with app.app_context():
            return jsonify({'error': message}), 500
    with app.app_context():
        return jsonify({'mockup_url': mockup_url, 'public_url': public_url})
    #return jsonify({'filename': filename})



@app.errorhandler(429)
def rate_limit_handler(e):
    print(e)
    limiter_info = getattr(g, 'limiter', 'limiter2 - months')
    response = jsonify({
        "message": "Too many requests. Please try again later.",
        "limit_info": limiter_info
    })
    response.headers['X-RateLimit-Limiter'] = limiter_info
    response.status_code = 429
    return response
    


@app.route('/upload', methods=['POST'])
def upload():
 
    # Get the base64 image from the request
    if request.get_json() is not None:
        data = request.get_json()
        base64_image = data.get('image')

    if not base64_image:
        return jsonify({'error': 'No image provided'}), 400

    # Convert base64 image to bytes
    image_data = base64.b64decode(base64_image)
