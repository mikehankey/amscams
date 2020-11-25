from flask import Flask
app = Flask(__name__)

@app.route('/')
def main_menu():
    return 'Main Menu!'


@app.route('/meteors/<amsid>/<date>/<meteor_sd_vid>')
def meteor_detail_page():
    return 'Meteor Detail!' 
