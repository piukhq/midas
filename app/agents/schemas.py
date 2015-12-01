from voluptuous import Schema, Required, Optional
from arrow.arrow import Arrow
from decimal import Decimal


transactions = Schema([{
    Required('date'): Arrow,
    Required('description'): str,
    Required('points'): Decimal,
    Optional('value'): Decimal,
    Optional('location'): str,
    Required('hash'): str,
}])

balance = Schema({
    Required('points'): Decimal,
    Required('value'): Decimal,
    Optional('balance'): Decimal,  # This is a Tesco only field
    Required('value_label'): str,
})

credentials = Schema({
    Required('user_name'): str,
    Required('password'): str,
    Optional('card_number'): str,
})
