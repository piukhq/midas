# We possibly don't need the class path but we'll see
from app.agents.boots import Boots
from app.agents.tesco import Tesco

#These could be strings, if we end up with too many imports
AGENTS = {
    "tesco": Tesco,
    "boots": Boots
}
    # ('slug', 'class name')
    # ('tesco', 'agents.Tesco'),
    # ('nectar', 'Nectar'),
    #{'boots', 'boots.Boots'),
    # ('superdrug', 'Superdrug'),
    # ('shell', 'Shell'),
    # ('starbucks', 'Starbucks'),
    # ('costa', 'costa'),
    # ('avios', 'avios'),
    # ('british-airways', 'BritishAirways'),
    # ('morrisons', 'Morrisons'),
    # ('co-operative', 'CoOperative'),
    # ('kfc', 'KFC'),
    # ('greggs', 'Greggs'),
    # ('nandos', 'Nandos'),
    # ('mothercare', 'Mothercare'),
    # ('house-of-fraser', 'HouseOfFraser'),
    # ('debenhams', 'Debenhams'),

CREDENTIALS = {
    "tesco": {'user_name': 'julie.gormley100@gmail.com',
              'password': 'NSHansbrics5',
              'card_number': '634004024051328070',}
}
