from voluptuous import Schema, Required
from arrow.arrow import Arrow
from decimal import Decimal


transactions = Schema([{
    Required('date'): Arrow,
    Required('title'): str,
    Required('points'): Decimal,
    Required('hash'): str,
}])

balance = Schema({
    Required('amount'): Decimal,
    'value': Decimal,
})
