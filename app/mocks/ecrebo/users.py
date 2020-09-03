from decimal import Decimal
from app.agents.exceptions import (
    STATUS_LOGIN_FAILED,
    NO_SUCH_RECORD,
    ACCOUNT_ALREADY_EXISTS,
    CARD_NOT_REGISTERED,
    GENERAL_ERROR,
    JOIN_IN_PROGRESS,
    VALIDATION,
    UnauthorisedError,
    STATUS_REGISTRATION_FAILED,
    PASSWORD_EXPIRED,
)

USER_STORE = {
    "whsmith": {
        "0000001": {
            "card_number": "WHS00000000000001",
            "points": Decimal("0"),
            "credentials": {},
            "earned_vouchers": [],
            "expired_vouchers": [],
            "redeemed_vouchers": [],
        },
        "9523456": {
            "card_number": "WHS00000009523457",
            "points": Decimal("3"),
            "credentials": {},
            "earned_vouchers": [
                ["WHS000046", "2021-01-01"],
                ["WHS000047", "2021-02-02"],
            ],
            "expired_vouchers": [["WHS000048", "2020-08-01"], ],
            "redeemed_vouchers": [
                ["WHS000049", "2020-08-04"],
                ["WHS000050", "2020-07-04"],
                ["WHS000051", "2020-06-04"],
            ],
        },
        "9523457": {
            "card_number": "WHS00000009523457",
            "points": Decimal("3"),
            "credentials": {},
            "earned_vouchers": [
                ["WHS000052", "2021-01-01"],
                ["WHS000053", "2021-02-02"],
            ],
            "expired_vouchers": [
                ["WHS000054", "2020-08-01"],
                ["WHS000055", "2020-07-25"],
            ],
            "redeemed_vouchers": [
                ["WHS000056", "2020-08-04"],
                ["WHS000057", "2020-07-04"],
            ],
        },
        "9523458": {
            "card_number": "WHS00000009523458",
            "points": Decimal("2"),
            "credentials": {},
            "earned_vouchers": [["WHS000058", "2021-01-01"], ],
            "expired_vouchers": [
                ["WHS000059", "2020-08-01"],
                ["WHS000060", "2020-07-25"],
                ["WHS000061", "2020-06-12"],
            ],
            "redeemed_vouchers": [
                ["WHS000062", "2020-08-04"],
                ["WHS000063", "2020-07-04"],
            ],
        },
        "9523459": {
            "card_number": "WHS00000009523459",
            "points": Decimal("0"),
            "credentials": {},
            "earned_vouchers": [],
            "expired_vouchers": [["WHS000064", "2020-08-01"], ],
            "redeemed_vouchers": [],
        },
        "9523460": {
            "card_number": "WHS00000009523460",
            "points": Decimal("3"),
            "credentials": {},
            "earned_vouchers": [
                ["WHS000065", "2021-01-01"],
                ["WHS000066", "2021-02-02"],
            ],
            "expired_vouchers": [],
            "redeemed_vouchers": [
                ["WHS000067", "2020-08-04"],
                ["WHS000068", "2020-07-04"],
                ["WHS000069", "2020-06-04"],
            ],
        },
        "9523461": {
            "card_number": "WHS00000009523461",
            "points": Decimal("2"),
            "credentials": {},
            "earned_vouchers": [
                ["WHS000070", "2021-01-01"],
                ["WHS000071", "2021-02-02"],
                ["WHS000072", "2021-03-03"],
            ],
            "expired_vouchers": [
                ["WHS000073", "2020-08-01"],
                ["WHS000074", "2020-07-25"],
                ["WHS000075", "2020-06-12"],
            ],
            "redeemed_vouchers": [["WHS000076", "2020-08-04"], ],
        },
        "9523462": {
            "card_number": "WHS00000009523462",
            "points": Decimal("2"),
            "credentials": {},
            "earned_vouchers": [["WHS000077", "2021-01-01"], ],
            "expired_vouchers": [["WHS000078", "2020-08-01"], ],
            "redeemed_vouchers": [["WHS000079", "2020-08-04"], ],
        },
        "9523463": {
            "card_number": "WHS00000009523463",
            "points": Decimal("0"),
            "credentials": {},
            "earned_vouchers": [
                ["WHS000080", "2021-01-01"],
                ["WHS000081", "2021-02-02"],
            ],
            "expired_vouchers": [["WHS000082", "2020-08-01"], ],
            "redeemed_vouchers": [
                ["WHS000083", "2020-08-04"],
                ["WHS000084", "2020-07-04"],
                ["WHS000085", "2020-06-04"],
            ],
        },
        "9523464": {
            "card_number": "WHS00000009523464",
            "points": Decimal("2"),
            "credentials": {},
            "earned_vouchers": [
                ["WHS000086", "2021-01-01"],
                ["WHS000087", "2021-02-02"],
            ],
            "expired_vouchers": [["WHS000088", "2020-08-01"], ],
            "redeemed_vouchers": [
                ["WHS000089", "2020-08-04"],
                ["WHS000090", "2020-07-04"],
            ],
        },
        "9523465": {
            "card_number": "WHS00000009523465",
            "points": Decimal("2"),
            "credentials": {},
            "earned_vouchers": [
                ["WHS000091", "2021-01-01"],
                ["WHS000092", "2021-02-02"],
                ["WHS000093", "2021-03-03"],
            ],
            "expired_vouchers": [
                ["WHS000094", "2020-08-01"],
                ["WHS000095", "2020-07-25"],
            ],
            "redeemed_vouchers": [["WHS000096", "2020-08-04"], ],
        },
        "9523466": {
            "card_number": "WHS00000009523466",
            "points": Decimal("3"),
            "credentials": {},
            "earned_vouchers": [["WHS000097", "2021-01-01"], ],
            "expired_vouchers": [],
            "redeemed_vouchers": [
                ["WHS000098", "2020-08-04"],
                ["WHS000099", "2020-07-04"],
            ],
        },
        "9523467": {
            "card_number": "WHS00000009523467",
            "points": Decimal("1"),
            "credentials": {},
            "earned_vouchers": [["WHS000100", "2021-01-01"], ],
            "expired_vouchers": [],
            "redeemed_vouchers": [
                ["WHS000101", "2020-08-04"],
                ["WHS000102", "2020-07-04"],
            ],
        },
        "9523468": {
            "card_number": "WHS00000009523468",
            "points": Decimal("1"),
            "credentials": {},
            "earned_vouchers": [["WHS000103", "2021-01-01"], ],
            "expired_vouchers": [],
            "redeemed_vouchers": [],
        },
        "9523469": {
            "card_number": "WHS00000009523469",
            "points": Decimal("4"),
            "credentials": {},
            "earned_vouchers": [
                ["WHS000104", "2021-01-01"],
                ["WHS000105", "2021-02-02"],
            ],
            "expired_vouchers": [["WHS000106", "2020-08-01"], ],
            "redeemed_vouchers": [
                ["WHS000107", "2020-08-04"],
                ["WHS000108", "2020-07-04"],
            ],
        },
        "9523470": {
            "card_number": "WHS00000009523470",
            "points": Decimal("1"),
            "credentials": {},
            "earned_vouchers": [],
            "expired_vouchers": [
                ["WHS000109", "2020-08-01"],
                ["WHS000110", "2020-07-25"],
                ["WHS000111", "2020-06-12"],
            ],
            "redeemed_vouchers": [
                ["WHS000112", "2020-08-04"],
                ["WHS000113", "2020-07-04"],
                ["WHS000114", "2020-06-04"],
            ],
        },
        "9523471": {
            "card_number": "WHS00000009523471",
            "points": Decimal("0"),
            "credentials": {},
            "earned_vouchers": [],
            "expired_vouchers": [["WHS000115", "2020-08-01"], ["WHS000116", ""], ],
            "redeemed_vouchers": [["WHS000117", "2020-08-04"], ],
        },
        "9523472": {
            "card_number": "WHS00000009523472",
            "points": Decimal("3"),
            "credentials": {},
            "earned_vouchers": [
                ["WHS000118", "2021-01-01"],
                ["WHS000119", "2021-02-02"],
                ["WHS000120", "2021-03-03"],
            ],
            "expired_vouchers": [],
            "redeemed_vouchers": [["WHS000121", "2020-08-04"], ],
        },
        "9523473": {
            "card_number": "WHS00000009523473",
            "points": Decimal("1"),
            "credentials": {},
            "earned_vouchers": [
                ["WHS000122", "2021-01-01"],
                ["WHS000123", "2021-02-02"],
                ["WHS000124", "2021-03-03"],
            ],
            "expired_vouchers": [["WHS000125", "2020-08-01"], ],
            "redeemed_vouchers": [
                ["WHS000126", "2020-08-04"],
                ["WHS000127", "2020-07-04"],
            ],
        },
        "9523474": {
            "card_number": "WHS00000009523474",
            "points": Decimal("3"),
            "credentials": {},
            "earned_vouchers": [["WHS000128", "2021-01-01"], ],
            "expired_vouchers": [
                ["WHS000129", "2020-08-01"],
                ["WHS000130", "2020-07-25"],
            ],
            "redeemed_vouchers": [
                ["WHS000131", "2020-08-04"],
                ["WHS000132", "2020-07-04"],
            ],
        },
        "9523475": {
            "card_number": "WHS00000009523475",
            "points": Decimal("1"),
            "credentials": {},
            "earned_vouchers": [],
            "expired_vouchers": [
                ["WHS000133", "2020-08-01"],
                ["WHS000134", "2020-07-25"],
            ],
            "redeemed_vouchers": [
                ["WHS000135", "2020-08-04"],
                ["WHS000136", "2020-07-04"],
            ],
        },
        "9523476": {
            "card_number": "WHS00000009523476",
            "points": Decimal("3"),
            "credentials": {},
            "earned_vouchers": [["WHS000137", "2021-01-01"], ],
            "expired_vouchers": [["WHS000138", "2020-08-01"], ],
            "redeemed_vouchers": [["WHS000139", "2020-08-04"], ],
        },
        "9523477": {
            "card_number": "WHS00000009523477",
            "points": Decimal("3"),
            "credentials": {},
            "earned_vouchers": [
                ["WHS000140", "2021-01-01"],
                ["WHS000141", "2021-02-02"],
            ],
            "expired_vouchers": [],
            "redeemed_vouchers": [["WHS000142", "2020-08-04"], ],
        },
        "9523478": {
            "card_number": "WHS00000009523478",
            "points": Decimal("1"),
            "credentials": {},
            "earned_vouchers": [
                ["WHS000143", "2021-01-01"],
                ["WHS000144", "2021-02-02"],
            ],
            "expired_vouchers": [],
            "redeemed_vouchers": [
                ["WHS000145", "2020-08-04"],
                ["WHS000146", "2020-07-04"],
            ],
        },
        "9523479": {
            "card_number": "WHS00000009523479",
            "points": Decimal("3"),
            "credentials": {},
            "earned_vouchers": [["WHS000147", "2021-01-01"], ],
            "expired_vouchers": [["WHS000148", "2020-08-01"], ],
            "redeemed_vouchers": [
                ["WHS000149", "2020-08-04"],
                ["WHS000150", "2020-07-04"],
                ["WHS000151", "2020-06-04"],
            ],
        },
        "9523480": {
            "card_number": "WHS00000009523480",
            "points": Decimal("0"),
            "credentials": {},
            "earned_vouchers": [
                ["WHS000152", "2021-01-01"],
                ["WHS000153", "2021-02-02"],
            ],
            "expired_vouchers": [],
            "redeemed_vouchers": [["WHS000154", "2020-08-04"], ],
        },
        "9523481": {
            "card_number": "WHS00000009523481",
            "points": Decimal("2"),
            "credentials": {},
            "earned_vouchers": [],
            "expired_vouchers": [["WHS000155", "2020-08-01"], ],
            "redeemed_vouchers": [
                ["WHS000156", "2020-08-04"],
                ["WHS000157", "2020-07-04"],
            ],
        },
        "9523482": {
            "card_number": "WHS00000009523482",
            "points": Decimal("0"),
            "credentials": {},
            "earned_vouchers": [
                ["WHS000158", "2021-01-01"],
                ["WHS000159", "2021-02-02"],
                ["WHS000160", "2021-03-03"],
            ],
            "expired_vouchers": [["WHS000161", "2020-08-01"], ],
            "redeemed_vouchers": [
                ["WHS000162", "2020-08-04"],
                ["WHS000163", "2020-07-04"],
                ["WHS000164", "2020-06-04"],
            ],
        },
        "9523483": {
            "card_number": "WHS00000009523483",
            "points": Decimal("3"),
            "credentials": {},
            "earned_vouchers": [],
            "expired_vouchers": [
                ["WHS000165", "2020-08-01"],
                ["WHS000166", "2020-07-25"],
            ],
            "redeemed_vouchers": [["0", ""], ],
        },
        "9523484": {
            "card_number": "WHS00000009523484",
            "points": Decimal("3"),
            "credentials": {},
            "earned_vouchers": [
                ["WHS000167", "2021-01-01"],
                ["WHS000168", "2021-02-02"],
            ],
            "expired_vouchers": [["WHS000169", "2020-08-01"], ],
            "redeemed_vouchers": [
                ["WHS000170", "2020-08-04"],
                ["WHS000171", "2020-07-04"],
                ["WHS000172", "2020-06-04"],
            ],
        },
        "9523485": {
            "card_number": "WHS00000009523485",
            "points": Decimal("1"),
            "credentials": {},
            "earned_vouchers": [],
            "expired_vouchers": [
                ["WHS000173", "2020-08-01"],
                ["WHS000174", "2020-07-25"],
                ["WHS000175", "2020-06-12"],
            ],
            "redeemed_vouchers": [["WHS000176", "2020-08-04"], ],
        },
        "9523486": {
            "card_number": "WHS00000009523486",
            "points": Decimal("0"),
            "credentials": {},
            "earned_vouchers": [["WHS000177", "2021-01-01"], ],
            "expired_vouchers": [
                ["WHS000178", "2020-08-01"],
                ["WHS000179", "2020-07-25"],
            ],
            "redeemed_vouchers": [
                ["WHS000180", "2020-08-04"],
                ["WHS000181", "2020-07-04"],
                ["WHS000182", "2020-06-04"],
            ],
        },
        "9523487": {
            "card_number": "WHS00000009523487",
            "points": Decimal("3"),
            "credentials": {},
            "earned_vouchers": [],
            "expired_vouchers": [
                ["WHS000183", "2020-08-01"],
                ["WHS000184", "2020-07-25"],
            ],
            "redeemed_vouchers": [
                ["WHS000185", "2020-08-04"],
                ["WHS000186", "2020-07-04"],
                ["WHS000187", "2020-06-04"],
            ],
        },
        "9523488": {
            "card_number": "WHS00000009523488",
            "points": Decimal("4"),
            "credentials": {},
            "earned_vouchers": [
                ["WHS000188", "2021-01-01"],
                ["WHS000189", "2021-02-02"],
            ],
            "expired_vouchers": [
                ["WHS000190", "2020-08-01"],
                ["WHS000191", "2020-07-25"],
            ],
            "redeemed_vouchers": [
                ["WHS000192", "2020-08-04"],
                ["WHS000193", "2020-07-04"],
            ],
        },
        "9523489": {
            "card_number": "WHS00000009523489",
            "points": Decimal("2"),
            "credentials": {},
            "earned_vouchers": [
                ["WHS000194", "2021-01-01"],
                ["WHS000195", "2021-02-02"],
            ],
            "expired_vouchers": [
                ["WHS000196", "2020-08-01"],
                ["WHS000197", "2020-07-25"],
            ],
            "redeemed_vouchers": [],
        },
        "9523490": {
            "card_number": "WHS00000009523490",
            "points": Decimal("3"),
            "credentials": {},
            "earned_vouchers": [["WHS000198", "2021-01-01"], ],
            "expired_vouchers": [],
            "redeemed_vouchers": [],
        },
        "9523491": {
            "card_number": "WHS00000009523491",
            "points": Decimal("3"),
            "credentials": {},
            "earned_vouchers": [["WHS000199", "2021-01-01"], ],
            "expired_vouchers": [],
            "redeemed_vouchers": [],
        },
        "9523492": {
            "card_number": "WHS00000009523492",
            "points": Decimal("0"),
            "credentials": {},
            "earned_vouchers": [
                ["WHS000200", "2021-01-01"],
                ["WHS000201", "2021-02-02"],
                ["WHS000202", "2021-03-03"],
            ],
            "expired_vouchers": [
                ["WHS000203", "2020-08-01"],
                ["WHS000204", "2020-07-25"],
                ["WHS000205", "2020-06-12"],
            ],
            "redeemed_vouchers": [
                ["WHS000206", "2020-08-04"],
                ["WHS000207", "2020-07-04"],
                ["WHS000208", "2020-06-04"],
            ],
        },
        "9523493": {
            "card_number": "WHS00000009523493",
            "points": Decimal("2"),
            "credentials": {},
            "earned_vouchers": [
                ["WHS000209", "2021-01-01"],
                ["WHS000210", "2021-02-02"],
            ],
            "expired_vouchers": [],
            "redeemed_vouchers": [["WHS000211", "2020-08-04"], ],
        },
        "9523494": {
            "card_number": "WHS00000009523494",
            "points": Decimal("3"),
            "credentials": {},
            "earned_vouchers": [],
            "expired_vouchers": [],
            "redeemed_vouchers": [["WHS000212", "2020-08-04"], ],
        },
        "9523495": {
            "card_number": "WHS00000009523495",
            "points": Decimal("4"),
            "credentials": {},
            "earned_vouchers": [],
            "expired_vouchers": [["WHS000213", "2020-08-01"], ],
            "redeemed_vouchers": [],
        },
        "9523496": {
            "card_number": "WHS00000009523496",
            "points": Decimal("1"),
            "credentials": {},
            "earned_vouchers": [
                ["WHS000214", "2021-01-01"],
                ["WHS000215", "2021-02-02"],
                ["WHS000216", "2021-03-03"],
            ],
            "expired_vouchers": [["WHS000217", "2020-08-01"], ],
            "redeemed_vouchers": [
                ["WHS000218", "2020-08-04"],
                ["WHS000219", "2020-07-04"],
            ],
        },
        "9523497": {
            "card_number": "WHS00000009523497",
            "points": Decimal("3"),
            "credentials": {},
            "earned_vouchers": [
                ["WHS000220", "2021-01-01"],
                ["WHS000221", "2021-02-02"],
            ],
            "expired_vouchers": [["WHS000222", "2020-08-01"], ],
            "redeemed_vouchers": [],
        },
        "9523498": {
            "card_number": "WHS00000009523498",
            "points": Decimal("0"),
            "credentials": {},
            "earned_vouchers": [],
            "expired_vouchers": [["WHS000223", "2020-08-01"], ],
            "redeemed_vouchers": [
                ["WHS000224", "2020-08-04"],
                ["WHS000225", "2020-07-04"],
                ["WHS000226", "2020-06-04"],
            ],
        },
        "9523499": {
            "card_number": "WHS00000009523499",
            "points": Decimal("3"),
            "credentials": {},
            "earned_vouchers": [
                ["WHS000227", "2021-01-01"],
                ["WHS000228", "2021-02-02"],
                ["WHS000229", "2021-03-03"],
            ],
            "expired_vouchers": [
                ["WHS000230", "2020-08-01"],
                ["WHS000231", "2020-07-25"],
                ["WHS000232", "2020-06-12"],
            ],
            "redeemed_vouchers": [
                ["WHS000233", "2020-08-04"],
                ["WHS000234", "2020-07-04"],
            ],
        },
        "9523500": {
            "card_number": "WHS00000009523500",
            "points": Decimal("1"),
            "credentials": {},
            "earned_vouchers": [
                ["WHS000235", "2021-01-01"],
                ["WHS000236", "2021-02-02"],
                ["WHS000237", "2021-03-03"],
            ],
            "expired_vouchers": [],
            "redeemed_vouchers": [["WHS000238", "2020-08-04"], ],
        },
        "9523501": {
            "card_number": "WHS00000009523501",
            "points": Decimal("2"),
            "credentials": {},
            "earned_vouchers": [["WHS000239", "2021-01-01"], ],
            "expired_vouchers": [],
            "redeemed_vouchers": [["0", ""], ],
        },
        "9523502": {
            "card_number": "WHS00000009523502",
            "points": Decimal("3"),
            "credentials": {},
            "earned_vouchers": [["WHS000240", "2021-01-01"], ],
            "expired_vouchers": [
                ["WHS000241", "2020-08-01"],
                ["WHS000242", "2020-07-25"],
                ["WHS000243", "2020-06-12"],
            ],
            "redeemed_vouchers": [["WHS000244", "2020-08-04"], ],
        },
        "9523503": {
            "card_number": "WHS00000009523503",
            "points": Decimal("3"),
            "credentials": {},
            "earned_vouchers": [
                ["WHS000245", "2021-01-01"],
                ["WHS000246", "2021-02-02"],
            ],
            "expired_vouchers": [],
            "redeemed_vouchers": [["WHS000247", "2020-08-04"], ],
        },
        "9523504": {
            "card_number": "WHS00000009523504",
            "points": Decimal("1"),
            "credentials": {},
            "earned_vouchers": [],
            "expired_vouchers": [
                ["WHS000248", "2020-08-01"],
                ["WHS000249", "2020-07-25"],
            ],
            "redeemed_vouchers": [["WHS000250", "2020-08-04"], ],
        },
        "9523505": {
            "card_number": "WHS00000009523505",
            "points": Decimal("1"),
            "credentials": {},
            "earned_vouchers": [
                ["WHS000251", "2021-01-01"],
                ["WHS000252", "2021-02-02"],
            ],
            "expired_vouchers": [],
            "redeemed_vouchers": [["WHS000253", "2020-08-04"], ],
        },
        # MER-432: return an exception for certain card numbers
        "9523100": {
            "card_number": "WHS00000009523100",
            "code_to_return": (
                "X100",
                None,
            ),  # Set code to None to force a PENDING state for the card
        },
        "9523101": {
            "card_number": "WHS00000009523101",
            "code_to_return": ("X101", NO_SUCH_RECORD),
        },
        "9523102": {
            "card_number": "WHS00000009523102",
            "code_to_return": ("X102", VALIDATION),
        },
        "9523103": {
            "card_number": "WHS00000009523103",
            "code_to_return": ("X103", UnauthorisedError),
        },
        "9523104": {
            "card_number": "WHS00000009523104",
            "code_to_return": ("X104", GENERAL_ERROR),
        },
        "9523105": {
            "card_number": "WHS00000009523105",
            "code_to_return": ("X105", CARD_NOT_REGISTERED),
        },
        "9523200": {
            "card_number": "WHS00000009523200",
            "code_to_return": ("X200", JOIN_IN_PROGRESS),
        },
        "9523201": {
            "card_number": "WHS00000009523201",
            "code_to_return": ("X201", STATUS_REGISTRATION_FAILED),
        },
        "9523202": {
            "card_number": "WHS00000009523202",
            "code_to_return": ("X202", ACCOUNT_ALREADY_EXISTS),
        },
        "9523303": {
            "card_number": "WHS00000009523303",
            "code_to_return": ("X303", STATUS_LOGIN_FAILED),
        },
        "9523304": {
            "card_number": "WHS00000009523304",
            "code_to_return": ("X304", PASSWORD_EXPIRED),
        },
    }
}
