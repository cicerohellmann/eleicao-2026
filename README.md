# Eleições 2026 · Apuração ao vivo

A single-page live tracker for Brazil's 2026 runoff (25 Oct 2026). It shows:

- **President:** the national count (Lula vs Flávio Bolsonaro) with the lead, sections counted, blank and null votes, and turnout.
- **Map:** each state coloured by who leads for president, or by the governor race.
- **Each state:** click one to see its presidential count and its governor race. That's the live runoff in AC, AM, DF, ES, RN and TO, and the 1st-round result (4 Oct) everywhere else.
- **Trend:** how the national lead moves as the count advances (recorded while the page is open).
- **Table:** a sortable list of every state, plus votes from abroad.

**Live:** https://cicerohellmann.github.io/eleicao-2026/

## How it works

The page reads the electoral court's (TSE) public results feed straight from the browser. The feed allows cross-origin requests, so there is no server or API key. The national count refreshes every 60 s, matching the feed's cache time, and states and governors refresh every 2 min.

Feed paths used (`https://resultados.tse.jus.br/oficial/`):

| Data | Path |
|---|---|
| Election list | `comum/config/ele-c.json` |
| President, 2nd round | `ele2026/6258/dados/{uf}/{uf}-c0001-e006258-u.json` (`br`, the states, `zz` = abroad) |
| Governor, 2nd round | `ele2026/6260/dados/{uf}/{uf}-c0003-e006260-u.json` |
| Governor, 1st round | `ele2026/6259/dados/{uf}/{uf}-c0003-e006259-u.json` |

You can also open `index.html` directly from disk, with no server.

## Editing

Edit `index.src.html`, then run `python3 tools/build.py`. That rebuilds `index.html` with the map outlines from `brmap.json` inlined. `tools/geo2svg.py` regenerates `brmap.json` from a states GeoJSON.

## Credits

- Results: [Tribunal Superior Eleitoral](https://resultados.tse.jus.br/oficial/app/index.html), public data. This is an unofficial viewer. For anything that matters, check the TSE.
- State outlines: [click_that_hood](https://github.com/codeforgermany/click_that_hood) (MIT), simplified.

## License

MIT
