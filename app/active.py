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
    'nectar': 'nectar.Nectar',
    'my-opc': 'odeon.Odeon',
    'quidco': 'quidco.Quidco',
    'shell-drivers-club': 'shell.Shell',
    'health-beautycard': 'superdrug.Superdrug',
    'tasty-rewards': 'tabletable.Tabletable',
    'tesco-clubcard': 'tesco.Tesco',
    'tesco-clubcard1': 'tesco.Tesco',
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
    'rspb': 'rspb.RSPB',
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
    'iceland-bonus-card': 'iceland.Iceland',
    'the-garden-club': 'the_garden_club.TheGardenClub',
    'handm-club': 'handm.HAndM',
    # 'marriott-rewards-card': 'marriott.Marriott',     # Selenium agent disabled until the Docker-py work is complete
    # 'hilton-hhonors': 'hilton_honors.Hilton',         # Selenium agent disabled until the Docker-py work is complete
    'stansted-farm': 'my360.My360',
    'the-courtyard': 'my360.My360',
    '19-fourteas-tea-rooms': 'my360.My360',
    'bored-of-southsea': 'my360.My360',
    'game-over-cafe': 'my360.My360',
    'mad-hatters': 'my360.My360',
    'watkins-and-faux': 'my360.My360',
    'northney-farm-tea-room': 'my360.My360',
    'shakeadelic': 'my360.My360',
    'drift-bar': 'my360.My360',
    'poppins-restaurant': 'my360.My360',
    'polka-dot-piercing': 'my360.My360',
    'nanoo-hair': 'my360.My360',
    'comics-games-and-coffee': 'my360.My360',
    'the-richmond': 'my360.My360',
    'tennessee-chicken': 'my360.My360',
    'cliff-roe-sports': 'my360.My360',
    'michael-chell': 'my360.My360',
    'the-food-cellar': 'my360.My360',
    'hewetts': 'my360.My360',
    'fit-stuff': 'my360.My360',
    'cafe-copia': 'my360.My360',
    'bear-garden': 'my360.My360',
    'fresco-delikafessen': 'my360.My360',
    'henley-sports': 'my360.My360',
    'the-chocolate-cafe': 'my360.My360',
    'ted-james-barbershop': 'my360.My360',
    'bubble-city': 'my360.My360',
    'peewees': 'my360.My360',
    'turners-pies': 'my360.My360',
    'the-vestry': 'my360.My360',
    'laurence-menswear': 'my360.My360',
    'gatsby-menswear': 'my360.My360',
    'celo-tan-and-lash': 'my360.My360',
    'linda-h': 'my360.My360',
    'moffats': 'my360.My360',
    'tiffin-tea-rooms': 'my360.My360',
    'strawberry-vibes': 'my360.My360',
    'magoos': 'my360.My360',
    'ians-barbers': 'my360.My360',
    'everybody-pilates': 'my360.My360',
    'nevaeh-hair': 'my360.My360',
    'the-marmion': 'my360.My360',
    'funland': 'my360.My360',
    'the-nags-head': 'my360.My360',
    'beauty-clinic': 'my360.My360',
    'grit-gym-mma-and-fitness': 'my360.My360',
    'hilites-hair-and-beauty': 'my360.My360',
    'the-coffee-co': 'my360.My360',
    'thousand-hills': 'my360.My360',
    'urban-food': 'my360.My360',
    'dhaba-lane': 'my360.My360',
    'deep-blue-restaurants': 'my360.My360',
    'el-mexicana': 'my360.My360',
}
