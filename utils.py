"""Various utilities not related to parsing per se."""

import datetime
import json
import re
import dateutil.parser


class BasicEqualityMixin:
    """Mixin to facilitate implementing the equality operator

    Subclasses of this will test for equality by checking the type, then
    comparing the attributes dictionary.
    """

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.__dict__ == other.__dict__


class DatetimeJSONEncoder(json.JSONEncoder):
    """JSON encoder that can handle datetime objects.

    The datetime will be encoded as a string, in ISO format.
    """

    def default(self, o):
        if isinstance(o, datetime.datetime):
            return o.isoformat()
        else:
            return json.JSONEncoder.default(self, o)


def clean_text(text):
    """Clean text by removing extra whitespace and normalizing."""
    # Remove leading/trailing whitespace and normalize internal whitespace
    return re.sub(r'\s+', ' ', text.strip())


def parse_date(date_string):
    """Parse a date string into a datetime object."""
    return dateutil.parser.parse(date_string)
