import arrow
from decimal import Decimal


USER_STORE = {
    "000000": {
        "len_transactions": 0,
        "credentials": {
            "email": "zero@testbink.com",
            "password": "Password01",
            "last_name": "zero",
            "postcode": "rg0 0aa",
            "date_of_birth": "2000-01-01",
        },
        "points": Decimal("0"),
    },
    "111111": {
        "len_transactions": 1,
        "credentials": {
            "email": "one@testbink.com",
            "password": "Password01",
            "last_name": "one",
            "postcode": "rg1 1aa",
            "date_of_birth": "2000-01-01",
        },
        "points": Decimal("20.10"),
    },
    "555555": {
        "len_transactions": 5,
        "credentials": {
            "email": "five@testbink.com",
            "password": "Password01",
            "last_name": "five",
            "postcode": "rg5 5aa",
            "date_of_birth": "2000-01-01",
        },
        "points": Decimal("380.01"),
    },
    "654321": {
        "len_transactions": 1,
        "credentials": {
            "email": "onetransaction@testbink.com",
            "password": "Password01",
            "last_name": "six",
            "postcode": "rg6 6bb",
            "date_of_birth": "2000-01-01",
        },
        "points": Decimal("0"),
    },
    "666666": {
        "len_transactions": 6,
        "credentials": {
            "email": "six@testbink.com",
            "password": "Password01",
            "last_name": "six",
            "postcode": "rg6 6aa",
            "date_of_birth": "2000-01-01",
        },
        "points": Decimal("1480"),
    },
    "123456": {
        "len_transactions": 6,
        "credentials": {
            "email": "sixdigitpoints@testbink.com",
            "password": "pa$$w&rd01!",
            "last_name": "million",
            "postcode": "mp6 0bb",
            "date_of_birth": "2000-01-01",
        },
        "points": Decimal("123456"),
    },
    "234567": {
        "len_transactions": 6,
        "credentials": {
            "email": "sevendigitpoints@testbink.com",
            "password": "Password01",
            "last_name": "smith-s",
            "postcode": "mp7 1bb",
            "date_of_birth": "2000-01-01",
        },
        "points": Decimal(1234567),
    },
    # QA Automated Test Fixtures
    "222220": {
        "len_transactions": 0,
        "credentials": {
            "email": "auto_zero@testbink.com",
            "password": "Password01",
            "last_name": "qa",
            "postcode": "qa1 1qa",
            "date_of_birth": "2000-01-01",
        },
        "points": Decimal("0"),
    },
    "222225": {
        "len_transactions": 5,
        "credentials": {
            "email": "auto_five@testbink.com",
            "password": "Password01",
            "last_name": "qa",
            "postcode": "qa1 1qa",
            "date_of_birth": "2000-01-01",
        },
        "points": Decimal("380.01"),
    },
    # Greppy Test Users
    "500001": {
        "len_transactions": 0,
        "credentials": {
            "email": "greppyuser0@testbink.com",
            "password": "GreppyPass0",
            "last_name": "zero",
            "postcode": "rg0 0aa",
            "date_of_birth": "2000-01-01",
        },
        "points": Decimal("0"),
    },
    "500002": {
        "len_transactions": 1,
        "credentials": {
            "email": "greppyuser1@testbink.com",
            "password": "GreppyPass1",
            "last_name": "one",
            "postcode": "rg1 1aa",
            "date_of_birth": "2000-01-01",
        },
        "points": Decimal("1"),
    },
    "500003": {
        "len_transactions": 3,
        "credentials": {
            "email": "greppyuser205@testbink.com",
            "password": "GreppyPass205",
            "last_name": "hundred",
            "postcode": "rg2 2aa",
            "date_of_birth": "2000-01-01",
        },
        "points": Decimal("205.02"),
    },
    "500004": {
        "len_transactions": 6,
        "credentials": {
            "email": "greppyuser1234567@testbink.com",
            "password": "GreppyPass1234567",
            "last_name": "million",
            "postcode": "rg6 6aa",
            "date_of_birth": "2000-01-01",
        },
        "points": Decimal("1234567.89"),
    },
    # NEW FIXTURES
    "900001": {
        "len_transactions": 0,
        "credentials": {
            "email": "perfuser01@testbink.com",
            "password": "Password01",
            "last_name": "perfuser01",
            "postcode": "rg0 0aa",
            "date_of_birth": "2000-01-01",
        },
        "points": Decimal("0"),
    },
    "900002": {
        "len_transactions": 5,
        "credentials": {
            "email": "perfuser02@testbink.com",
            "password": "Password02",
            "last_name": "perfuser02",
            "postcode": "rg5 5aa",
            "date_of_birth": "2000-01-01",
        },
        "points": Decimal("380.01"),
    },
    "900003": {
        "len_transactions": 5,
        "credentials": {
            "email": "perfuser03@testbink.com",
            "password": "Password03",
            "last_name": "perfuser03",
            "postcode": "mp6 0bb",
            "date_of_birth": "2000-01-01",
        },
        "points": Decimal("123456"),
    },
    "900004": {
        "len_transactions": 5,
        "credentials": {
            "email": "perfuser04@testbink.com",
            "password": "Password04",
            "last_name": "perfuser04",
            "postcode": "mp7 1bb",
            "date_of_birth": "2000-01-01",
        },
        "points": Decimal("1234567"),
    },
    "900005": {
        "len_transactions": 0,
        "credentials": {
            "email": "perfuser05@testbink.com",
            "password": "Password05",
            "last_name": "perfuser05",
            "postcode": "rg0 0aa",
            "date_of_birth": "2000-01-01",
        },
        "points": Decimal("0"),
    },
    "900006": {
        "len_transactions": 1,
        "credentials": {
            "email": "perfuser06@testbink.com",
            "password": "Password06",
            "last_name": "perfuser06",
            "postcode": "rg1 1aa",
            "date_of_birth": "2000-01-01",
        },
        "points": Decimal("20.10"),
    },
    "900007": {
        "len_transactions": 5,
        "credentials": {
            "email": "perfuser07@testbink.com",
            "password": "Password07",
            "last_name": "perfuser07",
            "postcode": "rg5 5aa",
            "date_of_birth": "2000-01-01",
        },
        "points": Decimal("380.01"),
    },
    "900008": {
        "len_transactions": 0,
        "credentials": {
            "email": "perfuser08@testbink.com",
            "password": "Password08",
            "last_name": "perfuser08",
            "postcode": "rg0 0aa",
            "date_of_birth": "2000-01-01",
        },
        "points": Decimal("0"),
    },
    "900009": {
        "len_transactions": 5,
        "credentials": {
            "email": "perfuser09@testbink.com",
            "password": "Password09",
            "last_name": "perfuser09",
            "postcode": "rg5 5aa",
            "date_of_birth": "2000-01-01",
        },
        "points": Decimal("380.01"),
    },
    "900010": {
        "len_transactions": 1,
        "credentials": {
            "email": "perfuser10@testbink.com",
            "password": "Password10",
            "last_name": "perfuser10",
            "postcode": "mp6 0bb",
            "date_of_birth": "2000-01-01",
        },
        "points": Decimal("20.10"),
    },
    "900011": {
        "len_transactions": 6,
        "credentials": {
            "email": "perfuser11@testbink.com",
            "password": "Password11",
            "last_name": "perfuser11",
            "postcode": "mp7 1bb",
            "date_of_birth": "2000-01-01",
        },
        "points": Decimal("1234567"),
    },
    "900012": {
        "len_transactions": 0,
        "credentials": {
            "email": "perfuser12@testbink.com",
            "password": "Password12",
            "last_name": "perfuser12",
            "postcode": "rg0 0aa",
            "date_of_birth": "2000-01-01",
        },
        "points": Decimal("0"),
    },
    "900013": {
        "len_transactions": 1,
        "credentials": {
            "email": "perfuser13@testbink.com",
            "password": "Password13",
            "last_name": "perfuser13",
            "postcode": "rg1 1aa",
            "date_of_birth": "2000-01-01",
        },
        "points": Decimal("20.10"),
    },
    "900014": {
        "len_transactions": 5,
        "credentials": {
            "email": "perfuser14@testbink.com",
            "password": "Password14",
            "last_name": "perfuser14",
            "postcode": "rg5 5aa",
            "date_of_birth": "2000-01-01",
        },
        "points": Decimal("380.01"),
    },
    "900015": {
        "len_transactions": 0,
        "credentials": {
            "email": "perfuser15@testbink.com",
            "password": "Password15",
            "last_name": "perfuser15",
            "postcode": "rg0 0aa",
            "date_of_birth": "2000-01-01",
        },
        "points": Decimal("0"),
    },
    "900016": {
        "len_transactions": 5,
        "credentials": {
            "email": "perfuser16@testbink.com",
            "password": "Password16",
            "last_name": "perfuser16",
            "postcode": "rg5 5aa",
            "date_of_birth": "2000-01-01",
        },
        "points": Decimal("380.01"),
    },
    "900017": {
        "len_transactions": 6,
        "credentials": {
            "email": "perfuser17@testbink.com",
            "password": "Password17",
            "last_name": "perfuser17",
            "postcode": "rg1 1aa",
            "date_of_birth": "2000-01-01",
        },
        "points": Decimal("123456"),
    },
    "900018": {
        "len_transactions": 2,
        "credentials": {"email": "passtest1@testbink.com", "password": r"/!£Password1"},
        "points": Decimal("123456"),
    },
    "900019": {
        "len_transactions": 3,
        "credentials": {"email": "passtest2@testbink.com", "password": r"Password1?£$"},
        "points": Decimal("123456"),
    },
    "900020": {
        "len_transactions": 1,
        "credentials": {"email": "passtest3@testbink.com", "password": r"<!-=]{"},
        "points": Decimal("123456"),
    },
    "900021": {
        "len_transactions": 2,
        "credentials": {"email": "passtest4@testbink.com", "password": r"Pass word1"},
        "points": Decimal("123456"),
    },
    "900022": {
        "len_transactions": 3,
        "credentials": {"email": "passtest5@testbink.com", "password": r"Pass'wo'rd1"},
        "points": Decimal("123456"),
    },
    "900023": {
        "len_transactions": 2,
        "credentials": {"email": "passtest6@testbink.com", "password": r'Pa"ssw"ord1'},
        "points": Decimal("123456"),
    },
    "900024": {
        "len_transactions": 1,
        "credentials": {"email": "passtest7@testbink.com", "password": r"Pass@word1"},
        "points": Decimal("123456"),
    },
    "900025": {
        "len_transactions": 2,
        "credentials": {"email": "passtest8@testbink.com", "password": r"Pass_word1"},
        "points": Decimal("123456"),
    },
    "900026": {
        "len_transactions": 2,
        "credentials": {"email": "passtest9@testbink.com", "password": r"Pa*()ss"},
        "points": Decimal("123456"),
    },
    "900027": {
        "len_transactions": 3,
        "credentials": {"email": "passtest10@testbink.com", "password": r"Pas\s\word1"},
        "points": Decimal("123456"),
    },
    "900028": {
        "len_transactions": 4,
        "credentials": {"email": "passtest11@testbink.com", "password": r"Pa$££€ss"},
        "points": Decimal("123456"),
    },
    "999000": {
        "len_transactions": 2,
        "credentials": {
            "email": "slow@testbink.com",
            "password": "Slowpass01",
            "last_name": "slow",
            "postcode": "sl1 1ow",
            "date_of_birth": "2000-01-01",
        },
        "points": Decimal("300"),
    },
    "911111": {
        "len_transactions": 5,
        "credentials": {
            "email": "special!#$%&'char1@testbink.com",
            "password": "Password01",
            "last_name": "five",
            "postcode": "rg5 5aa",
            "date_of_birth": "2000-01-01",
        },
        "points": Decimal("380.01"),
    },
    "922222": {
        "len_transactions": 3,
        "credentials": {
            "email": "special*+-/=?^char2@testbink.com",
            "password": "Password01",
            "last_name": "five",
            "postcode": "rg5 5aa",
            "date_of_birth": "2000-01-01",
        },
        "points": Decimal("380.01"),
    },
    "933333": {
        "len_transactions": 4,
        "credentials": {
            "email": "special_`{|}~char3@testbink.com",
            "password": "Password01",
            "last_name": "five",
            "postcode": "rg5 5aa",
            "date_of_birth": "2000-01-01",
        },
        "points": Decimal("380.01"),
    },
    # MER-349
    "934918": {
        "len_transactions": 0,
        "credentials": {
            "last_name": "testusereighteen",
            "postcode": "rg0 0aa",
        },
        "points": Decimal("0.00"),
    },
    "934919": {
        "len_transactions": 5,
        "credentials": {
            "last_name": "testusernineteen",
            "postcode": "rg5 5aa",
        },
        "points": Decimal("380.01"),
    },
    "934920": {
        "len_transactions": 5,
        "credentials": {
            "last_name": "testusertwenty",
            "postcode": "mp6 0bb",
        },
        "points": Decimal("123456"),
    },
    "934921": {
        "len_transactions": 5,
        "credentials": {
            "last_name": "testusertwentyone",
            "postcode": "mp7 1bb",
        },
        "points": Decimal("1234567"),
    },
    "934922": {
        "len_transactions": 0,
        "credentials": {
            "last_name": "testusertwentytwo",
            "postcode": "rg0 0aa",
        },
        "points": Decimal("0.00"),
    },
    "934923": {
        "len_transactions": 1,
        "credentials": {
            "last_name": "testusertwentythree",
            "postcode": "rg1 1aa",
        },
        "points": Decimal("20.10"),
    },
    "934924": {
        "len_transactions": 5,
        "credentials": {
            "last_name": "testusertwentyfour",
            "postcode": "rg5 5aa",
        },
        "points": Decimal("380.01"),
    },
    "934925": {
        "len_transactions": 0,
        "credentials": {
            "last_name": "testusertwentyfive",
            "postcode": "rg0 0aa",
        },
        "points": Decimal("0.00"),
    },
    "934926": {
        "len_transactions": 5,
        "credentials": {
            "last_name": "testusertwentysix",
            "postcode": "rg5 5aa",
        },
        "points": Decimal("380.01"),
    },
    "934927": {
        "len_transactions": 1,
        "credentials": {
            "last_name": "testusertwentyseven",
            "postcode": "mp6 0bb",
        },
        "points": Decimal("20.10"),
    },
}

transactions = [
    {
        "date": arrow.get("01/07/2018 14:24:15", "DD/MM/YYYY HH:mm:ss"),
        "description": "Test transaction: 1 item",
        "points": Decimal("20.71"),
    },
    {
        "date": arrow.get("02/08/2018 12:11:30", "DD/MM/YYYY HH:mm:ss"),
        "description": "Test transaction: 3 items",
        "points": Decimal("-100.01"),
    },
    {
        "date": arrow.get("03/09/2018 22:05:45", "DD/MM/YYYY HH:mm:ss"),
        "description": "Test transaction: 5 items",
        "points": Decimal("200"),
    },
    {
        "date": arrow.get("04/09/2018 16:55:00", "DD/MM/YYYY HH:mm:ss"),
        "description": "Test transaction: 2 items",
        "points": Decimal("-50"),
    },
    {
        "date": arrow.get("04/09/2018 07:35:10", "DD/MM/YYYY HH:mm:ss"),
        "description": "Test transaction: 1 item",
        "points": Decimal("10"),
    },
    {
        "date": arrow.get("05/09/2018 11:30:50", "DD/MM/YYYY HH:mm:ss"),
        "description": "Test transaction: 20 items",
        "points": Decimal("1100"),
    },
]
