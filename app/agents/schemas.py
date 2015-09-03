from voluptuous import Schema, Required, Optional
from arrow.arrow import Arrow
from decimal import Decimal


transactions = Schema([{
    Required('date'): Arrow,
    Required('title'): str,
    Required('points'): Decimal,
    Optional('value'): Decimal,
    Optional('location'): str,
    Required('hash'): str,
}])

balance = Schema({
    Required('amount'): Decimal,
    Optional('value'): Decimal,
    Optional('voucher_value'): Decimal,  # This is a Tesco only field
})

credentials = Schema({
    Required('user_name'): str,
    Required('password'): str,
    Optional('card_number'): str,
})
