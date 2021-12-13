# We possibly don't need the class path but we'll see

# These could be strings, if we end up with too many imports
# Commented entries are agents whose tests are currently not passing.
AGENTS = {
    "iceland-bonus-card": "iceland_merchant_integration.Iceland",
    "iceland-bonus-card-temp": "iceland.Iceland",
    "iceland-bonus-card-mock": "mock_agents.MockAgentIce",
    "harvey-nichols-mock": "mock_agents.MockAgentHN",
    "harvey-nichols": "harvey_nichols.HarveyNichols",
    "performance-mock": "performance_mock.MockPerformance",
    "performance-voucher-mock": "performance_mock.MockPerformanceVoucher",
    "fatface": "ecrebo.FatFace",
    "burger-king-rewards": "ecrebo.BurgerKing",
    "whsmith-rewards": "ecrebo.WhSmith",
    "whsmith-rewards-mock": "mock_agents.MockAgentWHS",
    "wasabi-club": "acteol.Wasabi",
    "bpl-trenette": "bpl.Trenette",
    "squaremeal": "squaremeal.Squaremeal",
}
