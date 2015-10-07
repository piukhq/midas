from app.encryption import AESCipher
from settings import AES_KEY
import json

CREDENTIALS = {
    "tesco": {
        'email': 'julie.gormley100@gmail.com',
        'password': 'NSHansbrics5',
        'card_number': '634004024051328070'
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
            'card_number': '9826300030842203013',
            'password': 'QMHansbrics6',
    },
    "bad": {
            'email': '234234@bad.com',
            'password': '234234',
    },
    "cooperative": {
            'card_number': '633174911212875989',
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
    }
}


def encrypt(scheme_slug):
    """For testing encryption"""
    aes = AESCipher(AES_KEY.encode())

    return aes.encrypt(json.dumps(CREDENTIALS[scheme_slug])).decode()
