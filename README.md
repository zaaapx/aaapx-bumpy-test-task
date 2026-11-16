# Bumpy · Liked You prototypes

Click-through HTML prototypes for the Bumpy product design test task (Liked You for free users, iOS).

| Prototype | Path | What it shows |
|---|---|---|
| Current flow | [`/current/`](current/) | The flow as it works today: push → blurred Liked You → reveal sheet or paywall → profile → Like → Bump → chat |
| H1 · Proof of real | [`/h1/`](h1/) | Country, reaction type, Verified and Active today on the blurred cards, a trust sheet, and a paywall with real counts |

Live: `https://zaaapx.github.io/aaapx-bumpy-test-task/` (GitHub Pages, branch `main`, folder `/`).

## How it is built

The screens are generated from the Figma file, so Figma stays the source of truth.

- `css/tokens.css` holds the Figma variables under their WEB code syntax (`--color-*`, `--space-*`, `--radius-*`, text styles `.t-*`, effects `--shadow-*`, `--blur-*`). Change a token there and every screen follows.
- `tools/figma-dump.js` exports screens from Figma to JSON (layer tree, positions, token references, text styles, prototype links). Run it through the Figma MCP `use_figma` tool or the Scripter plugin, with `IDS` set to the screen node IDs, and save each screen to `tools/dump/<node-id>.json`.
- `tools/prototypes.json` lists the screens of each prototype, the panel notes, and the wiring that is not in the Figma prototype (the current flow has none in Figma).
- `tools/build.py` turns the dumps into `current/index.html` and `h1/index.html`. Icons are recoloured through the Tone modes (`.tone-*` classes), photos, flags and emoji come from `assets/`.
- `js/proto.js` is the click-through engine: Figma transitions (dissolve, move in/out, push), after-delay links, deep links by `#screen-slug`, back with `←`, restart with `R`.

## Work locally

```bash
python3 tools/build.py          # rebuild both prototypes from tools/dump
python3 -m http.server 8765     # open http://localhost:8765
```

Open the pages over HTTP, not `file://`: the icon masks are blocked by the browser on `file://`.

Push to `main` to update GitHub Pages.

Fonts: Open Sans, SIL Open Font License (`assets/fonts/OFL.txt`).
