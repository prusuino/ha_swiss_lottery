import json
from pathlib import Path
"""Constants for the Swiss Lottery integration."""
DOMAIN = "swiss_lottery"

CONF_GAME = "game"
CONF_TICKETS = "tickets"

GAME_SWISSLOTTO = "swisslotto"
GAME_EUROMILLIONS = "euromillions"
GAME_EURODREAMS = "eurodreams"
GAMES = (GAME_SWISSLOTTO, GAME_EUROMILLIONS, GAME_EURODREAMS)

# Published names, as used by Swisslos (not translated).
GAME_NAMES = {
    GAME_SWISSLOTTO: "Swiss Lotto",
    GAME_EUROMILLIONS: "EuroMillions",
    GAME_EURODREAMS: "EuroDreams",
}

# Ticket layout per game: (count of main numbers, max main number, count of
# bonus numbers, max bonus number). Swiss Lotto: 6 of 42 + 1 lucky number of 6;
# EuroMillions: 5 of 50 + 2 stars of 12; EuroDreams: 6 of 40 + 1 dream number of 5.
GAME_RULES = {
    GAME_SWISSLOTTO: (6, 42, 1, 6),
    GAME_EUROMILLIONS: (5, 50, 2, 12),
    GAME_EURODREAMS: (6, 40, 1, 5),
}
MAX_TICKETS = 10

# Swisslos publishes the results of all three games in the footer of this page.
SWISSLOS_RESULTS_URL = (
    "https://www.swisslos.ch/en/swisslotto/information/winning-numbers/winning-numbers.html"
)
SWISSLOS_REQUEST_TIMEOUT_SECONDS = 30
# Draws are twice (Swiss Lotto Wed/Sat, EuroMillions Tue/Fri, EuroDreams
# Mon/Thu) a week in the evening; the results are online within the hour.
# One request per hour for all three games is plenty.
UPDATE_INTERVAL_SECONDS = 3600

ATTRIBUTION = "Source: Swisslos (swisslos.ch)"
CONFIGURATION_URL = "https://www.swisslos.ch"

# The integration's own version, shown on the service card. Read from the
# manifest so that a release never needs to touch two places.
VERSION: str = json.loads((Path(__file__).parent / "manifest.json").read_text(encoding="utf-8"))["version"]
