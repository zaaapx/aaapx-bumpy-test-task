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
    '87bdbb2e': 'photos/marta.jpg', '95c21628': 'photos/mei.jpg', '08ff3a55': 'photos/ines.jpg',
    'marta001': 'photos/marta.jpg', 'mei00001': 'photos/mei.jpg', 'ines0001': 'photos/ines.jpg',
    '317076df': 'photos/sofia.jpg', 'c1a99c0f': 'photos/nora.jpg',
}
FLAGS = {'pakistan': 'pk', 'mauritius': 'mu', 'portugal': 'pt', 'belgium': 'be', 'chile': 'cl',
         'bosnia and herzegovina': 'ba', 'norway': 'no', 'brazil': 'br'}
EMOJI = {'Emoji/Man Biking': 'biking', 'Emoji/Flexed Biceps': 'biceps', 'Emoji/Ring': 'ring',
         'Emoji/Waving Hand 32': 'wave', 'Emoji/Waving Hand': 'wave'}
ICONS = {'Icon/Filters': 'filters', 'Icon/Hearts': 'hearts', 'Icon/Profile': 'profile', 'Icon/Map': 'map',
         'Icon/People': 'people', 'Icon/Chats': 'chats', 'Icon/Close': 'close', 'Icon/Share': 'share',
         'Icon/Chevron Right': 'chevron', 'Icon/Sort': 'sort', 'Icon/Spinner': 'spinner',
         'Icon/Verified': 'verified', 'Icon/Lock': 'lock', 'Indicator/Online': 'online', 'Icon/Pass': 'pass', 'Icon/Heart': 'heart'}
COLOR_ICONS = {'verified', 'online', 'pass', 'heart'}       # multi-colour glyphs, shown as images
TONES = {'Primary': 'tone-primary', 'Active': 'tone-active', 'Inactive': 'tone-inactive', 'On media': 'tone-media'}
EFFECT_STYLES = {'Shadow/Text on media': ('shadow', '0px 1px 2px rgb(0 0 0 / 0.35)'), 'Shadow/Raised': ('shadow', 'var(--shadow-raised)'), 'Shadow/Card': ('shadow', 'var(--shadow-card)'),
                 'Blur/Background 24': ('backdrop', 'var(--blur-24)'), 'Blur/Background 12': ('backdrop', 'var(--blur-12)')}
GRADIENT_TOKENS = {
    ('var(--color-gold-edge)', 'var(--color-gold-center)', 'var(--color-gold-edge)'): 'var(--gradient-gold)',
    ('var(--color-gold-soft)', 'var(--color-gold-soft-center)', 'var(--color-gold-soft)'): 'var(--gradient-gold-soft)',
    ('var(--color-notify-start)', 'var(--color-notify-end)'): 'var(--gradient-notify)',
}

# Text that Figma draws with an iOS vibrancy blend mode; plain CSS needs the visible colour.
TEXT_COLOR = {'9:41 AM': '#ffffff'}

TOKENS_CSS = open(os.path.join(ROOT, 'css', 'tokens.css')).read()
ALPHA_TOKENS = set(re.findall(r'(--color-[a-z0-9-]+):\s*rgb\([^)]*/', TOKENS_CSS))

# ---------------------------------------------------------------- helpers

def px(v):
    v = round(v, 2)
    return f'{int(v)}px' if v == int(v) else f'{v}px'


DERIVED = {}   # id -> spec, filled per version from prototypes.json "derive"
PEOPLE_CONF = {}


def load(sid):
    if sid in DERIVED:
        return load_derived(sid, DERIVED[sid])
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
    if n.get('char'):
        return (f'<span class="n emoji-char" data-name="{name}" style="{box};font-size:{px(round(h * 0.86))};line-height:{px(h)};'
                f'text-align:center">{n["char"]}</span>')
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
            if interactive and n.get('_go') and out:
                extra = ''.join(f' {k}="{esc(str(v))}"' for k, v in n['_go'].items())
                out = re.sub(r'^<(\w+) class="n', lambda m: f'<{m.group(1)}{extra} class="n hot', out, count=1)
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
        if r and n['t'] != 'TEX':   # blurred children escape overflow+radius in Chromium; clip-path holds the corners
            st.append(f'clip-path:inset(0 round {r})')
    if n.get('_blur'):
        st.append(f"filter:blur({n['_blur']}px)")
        if not (n.get('clip') and r):
            st.append('clip-path:inset(0)')

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
    if shadows and n['t'] == 'TEX':   # a text shadow follows the glyphs, not the text box
        st.append('text-shadow:' + ', '.join(re.sub(r'^(\S+ \S+ \S+) \S+ ', r'\1 ', sh) for sh in shadows if not sh.startswith('inset') and not sh.startswith('var(')))
    elif shadows:
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
        svg = svg.replace('<svg ', '<svg style="display:block" preserveAspectRatio="none" ', 1)
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
    if n.get('c') in TEXT_COLOR:  # iOS kit text that Figma renders with vibrancy (blend mode)
        st.append(f"color:{TEXT_COLOR[n['c']]}")
    elif first.get('fill'):
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
    weight = {'Regular': 400, 'Medium': 500, 'Semibold': 600, 'SemiBold': 600, 'Bold': 700, 'ExtraBold': 700}.get(s.get('fw'), 400)
    family = "-apple-system, BlinkMacSystemFont, 'SF Pro Text', system-ui, sans-serif" if 'SF' in fam else 'var(--font-family-base)'
    lh = f";line-height:{px(s['lh'])}" if s.get('lh') else ''
    return f"font-family:{family};font-weight:{weight};font-size:{px(s.get('fs', 14))}{lh}"


def big_like(x):
    """H1: the Like reaction is a 28px heart, no chip, no label."""
    for top in [c for c in x.get('ch', []) if c.get('n') == 'Top']:
        for i, rr in enumerate(top.get('ch', [])):
            if rr.get('n') != 'Reaction':
                continue
            icon = next(find_all(rr, 'Leading'), None)
            if icon:
                top['ch'][i] = {**icon, 'n': 'Like', 'x': rr['x'] + rr['w'] - 28, 'y': top['y'] + (top['h'] - 28) // 2, 'w': 28, 'h': 28}
    for c in x.get('ch', []):
        big_like(c)


SEAL_SVG = '<svg width="16" height="16" viewBox="-1 -1 18 18" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M8.00 1.30Q10.15 -0.02 11.35 2.20Q13.87 2.13 13.80 4.65Q16.02 5.85 14.70 8.00Q16.02 10.15 13.80 11.35Q13.87 13.87 11.35 13.80Q10.15 16.02 8.00 14.70Q5.85 16.02 4.65 13.80Q2.13 13.87 2.20 11.35Q-0.02 10.15 1.30 8.00Q-0.02 5.85 2.20 4.65Q2.13 2.13 4.65 2.20Q5.85 -0.02 8.00 1.30Z" fill="#15B9F3" stroke="white" stroke-width="1.2" stroke-linejoin="round"/><path d="M5.1 8.2L7.1 10.1L10.9 6.1" stroke="white" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>'


def pin_check(x):
    """The verified pin on a flag badge is a blue seal with a white check, as in the app."""
    for i, c in enumerate(x.get('ch', [])):
        if c.get('n') == 'Avatar/Size7':
            x['ch'][i] = {'n': 'Verified seal', 't': 'VEC', 'x': c['x'], 'y': c['y'], 'w': c['w'], 'h': c['h'], 'svg': SEAL_SVG}
        else:
            pin_check(c)


EXTRA_CARDS = [  # people added to every Liked You grid
    {'name': 'Marta', 'age': '29', 'photo': 'marta001', 'flag': 'brazil', 'verified': True, 'online': False, 'tag': False},
    {'name': 'Mei', 'age': '31', 'photo': 'mei00001', 'flag': 'norway', 'verified': False, 'online': False, 'tag': False},
    {'name': 'Inês', 'age': '26', 'photo': 'ines0001', 'flag': 'brazil', 'verified': True, 'online': True, 'tag': True},
    {'name': 'Sofia', 'age': '33', 'photo': 'ba02f2b3', 'flag': 'brazil', 'verified': True, 'online': False, 'tag': False},
]


def shift(x, dx, dy):
    x = dict(x); x['x'] += dx; x['y'] += dy
    if 'ch' in x:
        x['ch'] = [shift(c, dx, dy) for c in x['ch']]
    return x


def more_cards(x, count, blur_tmpl=None, gold=False):
    for grid in list(find_all(x, 'Likes Grid')):
        cards = [c for c in grid.get('ch', []) if c.get('n', '').startswith('Like Card')]
        if not cards or any(c['n'].endswith(EXTRA_CARDS[0]['name']) for c in cards):
            continue
        tmpl = next((c for c in cards if 'Blurred' in (c.get('variant') or '')), None)
        if tmpl is None:
            tmpl = cards[0] if (gold or not blur_tmpl) else blur_tmpl
        x0 = min(c['x'] for c in cards); y0 = min(c['y'] for c in cards)
        for k, p in enumerate(EXTRA_CARDS[:count]):
            i = len(cards) + k
            card = shift(json.loads(json.dumps({k: v for k, v in tmpl.items() if k != '_go'})), x0 + (i % 2) * 189 - tmpl['x'], y0 + (i // 2) * 268 - tmpl['y'])
            card['n'] = 'Like Card · ' + p['name']
            def fix(n):
                kids = []
                for c in n.get('ch', []):
                    nm = c.get('n')
                    if nm in ('Reaction', 'Like') or (nm == 'Interest Tag' and not p['tag']):
                        continue
                    if (nm == 'Verified' and not p['verified']) or (nm == 'Online' and not p['online']):
                        continue
                    if nm == 'Photo':
                        c['f'] = [{**f, 'h': p['photo'], 'sm': 'FILL'} if f.get('k') == 'i' else f for f in c.get('f', [])]
                    if nm == 'Flag' and c.get('leaf'):
                        c['swap'] = p['flag']
                    if c.get('t') == 'TEX':
                        t = c.get('c', '')
                        if t.endswith(',') and t[:-1].isalpha():
                            c['c'] = p['name'] + ','
                        elif t.isdigit() and len(t) == 2:
                            c['c'] = p['age']
                        for sg in c.get('seg', []):
                            sg.pop('c', None)
                    fix(c); kids.append(c)
                n['ch'] = kids
            fix(card)
            grid['ch'].append(card)
        grid['h'] = max(c['y'] + c['h'] for c in grid['ch']) - grid['y']


def no_card_flags(x):
    for c in list(x.get('ch', [])):
        if c.get('n', '').startswith('Like Card'):
            stack = [c]
            while stack:
                n = stack.pop()
                n['ch'] = [k for k in n.get('ch', []) if not (k.get('n') == 'Flag' and k.get('leaf'))]
                stack.extend(n['ch'])
        else:
            no_card_flags(c)


def replace_texts(x, rules):
    for scope, old, new in rules:
        roots = list(find_all(x, scope)) if scope else [x]
        for root in roots:
            stack = [root]
            while stack:
                n = stack.pop(); stack.extend(n.get('ch', []))
                if n.get('t') == 'TEX' and n.get('c') == old:
                    n['c'] = new
                    for sg in n.get('seg', []):
                        if 'c' in sg: sg['c'] = sg['c'].replace(old, new)
                    if (n.get('ta') == 'C' or n.get('ar') == 'W') and len(new) > len(old):   # an auto-width or centred line keeps its centre
                        cx = n['x'] + n['w'] / 2
                        n['w'] = max(n['w'], text_w(new, 12, '600') + 24); n['x'] = round(cx - n['w'] / 2); n['ta'] = 'C'


RING_SVG = '<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="8" cy="8" r="5" stroke="#26FC0F" stroke-width="2"/></svg>'
ONLINE_LEAF = {'n': 'Indicator/Online', 't': 'INS', 'comp': 'Indicator/Online', 'leaf': 1, 'glyph': {'k': 's', 'v': 'var(--color-status-online)'}}
CITY = {'Ayesha': ('Porto', 'Portugal'), 'Chloé': ('Port Louis', 'Mauritius'), 'Lena': ('São Paulo', 'Brazil'), 'Marta': ('Rio de Janeiro', 'Brazil'), 'Mei': ('Oslo', 'Norway'), 'Inês': ('Belo Horizonte', 'Brazil'), 'Sofia': ('Curitiba', 'Brazil'), 'Nora': ('Salvador', 'Brazil')}  # Basics · 📍 and About me
PEOPLE = {  # one source of truth for every Liked You card; interest = shared interest chip, goal = chip under the name
    'Ayesha': {'age': '36', 'flag': 'portugal', 'photo': 'cb9c849b', 'type': 'hello', 'verified': True, 'status': 'online',
               'interest': ('💪', 'Healthy lifestyle'), 'goal': ('💍', 'Get married')},
    'Chloé': {'age': '30', 'flag': 'mauritius', 'photo': '8d73a736', 'type': 'hello', 'verified': True, 'status': 'today',
              'interest': ('🚴', 'Cycling'), 'goal': ('🌍', 'See the world')},
    'Lena': {'age': '27', 'flag': 'brazil', 'photo': 'ba02f2b3', 'type': 'like', 'verified': False, 'status': 'online',
             'interest': ('🚴', 'Cycling'), 'goal': ('🌍', 'See the world')},
    'Marta': {'age': '29', 'flag': 'brazil', 'photo': '87bdbb2e', 'type': 'hello', 'verified': True, 'status': None,
              'interest': ('💪', 'Healthy lifestyle'), 'goal': ('💬', 'Make friends')},
    'Mei': {'age': '31', 'flag': 'norway', 'photo': '95c21628', 'type': 'like', 'verified': False, 'status': 'today',
            'interest': ('🚴', 'Cycling'), 'goal': ('🏡', 'Start a family')},
    'Inês': {'age': '26', 'flag': 'brazil', 'photo': '08ff3a55', 'type': 'hello', 'verified': True, 'status': 'online',
             'interest': ('💪', 'Healthy lifestyle'), 'goal': ('💬', 'Make friends')},
    'Sofia': {'age': '33', 'flag': 'brazil', 'photo': '317076df', 'type': 'hello', 'verified': True, 'status': 'today',
              'interest': ('🚴', 'Cycling'), 'goal': ('💍', 'Get married')},
    'Nora': {'age': '28', 'flag': 'brazil', 'photo': 'c1a99c0f', 'type': 'hello', 'verified': True, 'status': None,
             'interest': ('💪', 'Healthy lifestyle'), 'goal': ('💬', 'Make friends')},
}


FONT_W = json.load(open(os.path.join(ROOT, 'tools', 'font_widths.json')))   # Open Sans advance widths per em, by weight


def text_w(t, size=12, weight='700'):
    """Rendered width of a one-line label in Open Sans (names on cards are Body/12 Bold)."""
    table = FONT_W[weight]
    return int(round(sum(table.get(ch, 0.6) for ch in t) * size))


def set_chip(chip, char, label, size=12):
    """Interest Tag / Info Chip: new emoji and label, width follows the label."""
    emo = next((k for k in chip.get('ch', []) if k.get('n') == 'Emoji'), None)
    lab = next((k for k in chip.get('ch', []) if k.get('t') == 'TEX'), None)
    bg = next((k for k in chip.get('ch', []) if k.get('n') == 'Background'), None)
    av = next((k for k in chip.get('ch', []) if k.get('n') == 'Shared Avatar'), None)
    if emo:
        emo.pop('ch', None); emo['leaf'] = 1; emo['char'] = char
    if lab:
        pad_r = chip['x'] + chip['w'] - (lab['x'] + lab['w'])
        lab['c'] = label; lab['w'] = text_w(label, size, '600') + 1
        for sg in lab.get('seg', []):
            sg.pop('c', None)
        chip['w'] = lab['x'] + lab['w'] + pad_r - chip['x']
        if bg:
            bg['w'] = chip['w']
        if av:
            av['x'] = chip['x'] + chip['w'] - 9


def load_derived(sid, spec):
    """A screen made from another one: same layout, another person (and a few extra layers)."""
    scr = json.loads(json.dumps(load(spec['from'])))
    scr['id'] = sid
    for src, name in spec.get('copy', []):
        node = next(find_all(load(src), name), None)
        if node:
            scr.setdefault('ch', []).append(json.loads(json.dumps(node)))
    if spec.get('pills_from'):   # H2: after today's free Hello back the pills lock (template pill from another screen)
        tmpl = next((n for n in load(spec['pills_from']).get('ch', []) if n.get('n', '').startswith('Hello back · ')), None)
        if tmpl:
            for i, n in enumerate(scr.get('ch', [])):
                if n.get('n', '').startswith('Hello back · '):
                    k = shift(json.loads(json.dumps(tmpl)), n['x'] - tmpl['x'], n['y'] - tmpl['y']); k['n'] = n['n']
                    scr['ch'][i] = k
    if spec.get('like_chip'):
        for n in _walk(scr):
            if n.get('n') == 'Info Chip':
                for k in _walk(n):
                    if k.get('n') == 'Emoji' or (k.get('leaf') and k.get('comp', '').startswith('Emoji/Waving')):
                        k['comp'] = 'Icon/Heart'; k['leaf'] = 1; k.pop('ch', None); k['glyph'] = {'k': 's', 'v': 'var(--color-accent-heart)'}
                    if k.get('t') == 'TEX' and k.get('c') == 'sent you a Hello':
                        k['c'] = 'liked you'; k['w'] = text_w('liked you', 10, '600') + 2
                        for sg in k.get('seg', []): sg.pop('c', None)
                lab = next((k for k in _walk(n) if k.get('t') == 'TEX'), None)
                if lab:   # the chip hugs the shorter label and stays centred
                    nw = lab['x'] + lab['w'] + 8 - n['x']; dx = round((n['w'] - nw) / 2)
                    for k in n.get('ch', []):
                        if k.get('n') == 'Background': k['w'] = nw
                    n['w'] = nw
                    for k in _walk(n): k['x'] += dx
    drop = set(spec.get('drop', []))
    if drop:
        def _drop(n):
            n['ch'] = [k for k in n.get('ch', []) if k.get('n') not in drop]
            for k in n['ch']:
                _drop(k)
        _drop(scr)
    to = spec.get('person')
    if to:
        base = spec.get('base', 'Ayesha')
        people = {k: {**v, **PEOPLE_CONF.get(k, {})} for k, v in PEOPLE.items()}
        pb, pt = people[base], people[to]
        hb = spec.get('base_photo', 'cb9c849b'); fb = spec.get('base_flag', 'portugal')
        scope = [x for name in spec.get('person_scope', []) for x in find_all(scr, name)] or [scr]   # only these layers change person
        for n in (m for root in scope for m in _walk(root)):
            if n.get('f'):
                n['f'] = [{**f, 'h': pt['photo']} if f.get('k') == 'i' and f.get('h') == hb else f for f in n['f']]
            if n.get('n') == 'Flag' and n.get('leaf') and (n.get('swap') or '').lower() == fb:
                n['swap'] = pt['flag']
            if n.get('t') == 'TEX' and to in CITY and base in CITY and CITY[base][0] in n.get('c', ''):
                cb, ct = CITY[base], CITY[to]
                n['c'] = n['c'].replace(f'{cb[0]}, {cb[1]}', f'{ct[0]}, {ct[1]}').replace(f'in {cb[0]}.', f'in {ct[0]}.')
                for sg in n.get('seg', []):
                    sg.pop('c', None)
            if n.get('t') == 'TEX' and base in n.get('c', ''):
                n['c'] = n['c'].replace(f"{base}, {pb['age']}", f"{to}, {pt['age']}").replace(f'{base}, 36', f"{to}, {pt['age']}").replace(base, to)
                for sg in n.get('seg', []):
                    sg.pop('c', None)
            if n.get('n') == 'Name' and n.get('t') == 'TEX' and n.get('w'):
                n['w'] = text_w(n['c'], 18, '600')
            if n.get('n') == 'Interest Tag' and pt.get('interest'):
                set_chip(n, *pt['interest'])
        if not pt.get('verified'):   # no Verified icon and no seal on the flag
            for n in _walk(scr):
                n['ch'] = [k for k in n.get('ch', []) if not (k.get('comp') == 'Icon/Verified' or k.get('n') == 'Verified seal')]
            for n in _walk(scr):
                if n.get('n') in ('Profile Header', 'Name Row'):
                    n['ch'] = [k for k in n.get('ch', []) if k.get('n') != 'Verified']
                if n.get('n') == 'Flag Badge':
                    n['ch'] = [k for k in n.get('ch', []) if not k.get('n', '').startswith('Avatar/')]
        if spec.get('signals'):   # preview sheet: the status label and the reaction follow the person
            st = pt.get('status')
            for n in _walk(scr):
                if n.get('n') == 'Status':
                    if st == 'today':
                        ind = next((k for k in n.get('ch', []) if k.get('n', '').startswith('Indicator')), None)
                        lab = next((k for k in n.get('ch', []) if k.get('t') == 'TEX'), None)
                        if ind:
                            n['ch'][n['ch'].index(ind)] = {'n': 'Indicator/Active today', 't': 'VEC', **{k: ind[k] for k in ('x', 'y', 'w', 'h')}, 'svg': RING_SVG}
                        if lab:
                            lab['c'] = 'Active today'; lab['w'] = text_w('Active today', 12, '600') + 2
                            for sg in lab.get('seg', []): sg.pop('c', None)
            for host in _walk(scr):   # the status sits right after the last signal in its row
                stn = next((k for k in host.get('ch', []) if k.get('n') == 'Status'), None)
                if stn:
                    row = [k for k in host['ch'] if k is not stn and k.get('n') in ('Name (hidden)', 'Age', 'Verified') and abs((k['y'] + k['h'] / 2) - (stn['y'] + stn['h'] / 2)) < 12]
                    if row:
                        nx = max(k['x'] + k['w'] for k in row) + 8
                        dx = nx - stn['x']
                        if dx < 0:
                            for k in _walk(stn): k['x'] += dx
            if st not in ('online', 'today'):
                for n in _walk(scr):
                    n['ch'] = [k for k in n.get('ch', []) if k.get('n') != 'Status']
            for n in _walk(scr):
                if n.get('n') == 'Age':
                    for k in _walk(n):
                        if k.get('t') == 'TEX' and k.get('c') == pb['age']:
                            k['c'] = pt['age']
                            for sg in k.get('seg', []): sg.pop('c', None)
            if pt.get('type') == 'like':
                for n in _walk(scr):
                    if n.get('n') == 'Reaction · Hello':
                        n['n'] = 'Reaction · Like'; n['comp'] = 'Icon/Heart'; n['leaf'] = 1; n.pop('ch', None)
                        n['glyph'] = {'k': 's', 'v': 'var(--color-accent-heart)'}
                    if n.get('t') == 'TEX' and n.get('c', '').startswith('See who sent this Hello'):
                        n['c'] = n['c'].replace('See who sent this Hello', 'See who sent this Like', 1)
                        for sg in n.get('seg', []):
                            if 'c' in sg: sg['c'] = sg['c'].replace('See who sent this Hello', 'See who sent this Like')
        for n in _walk(scr):   # Verified follows the longer or shorter name; a centred row stays centred
            if n.get('n') == 'Name Row':
                nm = next((k for k in n['ch'] if k.get('t') == 'TEX'), None)
                v = next((k for k in n['ch'] if k.get('n') == 'Verified' or k.get('comp') == 'Icon/Verified'), None)
                if nm and nm.get('n') != 'Name':
                    sg0 = (nm.get('seg') or [{}])[0]
                    ts = sg0.get('ts', '') or (f"x/{int(sg0['fs'])} {sg0.get('fw', 'SemiBold')}" if sg0.get('fs') else '')
                    m = re.search(r'/(\d+) (\w+)', ts)
                    if m:
                        wt = {'Regular': '400', 'Medium': '600', 'SemiBold': '600', 'Semibold': '600', 'Bold': '700'}.get(m.group(2), '600')
                        old_w = nm['w']; nm['w'] = text_w(nm['c'], int(m.group(1)), wt if wt in FONT_W else '600')
                        if v:
                            v['x'] = nm['x'] + nm['w'] + (v['x'] - nm['x'] - old_w)
                        if abs(n['x'] + n['w'] / 2 - 201) < 3:   # centred on the screen
                            right = max(k['x'] + k['w'] for k in n['ch']); left = min(k['x'] for k in n['ch'])
                            dx = round(201 - (left + right) / 2)
                            n['ch'] = [shift(k, dx, 0) for k in n['ch']]
                elif nm and v:
                    v['x'] = nm['x'] + nm['w'] + 6
        hdr = next(find_all(scr, 'Profile Header'), None)
        chip = hdr and next(find_all(hdr, 'Info Chip'), None)
        if chip and spec.get('like_pill'):
            sheet = next(find_all(scr, 'Profile Sheet'), None)
            bar = next(find_all(scr, 'Action Bar'), None)
            pas = bar and next(find_all(bar, 'Pass'), None)
            pill = json.loads(json.dumps(chip)); pill['n'] = 'Like Pill'
            set_chip(pill, '🤍', 'sent you a Like', 10)
            for k in pill['ch']:
                if k.get('n') == 'Background':
                    k['f'] = [{'k': 's', 'v': 'var(--color-accent-like)'}]
            pill = shift(pill, round(bar['x'] + bar['w'] / 2 - pill['w'] / 2) - pill['x'], pas['y'] - 32 - pill['y'])
            if sheet:
                sheet['ch'].append(pill)
        if chip and spec.get('goal_chip') and pt.get('goal'):
            set_chip(chip, *pt['goal'], 10)
    return scr


def ring_leaves(x):
    for i, c in enumerate(x.get('ch', [])):
        if c.get('leaf') and c.get('comp') == 'Indicator/Active today':
            x['ch'][i] = {'n': 'Indicator/Active today', 't': 'VEC', 'x': c['x'], 'y': c['y'], 'w': c['w'], 'h': c['h'], 'svg': RING_SVG}
        else:
            ring_leaves(c)


def _walk(x):
    yield x
    for c in x.get('ch', []):
        yield from _walk(c)


def set_card(card, p, revealed, cs, gold):
    """Rewrite one card (a fresh copy of a template) for person p."""
    name = card.pop('_person')
    def strip(node, pred):
        node['ch'] = [k for k in node.get('ch', []) if not pred(k)]
        for k in node['ch']:
            strip(k, pred)
    for n in _walk(card):
        if n.get('n') == 'Photo':
            n['f'] = [{**f, 'h': p['photo'], 'sm': 'FILL'} if f.get('k') == 'i' else f for f in n.get('f', [])]
        if n.get('n') == 'Flag' and n.get('leaf'):
            n['swap'] = p['flag']
        if n.get('t') == 'TEX':
            t = n.get('c', '')
            if t.endswith(',') and t[:-1].replace('é', 'e').replace('ê', 'e').isalpha():
                n['c'] = name + ','
            elif t.isdigit() and len(t) == 2:
                n['c'] = p['age']
            for sg in n.get('seg', []):
                sg.pop('c', None)
        if n.get('n') == 'Interest Tag' and p.get('interest'):
            set_chip(n, *p['interest'])
    if not revealed and not cs.get('hello_flags'):
        strip(card, lambda k: k.get('n') == 'Flag' and k.get('leaf'))
    if p['type'] != 'like':
        strip(card, lambda k: k.get('n') == 'Like' and k.get('leaf'))
    if not p['verified']:
        strip(card, lambda k: k.get('n') == 'Verified')
    else:
        pm = next((n for n in _walk(card) if n.get('n') == 'Profile Meta'), None)
        if pm and not any(k.get('n') == 'Verified' for k in pm.get('ch', [])):
            na = next((k for k in pm.get('ch', []) if k.get('n') in ('Name & Age', 'Name')), None)
            if na:
                w = int(7.6 * (len(name) + len(p['age']) + 2)) if na['n'] == 'Name & Age' else na['w']
                pm.setdefault('ch', []).insert(1, {'n': 'Verified', 't': 'INS', 'comp': 'Icon/Verified', 'leaf': 1, 'glyph': {'k': 's', 'v': 'var(--color-status-verified)'},
                                                   'x': na['x'] + w + 4, 'y': pm['y'], 'w': 16, 'h': 16})
    st = p['status']
    if cs.get('style') == 'label':
        strip(card, lambda k: k.get('n') in ('Online', 'Active today') and k.get('leaf'))
        info = next((n for n in _walk(card) if n.get('n') == 'Info'), None)
        row = next((k for k in (info or {}).get('ch', []) if k.get('n') == 'Status'), None)
        if row is not None:
            if not st:
                dy = row['h'] + 8
                info['ch'] = [k for k in info['ch'] if k is not row]
                for k in info['ch']:
                    for n in _walk(k):
                        n['y'] += dy
            else:
                ind = next((k for k in row.get('ch', []) if k.get('n', '').startswith('Indicator')), None)
                lab = next((k for k in row.get('ch', []) if k.get('t') == 'TEX'), None)
                if ind:
                    box = {k: ind[k] for k in ('x', 'y', 'w', 'h')}
                    new = {**ONLINE_LEAF, **box} if st == 'online' else {'n': 'Indicator/Active today', 't': 'VEC', **box, 'svg': RING_SVG}
                    row['ch'][row['ch'].index(ind)] = new
                if lab:
                    lab['c'] = 'Online' if st == 'online' else 'Active today'
                    lab['w'] = int(7 * len(lab['c'])) + 2
                    for sg in lab.get('seg', []):
                        sg.pop('c', None)
    else:
        if st != 'online':
            strip(card, lambda k: k.get('n') in ('Online', 'Active today') and (k.get('leaf') or k.get('t') == 'VEC'))
        else:
            pm = next((n for n in _walk(card) if n.get('n') == 'Profile Meta'), None)
            if pm and not any(k.get('n') == 'Online' for k in pm.get('ch', [])):
                last = max(pm.get('ch', []), key=lambda k: k['x'] + k['w'])
                pm['ch'].append({**ONLINE_LEAF, 'n': 'Online', 'x': last['x'] + last['w'] + 4, 'y': pm['y'], 'w': 16, 'h': 16})



def pack_meta(card):
    """Name & Age hugs the text; Verified, Online and the other icons follow it, 4 px apart, with no gaps."""
    for pm in [n for n in _walk(card) if n.get('n') == 'Profile Meta']:
        kids = pm.get('ch', [])
        na = next((k for k in kids if k.get('n') == 'Name & Age'), None)
        if na:
            nm_t = next((k for k in na.get('ch', []) if k.get('n') == 'Name'), None)
            ag_t = next((k for k in na.get('ch', []) if k.get('n') == 'Age'), None)
            if nm_t and ag_t:
                nm_t['w'] = text_w(nm_t['c']); ag_t['x'] = nm_t['x'] + nm_t['w'] + 4; ag_t['w'] = text_w(ag_t['c']) + 1
                na['w'] = ag_t['x'] + ag_t['w'] - na['x']
        first = na or next((k for k in kids if k.get('n') == 'Name'), None)
        if not first:
            continue
        x = first['x'] + first['w'] + 4
        for k in sorted([k for k in kids if k is not first and k['x'] >= first['x']], key=lambda k: k['x']):
            dx = x - k['x']
            for m in _walk(k):
                m['x'] += dx
            x += k['w'] + 4


def reflow_gone(scr, grid, gone):
    """People who already became a Bump leave the grid; the rest move up, Hello back pills travel with their cards."""
    if not gone:
        return
    who = lambda c: c.get('_who', c['n'].split(' · ', 1)[1])
    cards = sorted([c for c in grid['ch'] if c.get('n', '').startswith('Like Card · ')], key=lambda c: (c['y'], c['x']))
    slots = [(c['x'], c['y']) for c in cards]
    keep = [c for c in cards if who(c) not in gone]
    others = [c for c in grid['ch'] if not c.get('n', '').startswith('Like Card · ')]
    moved = [shift(c, sx - c['x'], sy - c['y']) for c, (sx, sy) in zip(keep, slots)]
    for old_c, new_c in zip(keep, moved):
        for i2, k in enumerate(scr.get('ch', [])):
            if k.get('n') == 'Hello back · ' + who(old_c):
                scr['ch'][i2] = shift(k, new_c['x'] - old_c['x'], new_c['y'] - old_c['y'])
    scr['ch'] = [k for k in scr.get('ch', []) if not (k.get('n', '').startswith('Hello back · ') and k['n'].split(' · ', 1)[1] in gone)]
    grid['ch'] = others + moved


def card_states(scr, conf, sid):
    cs = conf.get('card_states')
    if not cs:
        for grid in list(find_all(scr, 'Likes Grid')):
            reflow_gone(scr, grid, set(conf.get('gone', {}).get(sid, [])))
        return
    people = {k: {**v, **conf.get('people', {}).get(k, {})} for k, v in PEOPLE.items()}
    alias = cs.get('alias', {})
    tmpl = {}
    for k in ('blurred', 'revealed'):
        tsid, tname = cs[k]
        t = next(find_all(load(tsid), tname), None)
        ring_leaves(t)
        tmpl[k] = t
    heart = None
    if cs.get('heart'):
        hsid, hcard, hname = cs['heart']
        hc = next(find_all(load(hsid), hcard), None)
        hn = next(find_all(hc, hname), None)
        heart = {**hn, 'x': hn['x'] - hc['x'], 'y': hn['y'] - hc['y']}
    if cs.get('chips'):   # as in the app: every card keeps its shared-interest chip
        b = json.loads(json.dumps(tmpl['blurred'])); r = tmpl['revealed']
        b['ch'] = [k for k in b['ch'] if k.get('n') != 'Blur']
        info = next(k for k in b['ch'] if k.get('n') == 'Info')
        pm_b = next(k for k in info['ch'] if k.get('n') == 'Profile Meta')
        pm_r = next(find_all(r, 'Profile Meta'))
        pm_new = shift(json.loads(json.dumps(pm_r)), pm_b['x'] - pm_r['x'], pm_b['y'] - pm_r['y'])
        info['ch'][info['ch'].index(pm_b)] = pm_new
        tmpl['revealed'] = b
    gold = sid in conf.get('gold', [])
    opened = set(conf.get('reveal_on', {}).get(sid, []))     # people already revealed on this screen
    order = conf.get('grid_names', {}).get(sid)             # names by grid order, where the dump repeats a name
    for grid in list(find_all(scr, 'Likes Grid')):
        k = -1
        for i, c in enumerate(grid.get('ch', [])):
            if not c.get('n', '').startswith('Like Card · '):
                continue
            k += 1
            nm = c['n'].split(' · ', 1)[1]
            nm = order[k] if order and k < len(order) and nm in alias else alias.get(nm, nm)
            p = people.get(nm)
            if not p:
                continue
            revealed = gold or p['type'] == 'like' or nm in opened
            t = tmpl['revealed' if revealed else 'blurred']
            card = shift(json.loads(json.dumps({k: v for k, v in t.items() if k != '_go'})), c['x'] - t['x'], c['y'] - t['y'])
            card['n'] = 'Like Card · ' + nm
            card['_person'] = nm
            set_card(card, p, revealed, cs, gold)
            pack_meta(card)
            card['_who'] = nm
            if heart and p['type'] == 'like' and not any(k.get('n') == 'Like' for k in card['ch']):
                card['ch'].append({**heart, 'x': card['x'] + heart['x'], 'y': card['y'] + heart['y']})
            if p['type'] == 'like' and not gold:
                card['_nowire'] = 1
            grid['ch'][i] = card
        reflow_gone(scr, grid, set(conf.get('gone', {}).get(sid, [])))
    # H2: the Hello back pill only on blurred Hellos
    scr['ch'] = [k for k in scr.get('ch', []) if not (k.get('n', '').startswith('Hello back · ') and people.get(k['n'].split(' · ', 1)[1], {}).get('type') == 'like')]


def tweaks(scr, conf, sid=None):
    mc = conf.get('more_cards')
    if mc:
        n = mc.get(sid, mc.get('*', 0)) if isinstance(mc, dict) else mc
        if n:
            bt = None
            if conf.get('blur_card'):
                bsid, bname = conf['blur_card']
                bt = next(find_all(load(bsid), bname), None)
            more_cards(scr, n, bt, sid in conf.get('gold', []))
    if conf.get('no_card_flags'):
        no_card_flags(scr)
    if conf.get('replace_all'):
        replace_texts(scr, conf['replace_all'])
    if conf.get('big_like'):
        big_like(scr)
    if conf.get('pin_check'):
        pin_check(scr)
    card_states(scr, conf, sid)
    ring_leaves(scr)


def render_skipped(n, ctx):
    name = n['n']
    if name == 'Lock Screen':
        return f'<div class="n lockscreen" data-name="Lock Screen" style="left:0;top:0;width:{px(n["w"])};height:{px(n["h"])}"></div>'
    src = ctx.conf.get('backgrounds', {}).get(name)
    if not src:
        return ''
    scr = load(src)
    tweaks(scr, ctx.conf, src)
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
        if w['to'] == 'BACK':
            d = None
        else:
            d = ctx.dest(w['to'])
            if not d:
                continue
        grid_ids = {id(m) for g in find_all(scr, 'Likes Grid') for m in _walk(g)}
        hits = sorted(find_all(scr, w['node']), key=lambda m: id(m) in grid_ids)   # a button, not the heart on a card
        if not hits:
            print(f"  ! {scr['id']}: no layer named {w['node']!r}")
        for hit in hits if w.get('all') else hits[:1]:
            if d is None:
                hit['_go'] = {'data-back': '1', 'data-tt': w.get('tt', 'dissolve'), 'data-dir': w.get('dir', '')}
                fb = ctx.conf.get('_from', {}).get(scr.get('id'))
                if fb and ctx.dest(fb):
                    hit['_go']['data-fallback'] = ctx.dest(fb)
                continue
            hit['_go'] = {'data-go': d, 'data-tt': w.get('tt', 'dissolve'), 'data-dir': w.get('dir', ''),
                          'data-td': str(w.get('td', 0.3))}
            if 'ctx' in w:   # remember what the user came for (a card → that profile after Gold)
                hit['_go']['data-ctx'] = ctx.dest(w['ctx']) or '' if w['ctx'] else ''
            if w.get('go_ctx'):   # after the purchase: go to what the user came for, else to data-go
                hit['_go']['data-go-ctx'] = '1'
            if w.get('toast'):
                hit['_go']['data-toast'] = '1'


# ---------------------------------------------------------------- page

def slug(s):
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')


def versions_nav(active):
    items = []
    for k, c in CONF.items():
        cur = ' aria-current="page"' if k == active else ''
        tag_cls = 'tag tag--gold' if c.get('tag', '').startswith('H') else 'tag'
        items.append(f'<a class="ver"{cur} href="../{k}/"><span class="{tag_cls}">{esc(c.get("tag", ""))}</span>'
                     f'<span class="ver-name">{esc(c.get("short", c["heading"]))}</span></a>')
    return '\n      '.join(items)


def build(key):
    conf = CONF[key]
    DERIVED.clear(); DERIVED.update(conf.get('derive', {}))
    PEOPLE_CONF.clear(); PEOPLE_CONF.update(conf.get('people', {}))
    ids = [s['id'] for s in conf['screens']]
    ctx = Ctx(conf, ids)
    # where each screen is usually opened from: the first screen, in list order, that leads to it (Back falls back to it)
    frm = {}
    for s0 in conf['screens']:
        outs = [w['to'] for w in conf.get('wiring', {}).get(s0['id'], [])] + ([s0['after'][1]] if s0.get('after') else [])
        for t in outs:
            if t != 'BACK' and t != s0['id']:
                frm.setdefault(t, s0['id'])
    conf['_from'] = frm
    sections, nav = [], []
    for i, s in enumerate(conf['screens']):
        scr = load(s['id'])
        for path, amount in conf.get('blur', {}).get(s['id'], {}).items():   # 'Promo Banner/Photo'
            nodes = [scr]
            for part in path.split('/'):
                nodes = [m for x in nodes for m in find_all(x, part)]
            for x in nodes:
                x['_blur'] = amount
        tweaks(scr, conf, s['id'])
        # wiring for the added cards copies the wiring of a template card
        explicit = {w['node'] for w in conf.get('wiring', {}).get(s['id'], [])}
        tw = conf.get('extra_like')
        if tw and conf.get('wiring', {}).get(s['id']):
            ws = conf['wiring'][s['id']]
            for w in [w for w in ws if w['node'] == tw]:
                for p in EXTRA_CARDS:
                    nm = 'Like Card · ' + p['name']
                    if not any(x['node'] == nm for x in ws):
                        ws.append({**w, 'node': nm})
        gt = conf.get('gold_toast')
        if gt and s['id'] in gt['on']:   # "Welcome to Gold": shown only when the user lands here right after buying
            nodes = list(find_all(scr, 'Gold Toast'))
            if not nodes:
                tmpl = next(find_all(load(gt['src'][0]), gt['src'][1]), None)
                if tmpl:
                    nodes = [json.loads(json.dumps(tmpl))]; scr.setdefault('ch', []).append(nodes[0])
            for n in nodes:
                n['_go'] = {**(n.get('_go') or {}), 'data-toast-node': '1'}
        apply_wiring(scr, conf.get('wiring', {}).get(s['id'], []), ctx)
        for n in _walk(scr):   # a revealed Like opens only where the wiring names it
            if n.get('_nowire') and n.get('n') not in explicit:
                n.pop('_go', None)
        if 'chats_dot' in conf and s['id'] not in conf['chats_dot']:   # the Chats dot appears only after a Bump
            for tab in find_all(scr, 'Tab Bar Item · Chats'):
                tab['ch'] = [k for k in tab.get('ch', []) if k.get('n') != 'Badge Dot']
        for target in conf.get('badge', {}).get(s['id'], []):   # copy the red dot from the Liked You tab
            src = next(find_all(scr, 'Tab Bar Item · Liked You'), None)
            dst = next(find_all(scr, target), None)
            dot = src and next(find_all(src, 'Badge Dot'), None)
            if dot and dst and not next(find_all(dst, 'Badge Dot'), None):
                dst.setdefault('ch', []).append({**dot, 'x': dot['x'] - src['x'] + dst['x'], 'y': dot['y'] - src['y'] + dst['y']})
        for scope, old, new in conf.get('text_override', {}).get(s['id'], []):
            roots = list(find_all(scr, scope)) if scope else [scr]
            for root in roots:
                stack = [root]
                while stack:
                    x = stack.pop(); stack.extend(x.get('ch', []))
                    if x.get('t') == 'TEX' and x.get('c') == old:
                        x['c'] = new
                        for sg in x.get('seg', []):
                            if 'c' in sg: sg['c'] = sg['c'].replace(old, new)
        for name, ms in conf.get('autohide', {}).get(s['id'], {}).items():
            for hit in find_all(scr, name):
                hit['_go'] = {**(hit.get('_go') or {}), 'data-autohide': str(ms)}
        after = ''
        for r in scr.get('rx', []):
            if r.get('tr') == 'AFTER_TIMEOUT':
                d = ctx.dest(r['d'])
                if d:
                    after = f' data-after="{int((r.get("to") or 1) * 1000)}" data-after-go="{d}" data-after-tt="{(r.get("tt") or "dissolve").lower()}"'
        if s.get('after'):
            ms, to = s['after'][:2]
            tt, dr = (s['after'][2:4] + ['dissolve', ''])[:2] if len(s['after']) > 2 else ('dissolve', '')
            d = ctx.dest(to)
            if d:
                after = f' data-after="{int(ms)}" data-after-go="{d}" data-after-tt="{tt}" data-after-dir="{dr}"'
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
        nav.append({'id': s['id'], 'title': title, 'slug': slug(title), 'note': note, **({'hidden': 1} if s.get('hidden') else {})})

    ver = int(max(os.path.getmtime(os.path.join(ROOT, f)) for f in ('css/tokens.css', 'css/ui.css', 'js/proto.js')))
    page = TEMPLATE.format(ver=ver, collapse='true' if conf.get('collapse') else 'false', 
        title=esc(conf['title']), heading=esc(conf['heading']), lead=conf['lead'],
        extra=conf.get('panel_html', ''), screens='\n'.join(sections),
        nav=json.dumps(nav, ensure_ascii=False), start=conf['screens'][0]['id'], versions=versions_nav(key))
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
<link rel="stylesheet" href="../css/tokens.css?v={ver}">
<link rel="stylesheet" href="../css/ui.css?v={ver}">
</head>
<body>
<main class="stage">
  <aside class="panel">
    <nav class="versions" aria-label="Versions">
      {versions}
    </nav>
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
  </aside>
  <div class="device-wrap"><div class="device" id="device">
{screens}
  </div></div>
</main>
<script>window.PROTO = {{ start: "{start}", screens: {nav}, collapse: {collapse} }};</script>
<script src="../js/proto.js?v={ver}"></script>
</body>
</html>
'''

if __name__ == '__main__':
    for k in CONF:
        build(k)
