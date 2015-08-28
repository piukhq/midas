from flask import Flask
from redis import StrictRedis

app = Flask('core')
app.config.from_object('settings')

redis = StrictRedis(host='0.0.0.0', port=6379, db=0)

from app import views
