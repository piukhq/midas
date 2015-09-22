from app import create_app
from environment import read_env

read_env()
app = create_app()
