from app.encryption import AESCipher
from settings import AES_KEY
import json

CREDENTIALS = {
    "tesco-clubcard": {
        'email': 'julie.gormley100@gmail.com',
        'password': 'NSHansbrics5',
        'card_number': '634004024051328070'
    },
    "avios": {
        'email': 'chris.smith4@gmx.co.uk',
        'password': 'Loyalty1',
    },
    "avios_api": {
        'card_number': '3081471022657083',
        'last_name': 'GORMLEY',
        #  DoB not used for login or asked for in Hermes
        # 'date_of_birth': '01/01/1974',
    },
    "british-airways": {
        'username': "49932498",
        'password': 'Loyalty1'
    },
    "advantage-card": {
        'email': 'loyaltycards01@gmail.com',
        'password': 'ejUu3Z82in'
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
        'username': 'chris.gormley2@me.com',
        'password': 'KRHansbrics5',
    },
    "nectar": {
        'barcode': '29930842203013',
        'card_number': '9826300030842203013',
        'password': 'QMHansbrics6',
    },
    "bad": {
        'email': '234234@bad.com',
        'password': '234234',
    },
    "cooperative": {
            'email': 'chris.gormley2@me.com',
            'password': 'OBHansbrics4',
            # Card number for this account, not used in login
            # 'barcode': '633174913210282267'
    },
    "morrisons": {
        "email": "chris.gormley2@me.com",
        'password': 'Loyalty1',
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
        "username": "chris.gormley2@me.com",
        "password": "RRHansbrics9",
    },
    "star_rewards": {
        "card_number": "7076550200868547905",
        "password": "dZ13ep5z",
    },
    "debenhams": {
        "email": "chris.gormley2@me.com",
        "username": "gormleyj1",
        "password": "RCHansbrics9",
        "memorable_date": "28/08/2004",
    },
    "maximiles": {
        "email": "chris.gormley2@me.com",
        "password": "RLHansbrics9",
    },
    "waterstones": {
        "email": "chris.gormley2@me.com",
        "password": "RVHansbrics11",
    },
    "esprit": {
        "username": "chris.gormley2@me.com",
        "password": "SDHansbrics6",
    },
    "quidco": {
        "username": "chris.smith4@gmx.co.uk",
        "password": "NPHansbrics6",
    },
    "toysrus": {
        "email": "chris.gormley2@me.com",
        "password": "RSHansbrics7!",
    },
    "enterprise": {
        "username": "chris.gormley2@me.com",
        "password": "DDHansbrics10",
    },
    "heathrow": {
        "email": "chris.gormley2@me.com",
        "password": "RGHansbr15",
    },
    "hertz": {
        "username": "chris.gormley2@me.com",
        "password": "AGHansbrics5",
    },
    "eurostar": {
        "email": "chris.gormley2@me.com",
        "password": "QDHansbrics8",
    },
    "tabletable": {
        "email": "chris.gormley2@me.com",
        "password": "DSHansbrics10",
    },
    "decathlon": {
        "email": "chris.smith4@gmx.co.uk",
        "password": "Loyalty1",
    },
    "odeon": {
        "email": "chris.gormley2@me.com",
        "password": "MNHansbrics5",
    },
    "nandos": {
        "email": "nataliabrevot@live.com",
        "password": "LAngels2015!",
    },
    "beefeater": {
        "email": "chris.gormley2@me.com",
        "password": "DSHansbrics10",
    },
    "harrods": {
        "email": "chris.gormley2@me.com",
        "password": "RGHansbrics7",
    },
    "monsoon": {
        "email": "chris.gormley2@me.com",
        "password": "MLHansbrics7",
    },
    "jetblue": {
        "email": "loyaltycards01@gmail.com",
        "password": "2xMA8hazn7",
    },
    "qantas": {
        "card_number": "1933441600",
        "last_name": "walsh",
        "pin": "2124",
    },
    "the_perfume_shop": {
        "email": "chris.gormley2@me.com",
        "password": "OSHansbrics14",
    },
    "rewards4fishing": {
        "email": "la@loyaltyangels.com",
        "password": "LAngels2015!",
    },
    "rewards4golf": {
        "email": "la@loyaltyangels.com",
        "password": "gyYfRh26D2",
    },
    "rewards4racing": {
        "email": "la@loyaltyangels.com",
        "password": "YRKnQuP822",
    },
    "space_nk": {
        "barcode": "63385283721106029252",
        "email": "ssc@bink.com",
        "password": "Loyalty1",
    },
    "lufthansa": {
        "card_number": "992000656640646",
        "pin": "55296",
    },
    "avis": {
        "email": "chris.gormley2@me.com",
        "password": "RZHansbrics4",
    },
    "mandco": {
        "username": "la@loyaltyangels.com",
        "password": "f946HhpdMx",
    },
    "sparks": {
        "email": "chris.smith4@gmx.co.uk",
        "password": "Loyalty1",
    },
    "virgin": {
        "username": "1069267746",
        "password": "Loyalty1",
    },
    "ihg": {
        "username": "la@loyaltyangels.com",
        "pin": "1290",
    },
    "hyatt": {
        "username": "528180109F",
        "password": "Y2bRrPJ39V",
    },
    "holland_and_barrett": {
        "email": "chris.gormley2@me.com",
        "password": "SGHansbr17",
    },
    "starwood-preferred-guest": {
        "username": "LAngelBink",
        "password": "8n4Q9cjuPU",
        "favourite_food": "Chinese",
        "favourite_place": "Ascot",
        "favourite_attraction": "The Bink Office",
        "location_first_job": "Bagshot",
    },
    "the_works": {
        "email": "chris.gormley2@me.com",
        "password": "RSHansbrics8",
        "barcode": "6338846846810026009666"
    },
    "mymail": {
        "email": "chris.smith4@gmx.co.uk",
        "password": "KLHansbrics6",
    },
    "malaysia_airlines": {
        "card_number": "315377635",
        "password": "nA6AGt7G2Y",
    },
    "royal-orchid-plus": {
        "username": "NZ57271",
        "password": "d4Hgvf47",
    },
    "big-rewards": {
        "email": "la@loyaltyangels.com",
        "password": "Loyalty1",
    },
    "foyalty": {
        "barcode": "2900001336673",
        "email": "la@loyaltyangels.com",
    },
    "treat-me": {
        "email": "la@loyaltyangels.com",
        "password": "3Ws2BZ6Qod",
    },
    "priority-guest-rewards": {
        "username": "la@loyaltyangels.com",
        "password": "V6Z3p4LFoB",
    },
    "delta-skymiles": {
        "username": "9118431866",
        "password": "9Pv8nsv8hv",
    },
    "klm-flying-blue": {
        "username": "1109882571",
        "pin": "1234",
    },
    "le-club": {
        "username": "ssc@bink.com",
        "password": "Loyalty1",
    },
    "choicehotels": {
        "username": "LoyaltyAngels",
        "password": "ji7qM3i2jd",
    },
    "discovery": {
        "username": "LoyaltyAngels",
        "password": "CnMQY9YM83",
    },
    "clubcarlson": {
        "username": "6015995055905023",
        "password": "7dA84LCrGq",
    },
    "omni": {
        "email": "la@loyaltyangels.com",
        "password": "UgL88sd9ZG",
    },
    "papa_johns": {
        "email": "chris.gormley2@me.com",
        "password": "ROHansbrics9!",
    },
    "bonus-club": {
        "email": "chris.gormley2@me.com",
        "password": "DSHansbrics10",
    },
    "love-your-body": {
        "email": "chris.gormley2@me.com",
        "password": "OSHansbrics11",
    },
    "recognition-reward-card": {
        "email": "chris.gormley2@gmail.com",
        "password": "QGHansbric13",
    },
    "gbk-rewards": {
        "email": "chris.gormley2@me.com",
        "pin": "9876",
    },
    "pureHMV": {
        "email": "chris.gormley2@me.com",
        "password": "UOHansbrics7",
    },
    "marriott": {
        "email": "chris.gormley2@me.com",
        "password": "Password123",
    },
    "hilton-honors": {
        "username": "591806745",
        "password": "MGHansbrics6"
    },
    "food-cellar": {
        "barcode": "7JQv4LGHwz",
        "scheme_identifier": "-fdK4i",
    }
}


def encrypt(scheme_slug):
    """For testing encryption"""
    aes = AESCipher(AES_KEY.encode())

    return aes.encrypt(json.dumps(CREDENTIALS[scheme_slug])).decode()
