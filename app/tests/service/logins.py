from app.encryption import AESCipher
from settings import AES_KEY
import json

CREDENTIALS = {
    "tesco-clubcard": {
        'email': 'julie.gormley100@gmail.com',
        'password': 'NSHansbrics5',
        'barcode': '634004024051328070'
    },
    "avios": {
        'email': 'chris.gormley2@me.com',
        'password': 'RZHansbrics5',
    },
    "british-airways": {
        'card_number': "49932498",
        'password': 'RAHansbrics14'
    },
    "advantage-card": {
            'email': 'julie.gormley100@gmail.com',
            'password': 'RAHansbrics5'
    },
    "superdrug": {
            'email': 'julie.gormley100@gmail.com',
            'password': 'FRHansbrics9'
    },
    "costa": {
            'email': 'chris.smith4@gmx.co.uk',
            'password': 'ZBHansbrics5',
    },
    "shell": {
            'email': 'chris.gormley2@me.com',
            'password': 'KRHansbrics5',
    },
    "nectar": {
            'barcode': '29930842203013',
            'password': 'QMHansbrics6',
    },
    "bad": {
            'email': '234234@bad.com',
            'password': '234234',
    },
    "cooperative": {
            'barcode': '633174911212875989',
            'post_code': 'BH23 1HT',
            'place_of_birth': "cheltenham",
    },
    "morrisons": {
        "email": "chris.gormley2@me.com",
        'password': 'RLHansbrics9',
    },
    "kfc": {
        "email": "chris.gormley2@me.com",
        "password": "BJHansbrics3",
    },
    "greggs": {
        "email": "chris.gormley2@me.com",
        "password": "RFHansbrics6",
    },
    "starbucks": {
        "email": "chris.gormley2@me.com",
        "password": "RRHansbrics9",
    },
    "debenhams": {
        "username": "gormleyc1",
        "password": "RCHansbrics9",
        "memorable_date": "28/08/2004",
    },
    "maximiles": {
        "email": "chris.gormley2@me.com",
        "password": "RLHansbrics9",
    },
    "eurostar": {
        "email": "chris.gormley2@me.com",
        "password": "QDHansbrics8"
    }
}


def encrypt(scheme_slug):
    """For testing encryption"""
    aes = AESCipher(AES_KEY.encode())

    return aes.encrypt(json.dumps(CREDENTIALS[scheme_slug])).decode()
