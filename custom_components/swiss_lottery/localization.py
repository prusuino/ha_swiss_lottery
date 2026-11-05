"""Runtime string localization (entity names, device info).

Home Assistant's translation files only cover config-flow text and entity
state values. The names this integration assigns in Python are looked up
here, keyed by hass.config.language, with English as the fallback.
"""
from __future__ import annotations

from homeassistant.core import HomeAssistant

SUPPORTED_LANGUAGES = ("de", "en", "fr", "it")

STRINGS: dict[str, dict[str, str]] = {
    "manufacturer": {
        "de": "Swisslos Interkantonale Landeslotterie",
        "en": "Swisslos Interkantonale Landeslotterie",
        "fr": "Swisslos Loterie intercantonale",
        "it": "Swisslos Lotteria intercantonale",
    },
    "model": {
        "de": "Veröffentlichte Ziehungsergebnisse (swisslos.ch)",
        "en": "Published draw results (swisslos.ch)",
        "fr": "Résultats de tirage publiés (swisslos.ch)",
        "it": "Risultati delle estrazioni pubblicati (swisslos.ch)",
    },
    "numbers_sensor_name": {
        "de": "Gewinnzahlen",
        "en": "Winning Numbers",
        "fr": "Numéros gagnants",
        "it": "Numeri vincenti",
    },
    "bonus_swisslotto": {
        "de": "Glückszahl",
        "en": "Lucky Number",
        "fr": "Numéro chance",
        "it": "Numero fortunato",
    },
    "bonus_euromillions": {
        "de": "Sterne",
        "en": "Stars",
        "fr": "Étoiles",
        "it": "Stelle",
    },
    "bonus_eurodreams": {
        "de": "Dream-Zahl",
        "en": "Dream Number",
        "fr": "Numéro Dream",
        "it": "Numero Dream",
    },
    "replay_sensor_name": {
        "de": "Replay-Zahl",
        "en": "Replay Number",
        "fr": "Numéro Replay",
        "it": "Numero Replay",
    },
    "second_chance_sensor_name": {
        "de": "2. Chance",
        "en": "2nd Chance",
        "fr": "2e Chance",
        "it": "2a Chance",
    },
    "draw_date_sensor_name": {
        "de": "Ziehungsdatum",
        "en": "Draw Date",
        "fr": "Date du tirage",
        "it": "Data dell'estrazione",
    },
    "jackpot_sensor_name": {
        "de": "Jackpot",
        "en": "Jackpot",
        "fr": "Jackpot",
        "it": "Jackpot",
    },
    "next_draw_sensor_name": {
        "de": "Nächste Ziehung",
        "en": "Next Draw",
        "fr": "Prochain tirage",
        "it": "Prossima estrazione",
    },
    "ticket_sensor_name": {
        "de": "Tipp {n}",
        "en": "Ticket {n}",
        "fr": "Grille {n}",
        "it": "Schedina {n}",
    },
    "win_sensor_name": {
        "de": "Gewinn",
        "en": "Win",
        "fr": "Gain",
        "it": "Vincita",
    },
}


def t(key: str, hass: HomeAssistant, **kwargs) -> str:
    lang = (hass.config.language or "en").split("-")[0].lower()
    table = STRINGS[key]
    text = table.get(lang) or table["en"]
    return text.format(**kwargs) if kwargs else text
