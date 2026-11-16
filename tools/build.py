#!/usr/bin/env python3
"""Build the HTML prototypes from the Figma dumps in tools/dump/.

    python3 tools/build.py

Every Figma layer becomes an absolutely positioned element at its Figma coordinates.
Colours, gradients, shadows, blurs and text styles are written as the CSS tokens from
css/tokens.css (the Figma variables with their WEB code syntax), so a token change
in tokens.css changes every screen. Prototype links come from the Figma prototype
(reactions) plus the extra wiring in prototypes.json.
"""
import html
import json
import math
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DUMP = os.path.join(ROOT, 'tools', 'dump')
CONF = json.load(open(os.path.join(ROOT, 'tools', 'prototypes.json')))

IMAGES = {
    'cb9c849b': 'photos/ayesha.jpg', '8d73a736': 'photos/chloe.jpg', 'ba02f2b3': 'photos/lena.jpg',
    '4ea1645a': 'photos/jack.jpg', '0463ba52': 'photos/avatar.jpg', 'c311fe31': 'emoji/wave.png',
    '08c6d19b': 'img/app-icon.png',
}
FLAGS = {'pakistan': 'pk', 'mauritius': 'mu', 'portugal': 'pt', 'belgium': 'be', 'chile': 'cl',
         'bosnia and herzegovina': 'ba', 'norway': 'no', 'brazil': 'br'}
EMOJI = {'Emoji/Man Biking': 'biking', 'Emoji/Flexed Biceps': 'biceps', 'Emoji/Ring': 'ring',
         'Emoji/Waving Hand 32': 'wave', 'Emoji/Waving Hand': 'wave'}
ICONS = {'Icon/Filters': 'filters', 'Icon/Hearts': 'hearts', 'Icon/Profile': 'profile', 'Icon/Map': 'map',
         'Icon/People': 'people', 'Icon/Chats': 'chats', 'Icon/Close': 'close', 'Icon/Share': 'share',
         'Icon/Chevron Right': 'chevron', 'Icon/Sort': 'sort', 'Icon/Spinner': 'spinner',
         'Icon/Verified': 'verified', 'Indicator/Online': 'online', 'Icon/Pass': 'pass', 'Icon/Heart': 'heart'}
COLOR_ICONS = {'verified', 'online', 'pass', 'heart'}       # multi-colour glyphs, shown as images
TONES = {'Primary': 'tone-primary', 'Active': 'tone-active', 'Inactive': 'tone-inactive', 'On media': 'tone-media'}
EFFECT_STYLES = {'Shadow/Raised': ('shadow', 'var(--shadow-raised)'), 'Shadow/Card': ('shadow', 'var(--shadow-card)'),
                 'Blur/Background 24': ('backdrop', 'var(--blur-24)'), 'Blur/Background 12': ('backdrop', 'var(--blur-12)')}
GRADIENT_TOKENS = {
    ('var(--color-gold-edge)', 'var(--color-gold-center)', 'var(--color-gold-edge)'): 'var(--gradient-gold)',
    ('var(--color-gold-soft)', 'var(--color-gold-soft-center)', 'var(--color-gold-soft)'): 'var(--gradient-gold-soft)',
    ('var(--color-notify-start)', 'var(--color-notify-end)'): 'var(--gradient-notify)',
}

TOKENS_CSS = open(os.path.join(ROOT, 'css', 'tokens.css')).read()
ALPHA_TOKENS = set(re.findall(r'(--color-[a-z0-9-]+):\s*rgb\([^)]*/', TOKENS_CSS))

# ---------------------------------------------------------------- helpers

def px(v):
    v = round(v, 2)
    return f'{int(v)}px' if v == int(v) else f'{v}px'


def load(sid):
    return json.load(open(os.path.join(DUMP, sid.replace(':', '-') + '.json')))


def esc(s):
    return html.escape(s, quote=True)


def rgba(hexc, a=1.0):
    r, g, b = (int(hexc[i:i + 2], 16) for i in (1, 3, 5))
    return f'rgb({r} {g} {b} / {round(a, 3)})' if a < 1 else hexc


def with_opacity(color, op):
    if op is None or op >= 1:
        return color
    return f'color-mix(in srgb, {color} {round(op * 100, 1)}%, transparent)'


def solid(p):
    """CSS colour for a solid paint; alpha tokens already hold their opacity."""
    v = p.get('v')
    if v and v.startswith('var('):
        name = v[4:-1]
        return v if name in ALPHA_TOKENS else with_opacity(v, p.get('op'))
    return rgba(p.get('c', '#000000'), p.get('op', 1))


def gradient(p, w, h):
    stops = p['st']
    key = tuple(s.get('v') for s in stops)
    if key in GRADIENT_TOKENS and p.get('op', 1) >= 1 and p['m'] == [[1, 0, 0], [0, 1, 0]]:
        return GRADIENT_TOKENS[key]
    (a, b, c), (d, e, f) = p['m']
    det = a * e - b * d or 1e-9
    def inv(u, v):  # gradient space -> node unit space
        u, v = u - c, v - f
        return ((e * u - b * v) / det, (-d * u + a * v) / det)
    x0, y0 = inv(0, 0.5)
    x1, y1 = inv(1, 0.5)
    dx, dy = (x1 - x0) * w, (y1 - y0) * h
    ang = round(math.degrees(math.atan2(dx, -dy)) % 360, 1)
    parts = []
    for s in stops:
        col = s.get('v') or rgba(s['c'], s.get('a', 1))
        if s.get('v') and s.get('a', 1) < 1:
            col = with_opacity(s['v'], s['a'])
        parts.append(f"{with_opacity(col, p.get('op'))} {round(s['p'] * 100, 1)}%")
    return f"linear-gradient({ang}deg, {', '.join(parts)})"


def image(p, w, h):
    src = IMAGES.get(p['h'])
    if not src:
        return None, None
    url = f"url('../assets/{src}')"
    if p.get('sm') == 'CROP' and p.get('it'):
        (a, _, tx), (_, d, ty) = p['it']
        bw, bh = w / (a or 1), h / (d or 1)
        return url, f'{px(-tx * bw)} {px(-ty * bh)} / {px(bw)} {px(bh)} no-repeat'
    if p.get('sm') == 'FIT':
        return url, 'center / contain no-repeat'
    return url, 'center / cover no-repeat'


def text_class(ts):
    return 't-' + re.sub(r'[^a-z0-9]+', '-', ts.lower()).strip('-')


def radius(r):
    if r is None:
        return None
    if isinstance(r, list):
        return ' '.join(px(min(x, 9999)) for x in r)
    return '9999px' if r >= 999 else px(r)


# ---------------------------------------------------------------- renderer

class Ctx:
    def __init__(self, conf, screen_ids):
        self.conf = conf
        self.screen_ids = set(screen_ids)
        self.alias = conf.get('alias', {})

    def dest(self, d):
        d = self.alias.get(d, d)
        return d if d in self.screen_ids else None


def link_attrs(ctx, rx):
    for r in rx:
        if r.get('tr') == 'ON_CLICK' and r.get('a') == 'NODE':
            d = ctx.dest(r['d'])
            if d:
                return {'data-go': d, 'data-tt': (r.get('tt') or 'INSTANT').lower(),
                        'data-dir': (r.get('dir') or '').lower(), 'data-td': str(r.get('td') or 0.3)}
        if r.get('tr') == 'ON_CLICK' and r.get('a') == 'BACK':
            return {'data-back': '1'}
    return {}


STATUS_SVG = (
    '<svg class="sb-cell" width="19" height="12" viewBox="0 0 20 13"><path fill="currentColor" fill-rule="evenodd" d="M19.2 1.15C19.2.51 18.72 0 18.13 0h-1.06C16.48 0 16 .51 16 1.15v9.93c0 .63.48 1.15 1.07 1.15h1.06c.59 0 1.07-.52 1.07-1.15V1.15ZM11.77 2.45h1.06c.59 0 1.07.52 1.07 1.17v7.43c0 .65-.48 1.18-1.07 1.18h-1.06c-.6 0-1.07-.53-1.07-1.18V3.62c0-.65.48-1.17 1.07-1.17ZM7.43 5.09H6.37c-.59 0-1.07.54-1.07 1.19v4.76c0 .65.48 1.19 1.07 1.19h1.06c.59 0 1.07-.54 1.07-1.19V6.28c0-.65-.48-1.19-1.07-1.19ZM2.13 7.54H1.07C.48 7.54 0 8.06 0 8.71v2.34c0 .65.48 1.17 1.07 1.17h1.06c.59 0 1.07-.52 1.07-1.17V8.71c0-.65-.48-1.17-1.07-1.17Z"/></svg>'
    '<svg class="sb-wifi" width="17" height="12" viewBox="0 0 18 13"><path fill="currentColor" fill-rule="evenodd" d="M8.57 2.47c2.49 0 4.88.92 6.68 2.57.14.13.35.13.49 0l1.3-1.27a.35.35 0 0 0 0-.49C12.3-1.09 4.84-1.09.11 3.28a.35.35 0 0 0 0 .49l1.3 1.27c.13.13.35.13.48 0a9.87 9.87 0 0 1 6.68-2.57Zm0 4.22c1.36 0 2.67.51 3.67 1.43.14.13.35.13.48 0l1.29-1.32a.36.36 0 0 0 0-.52 7.98 7.98 0 0 0-10.87 0 .36.36 0 0 0 0 .52l1.28 1.32c.13.13.35.13.48 0a5.4 5.4 0 0 1 3.67-1.43Zm2.52 2.79a.36.36 0 0 1-.1.28l-2.18 2.46a.33.33 0 0 1-.48 0L6.15 9.76a.36.36 0 0 1 .01-.56c1.39-1.31 3.43-1.31 4.82 0 .07.07.11.17.11.28Z"/></svg>'
    '<span class="sb-batt"><i></i></span>'
)


def render_leaf(n, ox, oy, ctx):
    comp = n.get('comp', '')
    x, y, w, h = n['x'] - ox, n['y'] - oy, n['w'], n['h']
    box = f'left:{px(x)};top:{px(y)};width:{px(w)};height:{px(h)}'
    name = esc(n['n'])
    if comp == 'System Bar':
        g = n.get('glyph') or {}
        light = g.get('v') == 'var(--color-text-on-media)' or g.get('c', '').lower() in ('#ffffff', '#fff')
        return (f'<div class="n status-bar{" status-bar--light" if light else ""}" data-name="{name}" style="{box}">'
                f'<span class="sb-time">9:41</span><span class="sb-levels">{STATUS_SVG}</span></div>')
    if comp == 'HomeIndicator':
        return f'<div class="n home-ind" data-name="{name}" style="{box}"><i></i></div>'
    if comp == 'Flag':
        swap = (n.get('swap') or '').lower()
        swap = ctx.conf.get('flag_override', {}).get(swap, swap)
        code = FLAGS.get(swap)
        return f'<img class="n flag" data-name="{name}" alt="" src="../assets/flags/{code}.png" style="{box}">' if code else ''
    if comp in EMOJI or (comp.startswith('Emoji/') and n.get('swap') in ('Waving Hand',)):
        return f'<img class="n" data-name="{name}" alt="" src="../assets/emoji/{EMOJI.get(comp, "wave")}.png" style="{box}">'
    if comp == 'Logo/Bumpy':
        return f'<img class="n" data-name="{name}" alt="Bumpy" src="../assets/img/logo.png" style="{box};object-fit:contain">'
    icon = ICONS.get(comp)
    if icon:
        if icon in COLOR_ICONS:
            return f'<img class="n" data-name="{name}" alt="" src="../assets/icons/{icon}.png" style="{box}">'
        g = n.get('glyph') or {}
        color = ''
        if g.get('v') and g['v'] != 'var(--tone-icon)':
            color = f';background-color:{solid(g)}'
        return f'<i class="n i ic-{icon}" data-name="{name}" style="{box}{color}"></i>'
    return None


def render(n, ox, oy, ctx, interactive=True, depth=0):
    if n.get('skip') or n.get('n') == 'Lock Screen' or (depth == 0 and n.get('n') in ctx.conf.get('backgrounds', {})):
        return render_skipped(n, ctx)
    if n.get('leaf'):
        out = render_leaf(n, ox, oy, ctx)
        if out is not None:
            return out
    x, y, w, h = n['x'] - ox, n['y'] - oy, n['w'], n['h']
    st = [f'left:{px(x)}', f'top:{px(y)}', f'width:{px(w)}', f'height:{px(h)}']
    cls = ['n']
    attrs = {'data-name': n['n']}
    if n.get('tone') in TONES:
        cls.append(TONES[n['tone']])
    if interactive and n.get('rx'):
        attrs.update(link_attrs(ctx, n['rx']))
    if interactive and n.get('_go'):
        attrs.update(n['_go'])
    if n.get('op') is not None:
        st.append(f"opacity:{n['op']}")
    r = radius(n.get('r'))
    if r and n['t'] != 'TEX':
        st.append(f'border-radius:{r}')
    if n.get('clip'):
        st.append('overflow:hidden')

    # fills -> background layers (Figma lists bottom first, CSS top first)
    layers = []
    for p in reversed(n.get('f', [])):
        if p['k'] == 's':
            c = solid(p)
            layers.append(f'linear-gradient({c}, {c})')
        elif p['k'] == 'g':
            layers.append(gradient(p, w, h))
        elif p['k'] == 'i':
            url, pos = image(p, w, h)
            if url:
                layers.append(f'{url} {pos}')
    if n['t'] in ('VEC', 'BOO', 'STA', 'POL', 'LIN') and n.get('svg') and n['svg'] != 'BIG':
        layers = []
    if len(layers) == 1 and layers[0].startswith('linear-gradient(') and n.get('f', [{}])[-1].get('k') == 's':
        st.append(f"background:{solid(n['f'][-1])}")
    elif layers:
        st.append('background:' + ', '.join(layers))

    # strokes + effects -> box-shadow / filters
    shadows, backdrop, filt = [], None, None
    if n.get('s') and n['t'] not in ('VEC', 'BOO', 'TEX'):
        col = solid(n['s']) if n['s']['k'] == 's' else '#000'
        sw = n.get('sw', 1)
        align = n.get('sa', 'INSIDE')
        if isinstance(sw, list):
            t, rr, b, l = sw
            if t: shadows.append(f'inset 0 {px(t)} 0 {col}')
            if b: shadows.append(f'inset 0 {px(-b)} 0 {col}')
            if l: shadows.append(f'inset {px(l)} 0 0 {col}')
            if rr: shadows.append(f'inset {px(-rr)} 0 0 {col}')
        elif align == 'OUTSIDE':
            shadows.append(f'0 0 0 {px(sw)} {col}')
        elif align == 'CENTER':
            shadows.append(f'inset 0 0 0 {px(sw / 2)} {col}')
            shadows.append(f'0 0 0 {px(sw / 2)} {col}')
        else:
            shadows.append(f'inset 0 0 0 {px(sw)} {col}')
    if n.get('fxs') in EFFECT_STYLES:
        kind, val = EFFECT_STYLES[n['fxs']]
        if kind == 'shadow':
            shadows.append(val)
        else:
            backdrop = val
    for e in n.get('fx', []) or []:
        t = e.get('t')
        if t == 'DROP':
            shadows.append(f"{px(e.get('x') or 0)} {px(e.get('y') or 0)} {px(e.get('r') or 0)} {px(e.get('sp') or 0)} {rgba(e.get('c', '#000000'), e.get('a', 1))}")
        elif t == 'INNER':
            shadows.append(f"inset {px(e.get('x') or 0)} {px(e.get('y') or 0)} {px(e.get('r') or 0)} {px(e.get('sp') or 0)} {rgba(e.get('c', '#000000'), e.get('a', 1))}")
        elif t == 'BACKGROUND' and e.get('r'):
            backdrop = f"blur({px(e['r'] / 2)})"
        elif t == 'GLASS':
            backdrop = 'blur(14px) saturate(1.8)'
        elif t == 'LAYER' and e.get('r'):
            filt = f"blur({px(e['r'] / 2)})"
    if shadows:
        st.append('box-shadow:' + ', '.join(shadows))
    if backdrop:
        st.append(f'-webkit-backdrop-filter:{backdrop};backdrop-filter:{backdrop}')
    if filt:
        st.append(f'filter:{filt}')

    a = ''.join(f' {k}="{esc(str(v))}"' for k, v in attrs.items())
    if 'data-go' in attrs or 'data-back' in attrs:
        cls.append('hot')

    if n['t'] == 'TEX':
        return render_text(n, cls, st, a)
    if n['t'] in ('VEC', 'BOO', 'STA', 'POL', 'LIN') and n.get('svg') and n['svg'] != 'BIG':
        svg = re.sub(r'<svg ([^>]*?)width="[^"]*" height="[^"]*"', r'<svg \1width="100%" height="100%"', n['svg'], count=1)
        svg = svg.replace('<svg ', '<svg preserveAspectRatio="none" ', 1)
        return f'<div class="{" ".join(cls)}"{a} style="{";".join(st)}">{svg}</div>'
    if n['t'] == 'ELL':
        st.append('border-radius:50%')

    kids = ''.join(render(c, n['x'], n['y'], ctx, interactive, depth + 1) for c in n.get('ch', []))
    return f'<div class="{" ".join(cls)}"{a} style="{";".join(st)}">{kids}</div>'


def render_text(n, cls, st, a):
    segs = n.get('seg') or [{}]
    first = segs[0]
    if first.get('ts'):
        cls.append(text_class(first['ts']))
    else:
        st.append(text_font(first))
    if first.get('fill'):
        st.append(f"color:{solid(first['fill'])}")
    if n.get('ta') == 'C': st.append('text-align:center')
    elif n.get('ta') == 'R': st.append('text-align:right')
    elif n.get('ta') == 'J': st.append('text-align:justify')
    if n.get('ar') == 'W':
        st.append('white-space:nowrap')
    if n.get('tv') in ('C', 'B'):
        st.append('display:flex;flex-direction:column;justify-content:' + ('center' if n['tv'] == 'C' else 'flex-end'))
    if len(segs) > 1:
        body = ''
        for s in segs:
            sst = []
            if s.get('ts') and s.get('ts') != first.get('ts'):
                sc = f' class="{text_class(s["ts"])}"'
            else:
                sc = ''
            if not s.get('ts'):
                sst.append(text_font(s))
            if s.get('fill') and s['fill'] != first.get('fill'):
                sst.append(f"color:{solid(s['fill'])}")
            if s.get('td') == 'UNDERLINE':
                sst.append('text-decoration:underline')
            style = f' style="{";".join(sst)}"' if sst else ''
            body += f'<span{sc}{style}>{esc(s.get("c", "")).replace(chr(10), "<br>")}</span>'
        if n.get('tv') in ('C', 'B'):
            body = f'<span>{body}</span>'
    else:
        body = esc(n['c']).replace('\n', '<br>')
        if first.get('td') == 'UNDERLINE':
            st.append('text-decoration:underline')
    return f'<div class="{" ".join(cls)}"{a} style="{";".join(st)}">{body}</div>'


def text_font(s):
    fam = s.get('ff', '')
    weight = {'Regular': 400, 'Medium': 500, 'Semibold': 600, 'SemiBold': 600, 'Bold': 700}.get(s.get('fw'), 400)
    family = "-apple-system, BlinkMacSystemFont, 'SF Pro Text', system-ui, sans-serif" if 'SF' in fam else 'var(--font-family-base)'
    lh = f";line-height:{px(s['lh'])}" if s.get('lh') else ''
    return f"font-family:{family};font-weight:{weight};font-size:{px(s.get('fs', 14))}{lh}"


def render_skipped(n, ctx):
    name = n['n']
    if name == 'Lock Screen':
        return f'<div class="n lockscreen" data-name="Lock Screen" style="left:0;top:0;width:{px(n["w"])};height:{px(n["h"])}"></div>'
    src = ctx.conf.get('backgrounds', {}).get(name)
    if not src:
        return ''
    scr = load(src)
    kids = ''.join(render(c, 0, 0, ctx, interactive=False) for c in scr.get('ch', []))
    bg = ''
    if scr.get('f'):
        p = scr['f'][-1]
        bg = f';background:{solid(p) if p["k"] == "s" else gradient(p, 402, 874)}'
    return f'<div class="n bg-clone" data-name="{esc(name)}" style="left:0;top:0;width:402px;height:874px;overflow:hidden{bg}">{kids}</div>'


# ---------------------------------------------------------------- extra wiring

def find_all(n, name):
    if n.get('n') == name:
        yield n
    for c in n.get('ch', []):
        yield from find_all(c, name)


def apply_wiring(scr, wiring, ctx):
    for w in wiring:
        d = ctx.dest(w['to'])
        if not d:
            continue
        hits = list(find_all(scr, w['node']))
        if not hits:
            print(f"  ! {scr['id']}: no layer named {w['node']!r}")
        for hit in hits if w.get('all') else hits[:1]:
            hit['_go'] = {'data-go': d, 'data-tt': w.get('tt', 'dissolve'), 'data-dir': w.get('dir', ''),
                          'data-td': str(w.get('td', 0.3))}


# ---------------------------------------------------------------- page

def slug(s):
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')


def build(key):
    conf = CONF[key]
    ids = [s['id'] for s in conf['screens']]
    ctx = Ctx(conf, ids)
    sections, nav = [], []
    for i, s in enumerate(conf['screens']):
        scr = load(s['id'])
        apply_wiring(scr, conf.get('wiring', {}).get(s['id'], []), ctx)
        after = ''
        for r in scr.get('rx', []):
            if r.get('tr') == 'AFTER_TIMEOUT':
                d = ctx.dest(r['d'])
                if d:
                    after = f' data-after="{int((r.get("to") or 1) * 1000)}" data-after-go="{d}" data-after-tt="{(r.get("tt") or "dissolve").lower()}"'
        bg = ''
        if scr.get('f'):
            p = scr['f'][-1]
            bg = solid(p) if p['k'] == 's' else gradient(p, 402, 874)
        kids = ''.join(render(c, 0, 0, ctx) for c in scr.get('ch', []))
        title = s.get('title', scr['n'])
        sections.append(
            f'<section class="screen" id="s-{s["id"].replace(":", "-")}" data-id="{s["id"]}" data-slug="{slug(title)}"'
            f' data-title="{esc(title)}"{after} style="background:{bg}">{kids}</section>')
        note = s.get('note')
        nav.append({'id': s['id'], 'title': title, 'slug': slug(title), 'note': note})

    page = TEMPLATE.format(
        title=esc(conf['title']), heading=esc(conf['heading']), lead=conf['lead'],
        extra=conf.get('panel_html', ''), screens='\n'.join(sections),
        nav=json.dumps(nav, ensure_ascii=False), start=conf['screens'][0]['id'], other=conf.get('other', ''))
    out = os.path.join(ROOT, key, 'index.html')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, 'w').write(page)
    print(f'{key}/index.html  {len(sections)} screens  {len(page) // 1024} KB')


TEMPLATE = '''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{title}</title>
<link rel="stylesheet" href="../css/tokens.css">
<link rel="stylesheet" href="../css/ui.css">
</head>
<body>
<main class="stage">
  <aside class="panel">
    <a class="back-link" href="../">← Bumpy · Liked You</a>
    <h1>{heading}</h1>
    <p class="lead">{lead}</p>
    {extra}
    <div class="note" id="note" aria-live="polite"></div>
    <ol class="screens" id="screens"></ol>
    <div class="row">
      <button class="chip-btn" id="restart" type="button">Restart</button>
      <button class="chip-btn" id="hotspots" type="button" aria-pressed="false">Show hotspots</button>
    </div>
    <p class="hint">Tap the phone to click through. Tap an empty area to flash the hotspots. <kbd>R</kbd> restarts, <kbd>←</kbd> goes back.</p>
    {other}
  </aside>
  <div class="device-wrap"><div class="device" id="device">
{screens}
  </div></div>
</main>
<script>window.PROTO = {{ start: "{start}", screens: {nav} }};</script>
<script src="../js/proto.js"></script>
</body>
</html>
'''

if __name__ == '__main__':
    for k in CONF:
        build(k)
