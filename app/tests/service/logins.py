from app.encryption import AESCipher
from settings import AES_KEY
import json

CREDENTIALS = {
    "tesco-clubcard": {
        'email': 'julie.gormley100@gmail.com',
        'password': 'NSHansbrics5',
        'barcode': '9794024051328070'
    },
    "avios": {
        'email': 'chris.smith4@gmx.co.uk',
        'password': 'Loyalty1',
    },
    "avios_api": {
        'card_number': '3081471018143650',
        'date_of_birth': '11/03/1985',
        'last_name': 'AEAKPN',
    },
    "british-airways": {
        'username': "49932498",
        'password': 'Loyalty1'
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
        'username': 'chris.gormley2@me.com',
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
        'postcode': 'BH23 1HT',
        'place_of_birth': "cheltenham",
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
    "debenhams": {
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
        "email": "la@loyaltyangels.com",
        "password": "LAngels2015",
    },
    "qantas": {
        "card_number": "1925645176",
        "last_name": "angels",
        "pin": "1290",
    },
    "the_perfume_shop": {
        "email": "la@loyaltyangels.com",
        "password": "LAngels2015!",
    },
    "rewards4fishing": {
        "email": "la@loyaltyangels.com",
        "password": "LAngels2015!",
    },
    "rewards4golf": {
        "email": "la@loyaltyangels.com",
        "password": "LAngels2015!",
    },
    "rewards4racing": {
        "email": "la@loyaltyangels.com",
        "password": "LAngels2015!",
    },
    "space_nk": {
        "barcode": "63385283721106029252",
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
        "password": "LAngels2015!",
    },
    "sparks": {
        "email": "chris.smith4@gmx.co.uk",
        "password": "Loyalty1",
    },
    "virgin": {
        "username": "gormleyc",
        "password": "MUHansb6",
    },
    "ihg": {
        "username": "la@loyaltyangels.com",
        "pin": "1290",
    },
    "hyatt": {
        "username": "528180109F",
        "password": "Bagshot1",
    },
    "holland_and_barrett": {
        "email": "chris.gormley2@me.com",
        "password": "SGHansbr17",
    },
    "starwood-preferred-guest": {
        "username": "la@loyaltyangels.com",
        "password": "Loyalty1",
        "favourite_place": "bagshot",
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
        "card_number": "MH315377635",
        "password": "Loyalty1",
    },
    "royal-orchid-plus": {
        "username": "NX31265",
        "password": "Loyalty1",
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
        "password": "Loyalty1",
    },
    "priority-guest-rewards": {
        "username": "R2103483",
        "password": "Loyalty1",
    },
    "delta-skymiles": {
        "username": "9118431866",
        "password": "Loyalty1",
    },
    "klm-flying-blue": {
        "username": "1109882571",
        "pin": "1234",
    },
    "le-club": {
        "username": "3081031370906043",
        "password": "Loyalty1",
    },
    "choicehotels": {
        "username": "LoyaltyAngels",
        "password": "Loyalty1",
    },
    "discovery": {
        "username": "LoyaltyAngels",
        "password": "Loyalty1",
    },
    "clubcarlson": {
        "username": "6015995055905023",
        "password": "Loyalty1!",
    },
    "omni": {
        "email": "la@loyaltyangels.com",
        "password": "Loyalty1",
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
        "email": "Dkmudway@gmail.com",
        "password": "Loyalty2016",
    },
    "recognition-reward-card": {
        "email": "chris.gormley2@gmail.com",
        "password": "QGHansbric13",
    },
    "gbk-rewards": {
        "email": "chris.gormley2@me.com",
        "pin": "9876",
    },
}


def encrypt(scheme_slug):
    """For testing encryption"""
    aes = AESCipher(AES_KEY.encode())

    return aes.encrypt(json.dumps(CREDENTIALS[scheme_slug])).decode()
