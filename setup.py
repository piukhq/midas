from setuptools import setup

from app.version import __version__

setup(
    name='midas',
    version=__version__,
    description='Data acquisition project. Scrapes user data for scheme accounts such as balances and transactions. '
                'Also used to register users with new loyalty scheme accounts.',
    url='https://git.bink.com/Olympus/midas',
    author='Chris Latham',
    author_email='cl@bink.com',
    zip_safe=True)
