# Midas API Design

## Overview

The Midas API returns an agents transactions and balances give a users credentials. The service keeps no state apart
from the count of login retry attempts in a redis database to prevent user agent lock out.

## Api endpoints

### Balance

Returns hash map of latest balance values for a user agent

    /<string:agent>/balance?credentials=<credentials>&token=<token>

Example request:

    /tesco/balance?credentials=sdfg78sd879gf798dsfg&token=sdfg78sd879gf798dsfg

Response Schema:
    
    { Required('points'): Decimal,
      Optional('value'): Decimal, }

### Transactions

Returns a list of hash maps of the latest transactions for a users agent.

    /<string:agent>/transactions?credentials=<credentials>&token=<token>

Example request:

    /tesco/transactions?credentials=sdfg78sd879gf798dsfg&token=sdfg78sd879gf798dsfg

Response Schema:

    [{
        Required('date'): Datetime,
        Required('title'): str,
        Required('points'): Decimal,
        Optional('value'): Decimal,
        Required('hash'): str,
    }, ...]

The 'hash' value is a unique row identifier.

### Account Overview

Returns both the agent balance and transactions in the most efficient way for the daily refresh.

    /<string:agent>/account_overview?credentials=<credentials>&token=<token>

Example request:

    /tesco/account_overview?credentials=sdfg78sd879gf798dsfg&token=sdfg78sd879gf798dsfg

Response Schema:

    {"balance": { Required('points'): Decimal,
                  Optional('value'): Decimal, }
                  
     "transactions": [{
                        Required('date'): Datetime,
                        Required('title'): str,
                        Required('points'): Decimal,
                        Optional('value'): Decimal,
                        Required('hash'): str,
                     }, ...]


### Agents

Returns a hash map of supported Agents and the required authentication fields

    /agents?token=<token>

Example response:

    {"tescos": ["user_name", "password", "card_number"], ...}

### Error Reference

Returns a hash map of error names, codes and messages returned by Midas. Where it makes sense we will return the same erros 
as Yodlee https://developer.yodlee.com/FAQs/Error_Codes.

    /error_reference?token=<token>

Example response:

    {"STATUS_LOGIN_FAILED": {"code": 402,
                             "message": "We could not update your account because your username and/or password were
                                         reported to be incorrect. Please re-verify your username and password."},
     "INVALID_MFA_INFO": {"code": 234,
                          "message": "We're sorry, the authentication information you  provided is incorrect. Please try again."}}


## Url parameters

### Credentials

The credentials parameter is expected to be an AES 256 encrypted hash map. With the required values for login.
 
Tesco example:

    {"user_name": "frank@gmail.com",
     "password": "password1",
     "card_number": "634004024051328070"}

### Authentication

Authentication for use of the Midas api will be done by passing a unique string for verification.

## Exchange Format

At the moment we are returning JSON, however there may be value in using a data serialization framework such as:

* Apache Thrift
* Apache Avro

For a range of reasons including:

* Code-generation for static clients
* Better data types
* Performance
* Schema evolution processes



