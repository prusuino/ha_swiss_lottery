# Security Policy

## Supported Versions

Only the latest release is supported. Please update to the latest version before reporting an issue.

## Reporting a Vulnerability

This integration only reads one public web page over HTTPS. It has no write access to any external system and uses no credentials.

**What it sends:** once an hour (and once when a game is added), a plain GET request for `https://www.swisslos.ch/en/swisslotto/information/winning-numbers/winning-numbers.html` with an `Accept-Language: en` header – nothing else. No account, no cookies, no identifiers, and nothing about you or your tickets. Your tickets are stored with the config entry in Home Assistant's `.storage` and are compared with the published numbers on your own machine.

**Parsing:** the page is parsed with the Python standard library (`html.parser`) into a small element tree that is queried by CSS class; numbers are converted with strict patterns, and anything that does not match the expected structure makes the entities unavailable. Nothing from the page is executed, rendered as HTML, or written to disk. Text that reaches a dashboard (the extra-game code, prize texts) is escaped by the bundled card before it is inserted into the page.

If you believe you have found a security issue (for example in how a response is parsed or how entities are exposed), please report it privately via [GitHub Security Advisories](../../security/advisories/new) rather than opening a public issue.

For anything that is not security-sensitive (bugs, feature requests), please use the regular [Issues](../../issues) tab instead.
