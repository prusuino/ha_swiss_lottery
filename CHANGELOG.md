# Changelog

## 0.5.3 — 2026-11-09

- **Listed in the Marketplace default catalog.** The README now leads with the Marketplace/HACS search and keeps the custom-repository steps as a fallback, as suggested by @frenck in the HACS review (hacs/default #13449).

## 0.5.2 — 2026-11-09

- **Card hardening.** The card escapes every attribute value it renders: the badge class of the bonus balls, the bonus kind (only `lucky`, `stars` and `dream` are accepted) and the match counts of a ticket, which are coerced to numbers. Found in the HACS review by @frenck (hacs/default #13449).
- **Version on the service card.** The integration's version now appears on its service card under Settings → Devices & services, where the entities are listed.

## 0.5.1 — 2026-11-08

- **Maintenance.** The integration now keeps its per-entry data in the config entry's runtime data, as the Home Assistant quality scale asks, and declares the **bronze** tier in its manifest. The README gained a removal section. A test suite (ticket parser, draw evaluation, config flow) runs on every push. No change to entities or configuration.

## 0.5.0 — 2026-11-08

- **New: repair notices.** A notice under **Settings → Repairs** when swisslos.ch has not answered for three refreshes in a row, and another when the results page could not be read three times in a row, which means the page changed and the integration needs an update. Both clear themselves with the next successful refresh. In all four languages.

## 0.4.1 — 2026-11-06

- **Fixed: the diagnostics download could contain private values.** The entry's unique id went out unredacted: depending on the integration it holds the coordinates of the entry or, for a VKF entry of Swiss Hail Protection, the device serial. The text of the last error could also repeat a request URL. The unique id, the entry title and the entry's name and location fields are now redacted, and only the type of the last error is reported. If you have shared a diagnostics file from the previous version, consider it exposed.

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
