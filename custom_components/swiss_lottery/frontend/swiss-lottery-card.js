/*
 * Swiss Lottery card for Home Assistant.
 *
 * Shows the latest draw of a Swisslos game (Swiss Lotto, EuroMillions,
 * EuroDreams) as drawn balls, the extra game, the jackpot and the next draw,
 * and your tickets with the matched numbers highlighted. Everything comes
 * from the attributes of the integration's winning-numbers sensor.
 *
 * Served by the integration at /swiss_lottery_files/swiss-lottery-card.js.
 */

const CARD_VERSION = "0.1.0";

const LABELS = {
  draw_of: { de: "Ziehung vom", en: "Draw of", fr: "Tirage du", it: "Estrazione del" },
  lucky: { de: "Glückszahl", en: "Lucky number", fr: "Numéro chance", it: "Numero fortunato" },
  stars: { de: "Sterne", en: "Stars", fr: "Étoiles", it: "Stelle" },
  dream: { de: "Dream-Zahl", en: "Dream number", fr: "Numéro Dream", it: "Numero Dream" },
  replay: { de: "Replay", en: "Replay", fr: "Replay", it: "Replay" },
  second_chance: { de: "2. Chance", en: "2nd Chance", fr: "2e Chance", it: "2a Chance" },
  jackpot: { de: "Jackpot", en: "Jackpot", fr: "Jackpot", it: "Jackpot" },
  next_draw: { de: "Nächste Ziehung", en: "Next draw", fr: "Prochain tirage", it: "Prossima estrazione" },
  closing: { de: "Annahmeschluss", en: "closing", fr: "clôture", it: "chiusura" },
  tickets: { de: "Meine Tipps", en: "My tickets", fr: "Mes grilles", it: "Le mie schedine" },
  ticket: { de: "Tipp", en: "Ticket", fr: "Grille", it: "Schedina" },
  no_tickets: {
    de: "Keine Tipps hinterlegt – unter Einstellungen → Integrationen → Swiss Lottery → Konfigurieren eintragen.",
    en: "No tickets yet – add them under Settings → Integrations → Swiss Lottery → Configure.",
    fr: "Aucune grille – ajoutez-les sous Paramètres → Intégrations → Swiss Lottery → Configurer.",
    it: "Nessuna schedina – aggiungile in Impostazioni → Integrazioni → Swiss Lottery → Configura.",
  },
  no_win: { de: "kein Gewinn", en: "no win", fr: "pas de gain", it: "nessuna vincita" },
  won: { de: "Gewinn", en: "Win", fr: "Gain", it: "Vincita" },
  rank: { de: "Rang", en: "Rank", fr: "Rang", it: "Rango" },
  correct: { de: "Richtige", en: "Correct", fr: "Numéros exacts", it: "Numeri esatti" },
  winners: { de: "Gewinner", en: "Winners", fr: "Gagnants", it: "Vincitori" },
  prize: { de: "Gewinn (CHF)", en: "Prize (CHF)", fr: "Gain (CHF)", it: "Premio (CHF)" },
  unavailable: { de: "Keine aktuellen Daten von swisslos.ch", en: "No current data from swisslos.ch", fr: "Pas de données actuelles de swisslos.ch", it: "Nessun dato attuale da swisslos.ch" },
  source: { de: "Quelle: Swisslos", en: "Source: Swisslos", fr: "Source: Swisslos", it: "Fonte: Swisslos" },
};

const EDITOR_LABELS = {
  entity: { de: "Gewinnzahlen-Sensor", en: "Winning-numbers sensor", fr: "Capteur des numéros gagnants", it: "Sensore dei numeri vincenti" },
  title: { de: "Titel (optional)", en: "Title (optional)", fr: "Titre (facultatif)", it: "Titolo (facoltativo)" },
  show_tickets: { de: "Meine Tipps anzeigen", en: "Show my tickets", fr: "Afficher mes grilles", it: "Mostra le mie schedine" },
  show_jackpot: { de: "Jackpot und nächste Ziehung anzeigen", en: "Show jackpot and next draw", fr: "Afficher le jackpot et le prochain tirage", it: "Mostra jackpot e prossima estrazione" },
  show_ranks: { de: "Gewinnränge (Quoten) anzeigen", en: "Show prize ranks (odds)", fr: "Afficher les rangs de gain", it: "Mostra i ranghi di vincita" },
  show_extra: { de: "Joker / Super-Star / Replay anzeigen", en: "Show Joker / Super-Star / Replay", fr: "Afficher Joker / Super-Star / Replay", it: "Mostra Joker / Super-Star / Replay" },
};

function lang(hass) {
  return ((hass && hass.language) || "en").split("-")[0];
}
function L(hass, key) {
  const l = lang(hass);
  return (LABELS[key] && (LABELS[key][l] || LABELS[key].en)) || key;
}
function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
function fmtDate(hass, iso) {
  if (!iso) return "";
  const d = new Date(iso.length === 10 ? `${iso}T12:00:00` : iso);
  if (Number.isNaN(d.getTime())) return esc(iso);
  const locale = (hass && hass.locale && hass.locale.language) || "de-CH";
  return d.toLocaleDateString(locale, { weekday: "short", day: "2-digit", month: "2-digit", year: "numeric" });
}
function fmtDateTime(hass, iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return esc(iso);
  const locale = (hass && hass.locale && hass.locale.language) || "de-CH";
  return `${d.toLocaleDateString(locale, { weekday: "short", day: "2-digit", month: "2-digit", year: "numeric" })}, ${d.toLocaleTimeString(locale, { hour: "2-digit", minute: "2-digit" })}`;
}
function fmtChf(value, digits) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "";
  return new Intl.NumberFormat("de-CH", { maximumFractionDigits: digits, minimumFractionDigits: digits }).format(Number(value));
}
function fmtJackpot(value) {
  const n = Number(value);
  if (!Number.isFinite(n) || n <= 0) return "";
  if (n >= 1_000_000) {
    const mio = n / 1_000_000;
    return `CHF ${new Intl.NumberFormat("de-CH", { maximumFractionDigits: mio % 1 ? 1 : 0 }).format(mio)} Mio.`;
  }
  return `CHF ${fmtChf(n, 0)}`;
}

const STYLE = `
  :host { display: block; }
  ha-card { padding: 16px; }
  .head { display: flex; justify-content: space-between; align-items: baseline; gap: 12px; margin-bottom: 8px; }
  .title { font-size: 1.15em; font-weight: 500; }
  .date { color: var(--secondary-text-color); font-size: 0.9em; white-space: nowrap; }
  .balls { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin: 8px 0 4px; }
  .ball { width: 38px; height: 38px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center;
          font-weight: 600; font-size: 1.05em; background: var(--card-background-color, #fff); color: var(--primary-text-color);
          border: 2px solid var(--primary-color); box-sizing: border-box; }
  .ball.small { width: 28px; height: 28px; font-size: 0.85em; border-width: 1.5px; }
  .ball.bonus.lucky { background: #d32f2f; border-color: #d32f2f; color: #fff; }
  .ball.bonus.stars { background: #f9a825; border-color: #f9a825; color: #212121; }
  .ball.bonus.dream { background: #6a1b9a; border-color: #6a1b9a; color: #fff; }
  .ball.hit { background: var(--success-color, #2e7d32); border-color: var(--success-color, #2e7d32); color: #fff; }
  .ball.miss { opacity: 0.55; }
  .sep { width: 2px; height: 28px; background: var(--divider-color); margin: 0 4px; border-radius: 1px; }
  .line { display: flex; flex-wrap: wrap; gap: 6px 18px; color: var(--secondary-text-color); font-size: 0.92em; margin: 6px 0; }
  .line b { color: var(--primary-text-color); font-weight: 500; }
  .jackpot { display: flex; justify-content: space-between; flex-wrap: wrap; gap: 6px 16px; margin: 10px 0 2px; padding-top: 10px; border-top: 1px solid var(--divider-color); }
  .jackpot .amount { font-size: 1.25em; font-weight: 600; color: var(--primary-color); }
  .jackpot .next { color: var(--secondary-text-color); font-size: 0.9em; text-align: right; }
  .tickets { margin-top: 10px; padding-top: 10px; border-top: 1px solid var(--divider-color); }
  .tickets h3 { margin: 0 0 6px; font-size: 0.95em; font-weight: 500; color: var(--secondary-text-color); }
  .ticket { display: flex; align-items: center; gap: 8px; padding: 4px 0; flex-wrap: wrap; }
  .ticket .label { width: 56px; color: var(--secondary-text-color); font-size: 0.9em; flex: 0 0 auto; }
  .ticket .result { margin-left: auto; font-size: 0.9em; color: var(--secondary-text-color); white-space: nowrap; }
  .ticket.won .result { color: var(--success-color, #2e7d32); font-weight: 600; }
  .ticket.won .label { color: var(--success-color, #2e7d32); font-weight: 600; }
  .ranks { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 0.88em; }
  .ranks th, .ranks td { padding: 3px 6px; text-align: right; border-bottom: 1px solid var(--divider-color); }
  .ranks th:first-child, .ranks td:first-child { text-align: left; }
  .ranks th { color: var(--secondary-text-color); font-weight: 500; }
  .ranks tr.mine td { font-weight: 600; color: var(--success-color, #2e7d32); }
  .foot { margin-top: 8px; font-size: 0.75em; color: var(--secondary-text-color); text-align: right; }
  .empty { color: var(--secondary-text-color); font-size: 0.9em; padding: 6px 0; }
`;

function ball(n, cls) {
  return `<span class="ball ${cls || ""}">${esc(n)}</span>`;
}

class SwissLotteryCard extends HTMLElement {
  setConfig(config) {
    if (!config || !config.entity) throw new Error("entity (winning-numbers sensor) is required");
    this._config = {
      show_tickets: true,
      show_jackpot: true,
      show_extra: true,
      show_ranks: false,
      ...config,
    };
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  static getConfigElement() {
    return document.createElement("swiss-lottery-card-editor");
  }

  static getStubConfig(hass, entities) {
    const match = (entities || []).find((e) => /^sensor\.swiss_lottery_.*_numbers$/.test(e));
    return { entity: match || "" };
  }

  getCardSize() {
    return 4;
  }

  getGridOptions() {
    return { columns: 12, min_columns: 6, rows: "auto" };
  }

  _render() {
    if (!this._hass || !this._config) return;
    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
    }
    const hass = this._hass;
    const st = hass.states[this._config.entity];
    const a = (st && st.attributes) || {};
    const title = this._config.title || a.game_name || "Swiss Lottery";
    let body = "";

    if (!st || st.state === "unavailable" || st.state === "unknown" || !Array.isArray(a.numbers)) {
      body = `<div class="empty">${esc(L(hass, "unavailable"))}</div>`;
    } else {
      const kind = a.bonus_kind || "lucky";
      const main = a.numbers.map((n) => ball(n)).join("");
      const bonus = (a.bonus || []).map((n) => ball(n, `bonus ${kind}`)).join("");
      body += `<div class="balls">${main}${bonus ? `<span class="sep"></span>${bonus}` : ""}</div>`;

      if (this._config.show_extra) {
        const parts = [];
        if (a.replay !== null && a.replay !== undefined) parts.push(`${esc(L(hass, "replay"))}: <b>${esc(a.replay)}</b>`);
        if (a.extra_game && a.extra_game.number) {
          const jp = a.extra_game.jackpot ? ` (${esc(L(hass, "jackpot"))} ${esc(fmtJackpot(a.extra_game.jackpot))})` : "";
          parts.push(`${esc(a.extra_game.name)}: <b>${esc(a.extra_game.number)}</b>${jp}`);
        }
        if (Array.isArray(a.second_chance) && a.second_chance.length) {
          parts.push(`${esc(L(hass, "second_chance"))}: <b>${a.second_chance.map(esc).join(" ")}</b>`);
        }
        if (parts.length) body += `<div class="line">${parts.map((p) => `<span>${p}</span>`).join("")}</div>`;
      }

      if (this._config.show_jackpot && (a.jackpot || a.next_draw)) {
        const jp = a.jackpot ? `<span class="amount">${esc(L(hass, "jackpot"))} ${esc(fmtJackpot(a.jackpot))}</span>` : "<span></span>";
        const nd = a.next_draw
          ? `<span class="next">${esc(L(hass, "next_draw"))}: ${fmtDateTime(hass, a.next_draw)}${a.next_draw_closing ? ` (${esc(L(hass, "closing"))})` : ""}</span>`
          : "";
        body += `<div class="jackpot">${jp}${nd}</div>`;
      }

      if (this._config.show_tickets) {
        const tickets = Array.isArray(a.tickets) ? a.tickets : [];
        body += `<div class="tickets"><h3>${esc(L(hass, "tickets"))}</h3>`;
        if (!tickets.length) {
          body += `<div class="empty">${esc(L(hass, "no_tickets"))}</div>`;
        } else {
          tickets.forEach((tk, i) => {
            const mainBalls = (tk.numbers || [])
              .map((n) => ball(n, `small ${(tk.matched || []).includes(n) ? "hit" : "miss"}`))
              .join("");
            const bonusBalls = (tk.bonus || [])
              .map((n) => ball(n, `small bonus ${kind} ${(tk.matched_bonus || []).includes(n) ? "hit" : "miss"}`))
              .join("");
            let result;
            if (tk.won) {
              const prize = tk.prize !== null && tk.prize !== undefined ? `CHF ${fmtChf(tk.prize, 2)}` : esc(tk.prize_text || "");
              result = `🏆 ${esc(tk.rank || "")} · ${prize}`;
            } else {
              result = `${tk.matches}${tk.bonus_matches ? `+${tk.bonus_matches}` : ""} · ${esc(L(hass, "no_win"))}`;
            }
            body += `<div class="ticket ${tk.won ? "won" : ""}"><span class="label">${esc(L(hass, "ticket"))} ${i + 1}</span>${mainBalls}${bonusBalls ? `<span class="sep" style="height:20px"></span>${bonusBalls}` : ""}<span class="result">${result}</span></div>`;
          });
        }
        body += `</div>`;
      }

      if (this._config.show_ranks && Array.isArray(a.ranks) && a.ranks.length) {
        const mine = new Set((a.tickets || []).filter((t) => t.won).map((t) => t.rank));
        body += `<table class="ranks"><thead><tr><th>${esc(L(hass, "correct"))}</th><th>${esc(L(hass, "winners"))}</th><th>${esc(L(hass, "prize"))}</th></tr></thead><tbody>`;
        a.ranks.forEach((r) => {
          const prize = r.prize !== null && r.prize !== undefined ? fmtChf(r.prize, 2) : esc(r.prize_text || "");
          const winners = r.winners === null || r.winners === undefined ? "" : fmtChf(r.winners, 0);
          body += `<tr class="${mine.has(r.rank) ? "mine" : ""}"><td>${esc(r.rank)}</td><td>${winners}</td><td>${prize}</td></tr>`;
        });
        body += `</tbody></table>`;
      }
      body += `<div class="foot">${esc(L(hass, "source"))}</div>`;
    }

    const date = a.draw_date ? `<span class="date">${esc(L(hass, "draw_of"))} ${fmtDate(hass, a.draw_date)}</span>` : "";
    this.shadowRoot.innerHTML = `<style>${STYLE}</style><ha-card><div class="head"><span class="title">${esc(title)}</span>${date}</div>${body}</ha-card>`;
  }
}

customElements.define("swiss-lottery-card", SwissLotteryCard);

class SwissLotteryCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = config;
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  _render() {
    if (!this._hass || !this._config) return;
    if (!this._form) {
      this._form = document.createElement("ha-form");
      this._form.addEventListener("value-changed", (ev) => {
        ev.stopPropagation();
        const config = { type: "custom:swiss-lottery-card", ...ev.detail.value };
        if (!config.title) delete config.title;
        // Only persist toggles that differ from the defaults.
        if (config.show_tickets !== false) delete config.show_tickets;
        if (config.show_jackpot !== false) delete config.show_jackpot;
        if (config.show_extra !== false) delete config.show_extra;
        if (config.show_ranks !== true) delete config.show_ranks;
        this.dispatchEvent(new CustomEvent("config-changed", { detail: { config }, bubbles: true, composed: true }));
      });
      this.appendChild(this._form);
    }
    const l = lang(this._hass);
    this._form.hass = this._hass;
    this._form.data = {
      entity: this._config.entity || "",
      title: this._config.title || "",
      show_tickets: this._config.show_tickets !== false,
      show_jackpot: this._config.show_jackpot !== false,
      show_extra: this._config.show_extra !== false,
      show_ranks: this._config.show_ranks === true,
    };
    this._form.schema = [
      { name: "entity", required: true, selector: { entity: { domain: "sensor", integration: "swiss_lottery" } } },
      { name: "title", selector: { text: {} } },
      { name: "show_tickets", selector: { boolean: {} } },
      { name: "show_jackpot", selector: { boolean: {} } },
      { name: "show_extra", selector: { boolean: {} } },
      { name: "show_ranks", selector: { boolean: {} } },
    ];
    this._form.computeLabel = (schema) =>
      (EDITOR_LABELS[schema.name] && (EDITOR_LABELS[schema.name][l] || EDITOR_LABELS[schema.name].en)) || schema.name;
  }
}

customElements.define("swiss-lottery-card-editor", SwissLotteryCardEditor);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "swiss-lottery-card",
  name: "Swiss Lottery",
  description: "Latest Swisslos draw (Swiss Lotto, EuroMillions, EuroDreams), jackpot, next draw and your tickets.",
  preview: true,
  documentationURL: "https://github.com/prusuino/ha_swiss_lottery",
});

console.info(`%c SWISS-LOTTERY-CARD %c ${CARD_VERSION} `, "color: white; background: #d32f2f; font-weight: 700;", "color: #d32f2f; background: white; font-weight: 700;");

/* ---- Dashboard strategy ------------------------------------------------
 * The same resource also registers the dashboard strategy
 * `custom:swiss-lottery`. Core and strategy live in one IIFE so their names
 * never collide with another integration shipping the same core. */
(() => {
/* =====================================================================
 * Dashboard strategy core — shared building blocks
 * =====================================================================
 * A Lovelace dashboard strategy generates a dashboard in the browser at
 * render time. Nothing is written to .storage: the dashboard belongs to
 * the user, the integration only supplies the recipe.
 *
 * ⚠️ This block is duplicated into every integration that ships a
 * strategy. Each integration is its own HACS repository and must not
 * depend on another one being installed, so a shared file is not an
 * option. Keep the copies in sync and bump CORE_VERSION when the shared
 * part changes — it identifies which revision a copy was taken from.
 * ===================================================================== */

const CORE_VERSION = "1.1.1";

/* 1.1.1 - review follow-ups on the `strategy:` options
 *   (a) `map: false` only dropped the view with path "map". Where the map is
 *       a section inside another view (or a card in a panel view) it stayed
 *       visible. The option now also strips map cards out of every view: a
 *       section left with nothing but headings is dropped, and a view that
 *       ends up without any sections or cards is dropped as well.
 *   (b) The view flavour hardcoded max_columns: 2 and discarded the user's
 *       `max_columns`. It now uses the option when valid, else the value of
 *       the first sections view, else 2.
 *   (c) The view flavour copied only sections and cards, losing a view's
 *       `header` and `badges`. Both are carried over from the first view
 *       that has them. */

/* --- Registry access -------------------------------------------------
 * The registries are the only reliable way to find an integration's
 * entities: entity_id patterns are user-editable, unique_id is not.
 * Both calls are cheap and cached by the frontend for the render pass.
 */
async function loadRegistry(hass) {
  const [entities, devices] = await Promise.all([
    hass.callWS({ type: "config/entity_registry/list" }),
    hass.callWS({ type: "config/device_registry/list" }),
  ]);
  return { entities, devices };
}

/** All registry entries belonging to one integration (platform == domain). */
function entriesOfDomain(entities, domain) {
  return entities.filter((e) => e.platform === domain && !e.disabled_by);
}

/** Registry entries of one config entry, keyed by unique_id suffix.
 *  Mirrors the `f"{entry_id}_{suffix}"` convention the integrations use. */
function bySuffix(entities, configEntryId) {
  const out = {};
  const prefix = `${configEntryId}_`;
  for (const e of entities) {
    if (e.config_entry_id !== configEntryId) continue;
    if (typeof e.unique_id === "string" && e.unique_id.startsWith(prefix)) {
      out[e.unique_id.slice(prefix.length)] = e.entity_id;
    }
  }
  return out;
}

/** Group an integration's entities by the device they belong to.
 *  Returns [{device, entities:[registryEntry,...]}] sorted by device name. */
function groupByDevice(domainEntries, devices) {
  const byId = new Map(devices.map((d) => [d.id, d]));
  const groups = new Map();
  for (const e of domainEntries) {
    if (!e.device_id) continue;
    if (!groups.has(e.device_id)) groups.set(e.device_id, []);
    groups.get(e.device_id).push(e);
  }
  return [...groups.entries()]
    .map(([id, list]) => ({ device: byId.get(id), entities: list }))
    .filter((g) => g.device)
    .sort((a, b) => deviceName(a.device).localeCompare(deviceName(b.device)));
}

function deviceName(device) {
  return device.name_by_user || device.name || "";
}

/* --- Card helpers ---------------------------------------------------- */

const heading = (text, icon, badges) => {
  const card = { type: "heading", heading: text };
  if (icon) card.icon = icon;
  if (badges && badges.length) card.badges = badges;
  return card;
};

const grid = (cards, columnSpan) => {
  const section = { type: "grid", cards: cards.filter(Boolean) };
  if (columnSpan) section.column_span = columnSpan;
  return section;
};

const tile = (entity, extra = {}) => ({ type: "tile", entity, ...extra });

/** Map card fed from the integration's geo_location source.
 *  Deliberately uses geo_location_sources instead of an entity list: the
 *  markers are hidden entities, and the source keeps working when the
 *  set of markers changes between renders.
 *  labelAttribute writes the marker label into the source object, which is
 *  where the map card reads a geo-location source's label config from — the
 *  card-level label_mode only applies to `entities`. */
const mapCard = (domain, opts = {}) => ({
  type: "map",
  geo_location_sources: [
    opts.labelAttribute
      ? { source: domain, label_mode: "attribute", attribute: opts.labelAttribute }
      : domain,
  ],
  entities: opts.entities || ["zone.home"],
  default_zoom: opts.zoom ?? 8,
  theme_mode: "auto",
  grid_options: { columns: 12, rows: opts.rows ?? 6 },
});

/** Shown instead of an empty dashboard — an empty dashboard looks broken
 *  and gives the user nothing to act on. */
const emptyNotice = (text) => ({
  type: "markdown",
  content: text,
});

/* --- Localisation ----------------------------------------------------
 * Strategies run in the frontend, so hass.language is authoritative.
 * Falls back to English for any language the integration does not ship.
 */
function translator(strings, hass) {
  const lang = (hass.language || "en").split("-")[0];
  const table = strings[lang] || strings.en;
  return (key) => (table && table[key]) || (strings.en && strings.en[key]) || key;
}

/* --- Strategy base ---------------------------------------------------
 * Wraps the parts every strategy repeats: load registries, bail out
 * gracefully when the integration is not set up, and hand the concrete
 * strategy a prepared context.
 */

/* Options a user may put under `strategy:` in the raw configuration editor.
 * They are handled here in the core, so every integration supports the same
 * set without shipping its own option code:
 *
 *   map: false        drop the map: the full-screen map view as well as the
 *                     map cards inside section and panel views
 *   title: "..."      override the title
 *   max_columns: 3    column count of the generated section views (the view
 *                     flavour honours it too)
 *
 * Unknown keys are ignored on purpose - a strategy config is free-form, and a
 * typo should not take the dashboard down. */
const validColumns = (value) => {
  const cols = Number(value);
  return Number.isFinite(cols) && cols > 0 ? cols : undefined;
};

const isMapCard = (card) => Boolean(card) && card.type === "map";
const isHeadingCard = (card) => Boolean(card) && card.type === "heading";

/* Remove the map cards of one view. A section is dropped once only headings
 * remain - a heading merely labels the map that was just removed. Returns
 * null when nothing is left to show; views without a map card come back
 * untouched. */
const withoutMapCards = (view) => {
  let touched = false;
  const out = { ...view };
  if (Array.isArray(view.sections)) {
    out.sections = [];
    for (const section of view.sections) {
      const cards = Array.isArray(section.cards) ? section.cards : [];
      if (!cards.some(isMapCard)) {
        out.sections.push(section);
        continue;
      }
      touched = true;
      const rest = cards.filter((c) => !isMapCard(c));
      if (rest.some((c) => !isHeadingCard(c))) out.sections.push({ ...section, cards: rest });
    }
  }
  if (Array.isArray(view.cards) && view.cards.some(isMapCard)) {
    touched = true;
    out.cards = view.cards.filter((c) => !isMapCard(c));
  }
  if (!touched) return view;
  const empty = !(out.sections && out.sections.length) && !(out.cards && out.cards.length);
  return empty ? null : out;
};

const applyViewOptions = (views, config) => {
  const cfg = config || {};
  let out = views;
  if (cfg.map === false) {
    out = out
      .filter((v) => v.path !== "map")
      .map(withoutMapCards)
      .filter(Boolean);
  }
  const cols = validColumns(cfg.max_columns);
  if (cols) {
    out = out.map((v) => (v.type === "sections" ? { ...v, max_columns: cols } : v));
  }
  return out;
};

/* A view strategy must return exactly ONE view, while build() yields a list.
 * Section views are merged by concatenating their sections. A panel view (the
 * map) has no sections, so its cards become one full-width section instead -
 * that keeps the map visible rather than silently dropping it. */
const flattenToView = (views, title, icon, config) => {
  const sections = [];
  for (const v of views) {
    if (Array.isArray(v.sections) && v.sections.length) {
      sections.push(...v.sections);
    } else if (Array.isArray(v.cards) && v.cards.length) {
      sections.push(
        grid(
          v.cards.map((c) => ({
            ...c,
            grid_options: { columns: "full", rows: (c.grid_options || {}).rows ?? 8 },
          }))
        )
      );
    }
  }
  const sized = views.find((v) => v.type === "sections" && validColumns(v.max_columns));
  const view = {
    title,
    icon,
    type: "sections",
    max_columns: validColumns((config || {}).max_columns) ?? (sized ? validColumns(sized.max_columns) : 2),
    sections,
  };
  // header and badges live outside the sections and would be lost by the
  // merge above - keep the first ones the build produced.
  const withHeader = views.find((v) => v.header);
  if (withHeader) view.header = withHeader.header;
  const withBadges = views.find((v) => Array.isArray(v.badges) && v.badges.length);
  if (withBadges) view.badges = withBadges.badges;
  return view;
};

function defineDashboardStrategy(name, { domain, title, icon, build, strings, description }) {
  /* Shared by both strategy flavours: everything up to the finished view list. */
  const buildViews = async (config, hass) => {
    const t = translator(strings || {}, hass);
    let registry;
    try {
      registry = await loadRegistry(hass);
    } catch (err) {
      // Registry unreachable: render a readable message rather than
      // letting the dashboard fail with a blank screen.
      return [{ title: title, cards: [emptyNotice(`\u26a0\ufe0f ${err}`)] }];
    }
    const domainEntries = entriesOfDomain(registry.entities, domain);
    if (!domainEntries.length) {
      return [{ title: title, icon, cards: [emptyNotice(t("not_configured"))] }];
    }
    const views = await build({
      hass,
      config,
      t,
      domain,
      entities: domainEntries,
      devices: registry.devices,
      allEntities: registry.entities,
      helpers: { heading, grid, tile, mapCard, emptyNotice, bySuffix, groupByDevice, deviceName },
    });
    return applyViewOptions(views, config);
  };

  class Strategy extends HTMLElement {
    static async generate(config, hass) {
      const views = await buildViews(config, hass);
      return { title: (config && config.title) || title, views };
    }
  }

  /* The view flavour: fills a single view of a dashboard the user built
   * themselves, so adjusting the layout no longer requires "take control". */
  class ViewStrategy extends HTMLElement {
    static async generate(config, hass) {
      const views = await buildViews(config, hass);
      return flattenToView(views, (config && config.title) || title, icon, config);
    }
  }

  // getCreateSuggestions lets Home Assistant offer sensible defaults when the
  // strategy is picked from the "new dashboard" dialog.
  Strategy.getCreateSuggestions = () => ({ title, icon });

  customElements.define(`ll-strategy-dashboard-${name}`, Strategy);
  customElements.define(`ll-strategy-view-${name}`, ViewStrategy);

  // Announce the strategy to the frontend so it appears in the dashboard
  // creation dialog instead of having to be typed into the raw editor.
  window.customStrategies = window.customStrategies || [];
  if (!window.customStrategies.some((s) => s.type === name)) {
    window.customStrategies.push({
      type: name,
      strategyType: "dashboard",
      name: title,
      description: description || "",
    });
  }
  return Strategy;
}
/* =====================================================================
 * Dashboard strategy: Swiss Lottery
 * =====================================================================
 * Generates the dashboard in the browser at render time: one section per
 * configured game with the bundled card (drawn balls, extra games, jackpot,
 * next draw and your tickets) plus the win sensor and the closing time of
 * the next draw as tiles. Nothing is written into the user's configuration,
 * and the dashboard follows the config entries: add a game and its section
 * appears on the next load, remove one and it is gone.
 *
 * Usage — create an empty dashboard, open the raw configuration editor and
 * replace its content with:
 *
 *     strategy:
 *       type: custom:swiss-lottery
 *     views: []
 * ===================================================================== */

const SL_STRINGS = {
  en: {
    draws: "Draws",
    attribution: "Source: Swisslos",
    nothing_to_show:
      "### Nothing to show yet\n\nSwiss Lottery is set up, but none of its games has a visible sensor. Check the integration's devices under **Settings → Devices & services**.",
    not_configured:
      "### Swiss Lottery is not set up yet\n\nAdd the integration under **Settings → Devices & services** first, once per game. This dashboard then fills itself — there is nothing to configure here.",
  },
  de: {
    draws: "Ziehungen",
    attribution: "Quelle: Swisslos",
    nothing_to_show:
      "### Noch nichts anzuzeigen\n\nSwiss Lottery ist eingerichtet, aber kein Spiel hat einen sichtbaren Sensor. Prüfe die Geräte der Integration unter **Einstellungen → Geräte & Dienste**.",
    not_configured:
      "### Swiss Lottery ist noch nicht eingerichtet\n\nFüge die Integration zuerst unter **Einstellungen → Geräte & Dienste** hinzu, einmal pro Spiel. Dieses Dashboard füllt sich danach von selbst — hier ist nichts einzustellen.",
  },
  fr: {
    draws: "Tirages",
    attribution: "Source : Swisslos",
    nothing_to_show:
      "### Rien à afficher pour l'instant\n\nSwiss Lottery est configuré, mais aucun jeu n'a de capteur visible. Vérifiez les appareils de l'intégration sous **Paramètres → Appareils et services**.",
    not_configured:
      "### Swiss Lottery n'est pas encore configuré\n\nAjoutez d'abord l'intégration sous **Paramètres → Appareils et services**, une fois par jeu. Ce tableau de bord se remplit ensuite tout seul.",
  },
  it: {
    draws: "Estrazioni",
    attribution: "Fonte: Swisslos",
    nothing_to_show:
      "### Ancora niente da mostrare\n\nSwiss Lottery è configurato, ma nessun gioco ha un sensore visibile. Controlla i dispositivi dell'integrazione in **Impostazioni → Dispositivi e servizi**.",
    not_configured:
      "### Swiss Lottery non è ancora configurato\n\nAggiungi prima l'integrazione in **Impostazioni → Dispositivi e servizi**, una volta per gioco. Questa dashboard si riempie poi da sola.",
  },
};

/* The games in the order Swisslos lists them. Device names are the fixed
 * game names (not translated), so they can serve as the sort key; anything
 * unknown sorts after them alphabetically. */
const SL_GAME_ORDER = { "Swiss Lotto": 0, EuroMillions: 1, EuroDreams: 2 };
const SL_gameRank = (name) => (name in SL_GAME_ORDER ? SL_GAME_ORDER[name] : 9);

defineDashboardStrategy("swiss-lottery", {
  domain: "swiss_lottery",
  title: "Swiss Lottery",
  icon: "mdi:clover",
  description:
    "One section per game: the latest draw with your tickets, the win sensor and the closing time of the next draw, generated live from the integration.",
  strings: SL_STRINGS,

  async build({ t, entities, devices, helpers }) {
    const { heading, grid, tile, emptyNotice, groupByDevice, deviceName, bySuffix } = helpers;

    // One device per game (config entry). Suffix lookup mirrors the
    // integration's `<entry_id>_<suffix>` unique ids, so renamed entity ids
    // keep working.
    const groups = groupByDevice(entities, devices).sort(
      (a, b) =>
        SL_gameRank(deviceName(a.device)) - SL_gameRank(deviceName(b.device)) ||
        deviceName(a.device).localeCompare(deviceName(b.device))
    );

    const sections = [];
    for (const group of groups) {
      const entryId = group.entities.find((e) => e.config_entry_id)?.config_entry_id;
      if (!entryId) continue;
      const ids = bySuffix(entities, entryId);
      const hidden = new Set(group.entities.filter((e) => e.hidden_by).map((e) => e.entity_id));
      const visible = (entityId) => (entityId && !hidden.has(entityId) ? entityId : null);

      const numbersId = visible(ids.numbers);
      const cards = [];
      if (numbersId) {
        // The bundled card shows the whole draw from the numbers sensor's
        // attributes: balls, bonus numbers, extra games, jackpot, next draw
        // and the tickets with their hits. The prize table stays off here;
        // it is long and belongs to a card the user places deliberately.
        cards.push({
          type: "custom:swiss-lottery-card",
          entity: numbersId,
          show_ranks: false,
          grid_options: { columns: "full" },
        });
      } else {
        // Numbers sensor hidden: fall back to the plain sensors as tiles.
        for (const key of ["draw_date", "bonus", "extra_game", "jackpot"]) {
          const id = visible(ids[key]);
          if (id) cards.push(tile(id, { grid_options: { columns: 6 } }));
        }
      }
      const winId = visible(ids.win);
      const nextId = visible(ids.next_draw);
      if (winId) cards.push(tile(winId, { grid_options: { columns: 6 } }));
      if (nextId) cards.push(tile(nextId, { grid_options: { columns: 6 } }));
      if (!cards.length) continue;
      sections.push(grid([heading(deviceName(group.device), "mdi:clover"), ...cards]));
    }

    if (!sections.length) {
      return [{ title: t("draws"), cards: [emptyNotice(t("nothing_to_show"))] }];
    }
    // Swisslos is the source of every number shown; say so once at the bottom.
    sections.push(grid([{ type: "markdown", text_only: true, content: t("attribution") }], 3));
    return [
      {
        title: t("draws"),
        path: "draws",
        icon: "mdi:clover",
        type: "sections",
        max_columns: 3,
        sections,
      },
    ];
  },
});
})();
