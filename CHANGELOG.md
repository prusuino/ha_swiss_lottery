# Changelog

## 0.1.1 — 2026-11-05

- The results page is parsed in a worker thread instead of on the event loop (it is about 90 KB of HTML).
- A ticket line that cannot be used is reported in the log by its line number only, without the numbers on it.
- Removed an unreachable error text; the setup and options forms are otherwise unchanged.

## 0.1.0 — 2026-11-05

- **First release.** Swiss Lotto, EuroMillions and EuroDreams: the latest draw (numbers, lucky number / stars / dream number, Replay, Joker, Super-Star, 2nd Chance), the published prize ranks, the jackpot of the next draw and its closing time – read once an hour from the results page Swisslos publishes, one request for all three games.
- **Your tickets:** up to ten per game, entered when adding the game or later under *Configure*. One sensor per ticket with the matched numbers, the prize rank and the published prize, and a *Win* binary sensor per game for notifications.
- **Bundled dashboard card** `custom:swiss-lottery-card` with a visual editor: drawn balls, extra games, jackpot and next draw, your tickets with hits highlighted, optionally the prize table.
- Entity names in German, English, French and Italian.
