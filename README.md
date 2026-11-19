# Bumpy · Liked You prototypes

Click-through HTML prototypes for the Bumpy product design test task (Liked You for free users, iOS).

| Prototype | Path | What it shows |
|---|---|---|
| Control | [`/current/`](current/) | Liked You as the brief shows it: 8 blurred reactions, any tap → Gold paywall (US$), after Gold → profile → It’s a BUMP → chats |
| H1a · Proof of real | [`/h1/`](h1/) | Country, reaction type, Verified and a labelled status on every blurred card, a preview from the push, and a paywall with real counts and the country mix |
| H1b · Proof of real + age | [`/h1b/`](h1b/) | H1a plus the age before paying: on the card, in the preview, in the push and as an age range on the paywall |
| H2 · Free reply | [`/h2/`](h2/) | The control plus Hello back on every blurred card, 1 free a day: the tap makes a Bump and reveals both, then the other pills lock until tomorrow |

Live: `https://zaaapx.github.io/aaapx-bumpy-test-task/` (GitHub Pages, branch `main`, folder `/`).

## How it is built

The screens are generated from the Figma file, so Figma stays the source of truth.

- `css/tokens.css` holds the Figma variables under their WEB code syntax (`--color-*`, `--space-*`, `--radius-*`, text styles `.t-*`, effects `--shadow-*`, `--blur-*`). Change a token there and every screen follows.
- `tools/figma-dump.js` exports screens from Figma to JSON (layer tree, positions, token references, text styles, prototype links). Run it through the Figma MCP `use_figma` tool or the Scripter plugin, with `IDS` set to the screen node IDs, and save each screen to `tools/dump/<node-id>.json`.
- `tools/prototypes.json` lists the screens of each prototype, the panel notes, and the wiring that is not in the Figma prototype (the current flow has none in Figma).
- `tools/build.py` turns the dumps into `current/`, `h1/`, `h1b/` and `h2/index.html`. Icons are recoloured through the Tone modes (`.tone-*` classes), photos, flags and emoji come from `assets/`.
- `js/proto.js` is the click-through engine: Figma transitions (dissolve, move in/out, push), after-delay links, deep links by `#screen-slug`, back with `←`, restart with `R`.

## Work locally

```bash
python3 tools/build.py          # rebuild the prototypes from tools/dump
python3 -m http.server 8765     # open http://localhost:8765
```

Open the pages over HTTP, not `file://`: the icon masks are blocked by the browser on `file://`.

Push to `main` to update GitHub Pages.

Fonts: Open Sans, SIL Open Font License (`assets/fonts/OFL.txt`).
