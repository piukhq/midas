from voluptuous import Schema, Required, Optional
from arrow.arrow import Arrow
from decimal import Decimal


transactions = Schema([{
    Required('date'): Arrow,
    Required('title'): str,
    Required('points'): Decimal,
    Required('value'): Decimal,
    Required('hash'): str,
}])

balance = Schema({
    Required('amount'): Decimal,
    Optional('value'): Decimal,
})

credentials = Schema({
    Required('user_name'): str,
    Required('password'): str,
    Optional('card_number'): str,
})