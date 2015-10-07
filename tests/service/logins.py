from app.encryption import AESCipher
from settings import AES_KEY
import json

CREDENTIALS = {
    "tesco": {
        'user_name': 'julie.gormley100@gmail.com',
        'password': 'NSHansbrics5',
        'card_number': '634004024051328070'
    },
    "avios": {
        'username': 'chris.gormley2@me.com',
        'password': 'RZHansbrics5',
    },
    "british-airways": {
        'card_number': "49932498",
        'password': 'RAHansbrics14'
    },
    "advantage-card": {
            'user_name': 'julie.gormley100@gmail.com',
            'password': 'RAHansbrics5'
    },
    "superdrug": {
            'user_name': 'julie.gormley100@gmail.com',
            'password': 'FRHansbrics9'
    },
    "costa": {
            'user_name': 'chris.smith4@gmx.co.uk',
            'password': 'ZBHansbrics5',
    },
    "shell": {
            'user_name': 'chris.gormley2@me.com',
            'password': 'KRHansbrics5',
    },
    "nectar": {
            'card_number': '9826300030842203013',
            'password': 'QMHansbrics6',
    },
    "bad": {
            'user_name': '234234@bad.com',
            'password': '234234',
    },
    "cooperative": {
            'card_number': '633174911212875989',
            'post_code': 'BH23 1HT',
            'place_of_birth': "cheltenham",
    },
    "morrisons": {
        "user_name": "chris.gormley2@me.com",
        'password': 'RLHansbrics9',
    },
    "kfc": {
        "user_name": "chris.gormley2@me.com",
        "password": "BJHansbrics3",
    }
}


def encrypt(scheme_slug):
    """For testing encryption"""
    aes = AESCipher(AES_KEY.encode())

    return aes.encrypt(json.dumps(CREDENTIALS[scheme_slug])).decode()
