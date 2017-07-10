# We possibly don't need the class path but we'll see

# These could be strings, if we end up with too many imports
# Commented entries are agents whose tests are currently not passing.
AGENTS = {
    'avios': 'avios_api.Avios',
    'advantage-card': 'boots.Boots',
    'executive-club': 'british_airways.BritishAirways',
    'the-co-operative-membership': 'cooperative.Cooperative',
    # 'coffee-club': 'costa.Costa',                         # Costa now has a captcha.
    'debenhams': 'debenhams.Debenhams',
    'decathlon-card': 'decathlon.Decathlon',
    'enterprise': 'enterprise.Enterprise',
    'my-esprit': 'esprit.Esprit',
    'eurostar-plus-points': 'eurostar.Eurostar',
    'greggs-rewards': 'greggs.Greggs',
    'heathrow-rewards': 'heathrow.Heathrow',
    'hertz': 'hertz.Hertz',
    'colonels-club': 'kfc.Kfc',
    'maximiles': 'maximiles.Maximiles',
    'match-more': 'morrisons.Morrisons',
    # 'nectar': 'nectar.Nectar',  # c&d from nectar means we need to not scrape their site
    'my-opc': 'odeon.Odeon',
    'quidco': 'quidco.Quidco',
    'shell-drivers-club': 'shell.Shell',
    'health-beautycard': 'superdrug.Superdrug',
    'tasty-rewards': 'tabletable.Tabletable',
    'tesco-clubcard': 'tesco.Tesco',
    'toysrus': 'toysrus.Toysrus',
    'the-waterstones-card': 'waterstones.Waterstones',
    'nandos-card': 'nandos.Nandos',
    'beefeater-grill-reward-club': 'beefeater.Beefeater',
    'monsoon': 'monsoon.Monsoon',
    'harrods-rewards': 'harrods.Harrods',
    'trueblue': 'jetblue.JetBlue',
    'frequent-flyer': 'qantas.Qantas',
    'the-perfume-shop': 'the_perfume_shop.ThePerfumeShop',
    # 'rewards4fishing': 'rewards4fishing.Rewards4Fishing',     # scheme is being/has been shut down.
    'rewards4golf': 'rewards4golf.Rewards4Golf',
    'rewards4racing': 'rewards4racing.Rewards4Racing',
    'space-nk': 'space_nk.SpaceNK',
    'miles-and-more': 'lufthansa.Lufthansa',
    'avis': 'avis.Avis',
    'm-co-loyalty-card': 'mandco.MandCo',
    'sparks': 'sparks.Sparks',
    'virgin-flyingclub': 'virgin.Virgin',
    'rewards-club': 'ihg.Ihg',
    'gold-passport': 'hyatt.Hyatt',
    'rewards-for-life': 'holland_and_barrett.HollandAndBarrett',
    'starwood-preferred-guest': 'starwood.Starwood',
    'together-rewards-card': 'the_works.TheWorks',
    'enrich': 'malaysia_airlines.MalaysiaAirlines',
    'royal-orchid-plus': 'thai_airways.ThaiAirways',
    'big-rewards': 'air_asia.AirAsia',
    'foyalty': 'foyles_bookstore.FoylesBookstore',
    'treat-me': 'paperchase.Paperchase',
    'priority-guest-rewards': 'priority_guest_rewards.PriorityGuestRewards',
    'delta-skymiles': 'delta.Delta',
    # 'klm-flying-blue': 'flying_blue.FlyingBlue',      # captcha
    'le-club': 'accor.Accor',
    'choicehotels': 'choicehotels.ChoiceHotels',
    'discovery': 'gha.Gha',
    'clubcarlson': 'carlson.Carlson',
    'omni': 'omni.Omni',
    'papa-johns': 'papa_johns.PapaJohns',
    # 'mystarbucks-rewards': 'starbucks.Starbucks',      # starbucks has added several mesaures to stop us scraping them
    'mymail': 'mymail.MyMail',
    'bonus-club': 'brewersfayre.BrewersFayre',
    'love-your-body': 'the_body_shop.TheBodyShop',
    'recognition-reward-card': 'house_of_fraser.HouseOfFraser',
    'gbk-rewards': 'gourmet_burger_kitchen.GourmetBurgerKitchen',
    'pure-hmv': 'hmv.HMV',
    'star-rewards': 'star_rewards.StarRewards',
    'iceland': 'iceland.Iceland'
    # 'marriott-rewards-card': 'marriott.Marriott',     # Selenium agent disabled until the Docker-py work is complete
    # 'hilton-hhonors': 'hilton_honors.Hilton',         # Selenium agent disabled until the Docker-py work is complete
}
