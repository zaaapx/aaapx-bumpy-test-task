// Figma → JSON dump for tools/build.py.
// Run through the Figma MCP use_figma tool (or the Scripter plugin) with IDS set to the screens to export.
// Leaf components (icons, flags, emoji, logo, system bars) are not walked; build.py maps them to assets.
const IDS = __IDS__;
const LEAF = /^(Icon\/|Indicator\/|Emoji\/|Flag$|Logo\/|System Bar|HomeIndicator|Badge Dot|Page Dot|Skeleton)/;
const TONE_COLLECTION = 'VariableCollectionId:35:334';
const vcache = {};
async function vref(alias) {
  if (!alias) return null;
  const id = alias.id;
  if (!(id in vcache)) /* cache */ {
    const v = await figma.variables.getVariableByIdAsync(id);
    vcache[id] = v ? ((v.codeSyntax && v.codeSyntax.WEB) || v.name) : null;
  }
  return vcache[id];
}
const r2 = x => Math.round(x * 100) / 100;
const ri = x => Math.round(x);
const hex = c => '#' + [c.r, c.g, c.b].map(x => Math.round(x * 255).toString(16).padStart(2, '0')).join('');
async function paint(p) {
  if (p.visible === false) return null;
  const o = {}; if (p.opacity != null && p.opacity < 1) o.op = r2(p.opacity);
  if (p.type === 'SOLID') { o.k = 's'; o.c = hex(p.color); const vv = await vref(p.boundVariables && p.boundVariables.color); if (vv) { o.v = vv; if (vv.startsWith('var(')) delete o.c; } }
  else if (p.type.startsWith('GRADIENT')) {
    o.k = 'g'; if (p.type !== 'GRADIENT_LINEAR') o.gt = p.type; o.m = p.gradientTransform.map(r => r.map(r2));
    o.st = [];
    for (const s of p.gradientStops) { const q = { p: r2(s.position), c: hex(s.color), a: r2(s.color.a) }; const vv = await vref(s.boundVariables && s.boundVariables.color); if (vv) q.v = vv; o.st.push(q); }
  } else if (p.type === 'IMAGE') { o.k = 'i'; o.h = p.imageHash.slice(0, 8); o.sm = p.scaleMode; if (p.scaleMode === 'CROP') o.it = p.imageTransform.map(r => r.map(x => Math.round(x * 1000) / 1000)); }
  else return null;
  return o;
}
async function walk(n, ox, oy, leafHint) {
  if (n.visible === false) return null;
  const bb = n.absoluteBoundingBox || { x: n.x, y: n.y, width: n.width, height: n.height };
  const o = { n: n.name, t: n.type.slice(0, 3), x: ri(bb.x - ox), y: ri(bb.y - oy), w: ri(bb.width), h: ri(bb.height) };
  if ('opacity' in n && n.opacity < 1) o.op = r2(n.opacity);
  if ('cornerRadius' in n) {
    if (typeof n.cornerRadius === 'number') { if (n.cornerRadius) o.r = n.cornerRadius; }
    else o.r = [n.topLeftRadius, n.topRightRadius, n.bottomRightRadius, n.bottomLeftRadius];
  }
  if ('clipsContent' in n && n.clipsContent) o.clip = 1;
  if ('fills' in n && Array.isArray(n.fills) && n.fills.length && n.type !== 'TEXT') {
    const f = []; for (const p of n.fills) { const q = await paint(p); if (q) f.push(q); } if (f.length) o.f = f;
  }
  if ('strokes' in n && n.strokes.length && n.type !== 'TEXT') {
    const s = await paint(n.strokes[0]);
    if (s) {
      o.s = s; o.sa = n.strokeAlign;
      o.sw = typeof n.strokeWeight === 'number' ? n.strokeWeight : [n.strokeTopWeight, n.strokeRightWeight, n.strokeBottomWeight, n.strokeLeftWeight];
    }
  }
  if ('effects' in n && n.effects.length) {
    let es = null;
    if (n.effectStyleId && typeof n.effectStyleId === 'string') { const st = await figma.getStyleByIdAsync(n.effectStyleId); es = st && st.name; }
    if (es) o.fxs = es; else o.fx = n.effects.filter(e => e.visible !== false).map(e => ({ t: e.type.split('_')[0], r: e.radius, x: e.offset && e.offset.x, y: e.offset && e.offset.y, sp: e.spread, c: e.color && hex(e.color), a: e.color && r2(e.color.a) }));
  }
  if (n.explicitVariableModes && n.explicitVariableModes[TONE_COLLECTION]) {
    const col = await figma.variables.getVariableCollectionByIdAsync(TONE_COLLECTION);
    const m = col.modes.find(m => m.modeId === n.explicitVariableModes[TONE_COLLECTION]);
    if (m) o.tone = m.name;
  }
  if (n.reactions && n.reactions.length) {
    o.rx = [];
    for (const re of n.reactions) for (const a of (re.actions || [re.action]).filter(Boolean)) {
      if (a.type === 'NODE' && a.navigation === 'NAVIGATE' || a.type === 'BACK' || a.type === 'CLOSE')
        o.rx.push({ tr: re.trigger.type, to: re.trigger.timeout, a: a.type, d: a.destinationId, tt: a.transition && a.transition.type, td: a.transition && r2(a.transition.duration), dir: a.transition && a.transition.direction });
    }
    if (!o.rx.length) delete o.rx; else o.id = n.id;
  }
  if (n.type === 'TEXT') {
    o.c = n.characters;
    if (n.textAlignHorizontal !== 'LEFT') o.ta = n.textAlignHorizontal[0]; if (n.textAlignVertical !== 'TOP') o.tv = n.textAlignVertical[0]; o.ar = n.textAutoResize[0];
    o.seg = [];
    for (const s of n.getStyledTextSegments(['fontName', 'fontSize', 'lineHeight', 'fills', 'textStyleId', 'textDecoration', 'letterSpacing', 'textCase'])) {
      let ts = null; if (s.textStyleId) { const st = await figma.getStyleByIdAsync(s.textStyleId); ts = st && st.name; }
      const fp = s.fills && s.fills[0] ? await paint(s.fills[0]) : null;
      const q = { fill: fp }; if (ts) q.ts = ts; else { q.ff = s.fontName.family; q.fw = s.fontName.style; q.fs = s.fontSize; q.lh = s.lineHeight.unit === 'PIXELS' ? s.lineHeight.value : null; } if (s.textDecoration !== 'NONE') q.td = s.textDecoration; if (s.textCase !== 'ORIGINAL') q.tc = s.textCase; if (n.characters.length !== s.characters.length) q.c = s.characters; o.seg.push(q);
    }
    return o;
  }
  if (n.type === 'INSTANCE') {
    const mc = await n.getMainComponentAsync();
    if (mc) {
      const set = mc.parent && mc.parent.type === 'COMPONENT_SET' ? mc.parent : null;
      o.comp = set ? set.name : mc.name; if (set) o.variant = mc.name;
      if (LEAF.test(o.comp)) {
        o.leaf = 1;
        // icon glyph colour, swapped flag country, label colour of system bars
        const g = n.findOne(c => c.type !== 'INSTANCE' && 'fills' in c && Array.isArray(c.fills) && c.fills.length && c.fills[0].type === 'SOLID');
        if (g) o.glyph = await paint(g.fills[0]);
        const sw = n.findOne(c => c.type === 'INSTANCE');
        if (sw) { const sm = await sw.getMainComponentAsync(); o.swap = sm && sm.name; }
        return o;
      }
    }
  }
  if (['VECTOR', 'BOOLEAN_OPERATION', 'STAR', 'POLYGON', 'LINE', 'ELLIPSE'].includes(n.type)) {
    if (n.type === 'ELLIPSE' && !(n.arcData && (n.arcData.endingAngle - n.arcData.startingAngle) < 6.28)) { o.t = 'ELLIPSE'; return o; }
    try { const sv = await n.exportAsync({ format: 'SVG_STRING' }); o.svg = sv.length < 2500 ? sv.replace(/\n/g, '') : 'BIG'; } catch (e) {}
    return o;
  }
  if ('children' in n) {
    o.ch = [];
    for (const c of n.children) { const q = await walk(c, ox, oy); if (q) o.ch.push(q); }
  }
  return o;
}
const out = [];
for (const id of IDS) {
  const s = await figma.getNodeByIdAsync(id);
  const bb = s.absoluteBoundingBox;
  const d = await walk(s, bb.x, bb.y); d.id = s.id;
  out.push(d);
}
return JSON.stringify(out);
