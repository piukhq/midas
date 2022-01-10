# We possibly don't need the class path but we'll see

# These could be strings, if we end up with too many imports
# Commented entries are agents whose tests are currently not passing.
from settings import NEW_ICELAND_AGENT_ACTIVE

AGENTS = {
    "iceland-bonus-card": "iceland.Iceland" if NEW_ICELAND_AGENT_ACTIVE else "iceland_merchant_integration.Iceland",
    "iceland-bonus-card-mock": "mock_agents.MockAgentIce",
    "harvey-nichols-mock": "mock_agents.MockAgentHN",
    "harvey-nichols": "harvey_nichols.HarveyNichols",
    "performance-mock": "performance_mock.MockPerformance",
    "performance-voucher-mock": "performance_mock.MockPerformanceVoucher",
    "wasabi-club": "acteol.Wasabi",
    "bpl-trenette": "bpl.Trenette",
    "squaremeal": "squaremeal.Squaremeal",
}
