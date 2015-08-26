from flask import Flask


app = Flask('core')
app.config.from_object('settings')


from app import views