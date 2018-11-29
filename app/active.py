# We possibly don't need the class path but we'll see

# These could be strings, if we end up with too many imports
# Commented entries are agents whose tests are currently not passing.
AGENTS = {
    # 'executive-club': 'british_airways.BritishAirways',    # Captcha.
    # 'coffee-club': 'costa.Costa',                          # Captcha.
    # 'greggs-rewards': 'greggs.Greggs',                     # Captcha.
    # 'colonels-club': 'kfc.Kfc',                            # Captcha.
    # 'my-opc': 'odeon.Odeon',                               # Captcha.
    # 'nandos-card': 'nandos.Nandos',                        # Captcha.
    # 'monsoon': 'monsoon.Monsoon',                          # Captcha.
    # 'klm-flying-blue': 'flying_blue.FlyingBlue',           # Captcha.
    # 'choicehotels': 'choicehotels.ChoiceHotels',           # Captcha.
    # 'mymail': 'mymail.MyMail',                             # Captcha.
    # 'starwood-preferred-guest': 'starwood.Starwood',       # Captcha.
    # 'hilton-hhonors': 'hilton_honors.Hilton',              # Captcha.
    # 'play-points': 'play_points.PlayPoints',               # Captcha.
    # 'shell-drivers-club': 'shell.Shell',                   # Shell have IP blocked us.
    # 'papa-johns': 'papa_johns.PapaJohns',                  # Papa johns have IP blocked us on production
    # 'mystarbucks-rewards': 'starbucks.Starbucks',          # Starbucks have added several measures to stop scraping.
    # 'aerclub': 'aerclub.AerClub',                          # Staging/prod can't handle requests[security]==2.18.4.
    # 'rewards4fishing': 'rewards4fishing.Rewards4Fishing',  # Scheme is being/has been shut down.
    # 'rewards4golf': 'rewards4golf.Rewards4Golf',           # CG request to deactivate due to low usage.
    # 'rewards4racing': 'rewards4racing.Rewards4Racing',     # CG request to deactivate due to low usage.
    # 'toysrus': 'toysrus.Toysrus',                          # Scheme is being/has been shut down.
    # ----------- sandbox testing start -------------- #
    'iceland-bonus-card': 'merchant_api_generic.MerchantAPIGeneric',
    # 'iceland-bonus-card': 'test_agent.TestAgentIce',
    # 'club-individual': 'club_individual.ClubIndividual',
    'club-individual': 'test_agent.TestAgentCI',
    'harvey-nichols-mock': 'test_agent.TestAgentHN',
    'harvey-nichols': 'harvey_nichols.HarveyNichols',
    # ----------- sandbox testing end ---------------- #
    'avios': 'avios_api.Avios',
    'advantage-card': 'boots.Boots',
    'the-co-operative-membership': 'cooperative.Cooperative',
    'debenhams': 'debenhams.Debenhams',
    'decathlon-card': 'decathlon.Decathlon',
    'enterprise': 'enterprise.Enterprise',
    'my-esprit': 'esprit.Esprit',
    'eurostar-plus-points': 'eurostar.Eurostar',
    'heathrow-rewards': 'heathrow.Heathrow',
    'vibe-club': 'vibe_club.VibeClub',
    'hertz': 'hertz.Hertz',
    'maximiles': 'maximiles.Maximiles',
    'match-more': 'morrisons.Morrisons',
    'nectar': 'nectar.Nectar',
    'quidco': 'quidco.Quidco',
    'coffee-one': 'coffee_one.CoffeeOne',
    'health-beautycard': 'superdrug.Superdrug',
    'tasty-rewards': 'tabletable.Tabletable',
    'esquires-coffee': 'esquires_coffee.EsquiresCoffee',
    'tesco-clubcard': 'tesco.Tesco',
    'tesco-clubcard1': 'tesco.Tesco',
    'the-waterstones-card': 'waterstones.Waterstones',
    'beefeater-grill-reward-club': 'beefeater.Beefeater',
    'harrods-rewards': 'harrods.Harrods',
    'trueblue': 'jetblue.JetBlue',
    'addison-lee': 'addison_lee.AddisonLee',
    'frequent-flyer': 'qantas.Qantas',
    'the-perfume-shop': 'the_perfume_shop.ThePerfumeShop',
    'space-nk': 'space_nk.SpaceNK',
    'jal-mileage-bank': 'jal_mileage_bank.JalMileageBank',
    'miles-and-more': 'lufthansa.Lufthansa',
    'avis': 'avis.Avis',
    'm-co-loyalty-card': 'mandco.MandCo',
    'sparks': 'sparks.Sparks',
    'virgin-flyingclub': 'virgin.Virgin',
    'rspb': 'rspb.RSPB',
    'rewards-club': 'ihg.Ihg',
    'gold-passport': 'hyatt.Hyatt',
    'rewards-for-life': 'holland_and_barrett.HollandAndBarrett',
    'together-rewards-card': 'the_works.TheWorks',
    'enrich': 'malaysia_airlines.MalaysiaAirlines',
    'royal-orchid-plus': 'thai_airways.ThaiAirways',
    'big-rewards': 'air_asia.AirAsia',
    'foyalty': 'foyles_bookstore.FoylesBookstore',
    'treat-me': 'paperchase.Paperchase',
    'priority-guest-rewards': 'priority_guest_rewards.PriorityGuestRewards',
    'delta-skymiles': 'delta.Delta',
    'le-club': 'accor.Accor',
    'discovery': 'gha.Gha',
    'clubcarlson': 'carlson.Carlson',
    'omni': 'omni.Omni',
    'bonus-club': 'brewersfayre.BrewersFayre',
    'love-your-body': 'the_body_shop.TheBodyShop',
    'recognition-reward-card': 'house_of_fraser.HouseOfFraser',
    'gbk-rewards': 'gourmet_burger_kitchen.GourmetBurgerKitchen',
    'pure-hmv': 'hmv.HMV',
    'victoria': 'victoria.Victoria',
    'star-rewards': 'star_rewards.StarRewards',
    'the-garden-club': 'the_garden_club.TheGardenClub',
    'handm-club': 'handm.HAndM',
    'tkmaxx': 'tk_maxx.TKMaxx',
    'macdonald-hotels': 'the_club.TheClub',
    'marriott-rewards-card': 'marriott.Marriott',
    'test-club-individual': 'club_individual_merchant_integration.ClubIndividual',
    'showcase': 'showcase.Showcase',
    'krisflyer': 'krisflyer.Krisflyer',
    'stansted-farm': 'my360.My360',
    'the-courtyard': 'my360.My360',
    '19-fourteas-tea-rooms': 'my360.My360',
    'bored-of-southsea': 'my360.My360',
    'game-over': 'my360.My360',
    'watkins-and-faux': 'my360.My360',
    'northney-farm': 'my360.My360',
    'shakeadelic': 'my360.My360',
    'drift-bar': 'my360.My360',
    'poppins-restaurant': 'my360.My360',
    'polka-dot-piercing': 'my360.My360',
    'nanoo-hair': 'my360.My360',
    'comics-games-and-coffee': 'my360.My360',
    'the-richmond': 'my360.My360',
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
    'turners-pies': 'my360.My360',
    'gatsby-menswear': 'my360.My360',
    'linda-h': 'my360.My360',
    'tiffin-tea-rooms': 'my360.My360',
    'hilites-hair-and-beauty': 'my360.My360',
    'dhaba-lane': 'my360.My360',
    'deep-blue-restaurants': 'my360.My360',
    'el-mexicana': 'my360.My360',
}
