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
          body += `<tr class="${mine.has(r.rank) ? "mine" : ""}"><td>${esc(r.rank)}</td><td>${esc(r.winners ?? "")}</td><td>${prize}</td></tr>`;
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
