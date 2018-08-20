# Midas

# Templates

https://github.com/sendgridlabs/cookiecutter-flaskrestful
https://github.com/alexandre/flask-rest-template


https://developer.yodlee.com/FAQs/Error_Codes

## Environment

install docker and docker-compose
then

sudo docker-compose run --service-ports redis

## Docker Configuration

### Environment Variables

- `DEBUG`
  - String Value, enable application debug logging
- `REDIS_HOST`
  - String Value, IP or FQDN of REDIS
- `REDIS_PORT`
  - String Value, Port for REDIS
- `REDIS_PASSWORD`
  - String Value, Password for REDIS
- `HADES_URL`
  - String Value, URL for Hades
- `HERMES_URL`
  - String Value, URL for Hermes
- `SENTRY_DSN`
  - String Value, Sentry DNS for Midas
 - `RETRY_PERIOD` 
    - String Value, Number of seconds to retry consents send (should be about '1800')
- `REDIS_CELERY_DB`
    - String Value, To allow the use of a different database for Celery
    

### Use consents retry mechanism as explained in 
                
https://books.bink.com/books/backend-development/page/retry-tasks
                
### Celery help:
 
https://books.bink.com/books/backend-development/page/celery-and-celery-beat-overview
 
https://books.bink.com/books/backend-development/page/run-and-debugging-celery-and-celery-beat-in-pycharm
