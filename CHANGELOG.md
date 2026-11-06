# Changelog

## 0.4.0 — 2026-11-06

- **New: diagnostics download.** The entry menu under **Settings → Devices & services** offers *Download diagnostics*: the entry's configuration, what was last fetched and the current state of its entities, with coordinates, credentials and other personal values redacted and long lists cut. Attach it to an issue report.

## 0.3.0 — 2026-11-06

- **New: triggers and conditions in the automation editor** (Home Assistant 2026.10 / 2026.11 or newer). *A ticket has won*, *A draw was published* and *Jackpot crossed a threshold* (an amount in CHF or a CHF entity) appear in the trigger list, *A ticket has won* and *No ticket has won* in the condition list, in all four languages. Each targets the integration's own entities; the usual *for* and behaviour options apply. On older versions the entries are simply not offered.
- **New: a blueprint, *notify on a winning ticket*.** One-click import from the README: picks the win sensors of your games and your phone, and sends game, draw date and every winning ticket with rank and prize; an action field takes your own steps with the text as `{{ message }}`.

## 0.2.0 — 2026-11-06

- **New: a dashboard strategy.** The card file now also registers `custom:swiss-lottery`, a recipe Home Assistant renders in the browser: one section per game with the Swiss Lottery card, the win sensor and the closing time of the next draw, generated live from your config entries — nothing is written into your dashboard configuration. The resource you registered for the card is all it needs. Pick *Swiss Lottery* under **Settings → Dashboards → + Add dashboard**, or fill a single view of your own dashboard with it; `title` and `max_columns` can be set under `strategy:`. The README has the details.

## 0.1.1 — 2026-11-05

- The results page is parsed in a worker thread instead of on the event loop (it is about 90 KB of HTML).
- A ticket line that cannot be used is reported in the log by its line number only, without the numbers on it.
- Removed an unreachable error text; the setup and options forms are otherwise unchanged.

## 0.1.0 — 2026-11-05

- **First release.** Swiss Lotto, EuroMillions and EuroDreams: the latest draw (numbers, lucky number / stars / dream number, Replay, Joker, Super-Star, 2nd Chance), the published prize ranks, the jackpot of the next draw and its closing time – read once an hour from the results page Swisslos publishes, one request for all three games.
- **Your tickets:** up to ten per game, entered when adding the game or later under *Configure*. One sensor per ticket with the matched numbers, the prize rank and the published prize, and a *Win* binary sensor per game for notifications.
- **Bundled dashboard card** `custom:swiss-lottery-card` with a visual editor: drawn balls, extra games, jackpot and next draw, your tickets with hits highlighted, optionally the prize table.
- Entity names in German, English, French and Italian.
