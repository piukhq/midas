import json
import arrow
from decimal import Decimal
from datetime import datetime


class JsonEncoder(json.JSONEncoder):
    def default(self, obj):
        date_format = 'YYYY-MM-DD HH:mm:ssZZ'

        if isinstance(obj, arrow.Arrow):
            return obj.format(date_format)

        if isinstance(obj, datetime):
            return arrow.get(obj).format(date_format)

        if isinstance(obj, Decimal):
            return float(obj)

        return json.JSONEncoder.default(self, obj)
