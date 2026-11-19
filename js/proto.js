// Bumpy prototypes — click-through engine.
// Screens are <section class="screen" data-id> elements; hotspots carry
// data-go (target screen id), data-tt (transition), data-dir, data-td (seconds).
(() => {
  const P = window.PROTO;
  const device = document.getElementById('device');
  const screens = new Map([...device.querySelectorAll('.screen')].map(s => [s.dataset.id, s]));
  const meta = new Map(P.screens.map(s => [s.id, s]));
  const list = document.getElementById('screens');
  const note = document.getElementById('note');
  const EASE = 'cubic-bezier(.2,.8,.2,1)';
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  let current = null, timer = null, busy = false, lastHot = null, lastCard = null;
  const hideTimers = [];
  const trail = [];

  // ---------- scale the phone to the window ----------
  function fit() {
    const mobile = innerWidth <= 820;
    const bar = mobile ? (document.querySelector('.panel .versions') || {}).offsetHeight || 0 : 0;
    const s = mobile ? Math.min(innerWidth / 402, (innerHeight - bar - 16) / 874) : Math.min(1, (innerHeight - 48) / 874);
    document.documentElement.style.setProperty('--s', s.toFixed(4));
  }
  addEventListener('resize', fit); fit();

  // ---------- panel ----------
  P.screens.forEach(s => {
    if (s.hidden) return;
    const li = document.createElement('li');
    const b = document.createElement('button');
    b.type = 'button'; b.textContent = s.title; b.dataset.id = s.id;
    b.addEventListener('click', () => go(s.id, 'dissolve', '', 0.2));
    li.append(b); list.append(li);
  });
  let intent = '', toastNext = false;
  document.getElementById('restart').addEventListener('click', () => { trail.length = 0; intent = ''; go(P.start, 'dissolve', '', 0.25, false); });
  const hotBtn = document.getElementById('hotspots');
  hotBtn.addEventListener('click', () => {
    const on = device.classList.toggle('show-hot');
    hotBtn.setAttribute('aria-pressed', String(on));
  });

  function setPanel(id) {
    list.querySelectorAll('button').forEach(b => b.setAttribute('aria-current', String(b.dataset.id === id)));
    const m = meta.get(id);
    note.innerHTML = (m && m.note) || '';
    if (m) window.history.replaceState(null, '', '#' + m.slug);
  }

  // ---------- transitions ----------
  const isBackdrop = el => el.classList.contains('bg-clone');
  const isFade = el => /^(Scrim|Underlying screen)/.test(el.dataset.name || '');
  const layered = scr => [...scr.children].some(c => isBackdrop(c) || isFade(c));
  const offset = dir => ({ top: [0, 100], bottom: [0, -100], left: [100, 0], right: [-100, 0] }[dir] || [0, 100]);
  const tr = ([x, y], k = 1) => `translate(${x * k}%, ${y * k}%)`;
  const trPx = ([x, y]) => `translate(${x * 4.02}px, ${y * 8.74}px)`; // % of the 402×874 screen

  // overlay: everything above the first scrim opens from the tapped card; what lies under the scrim stays put
  const overlayParts = scr => {
    const kids = [...scr.children];
    const i = kids.findIndex(isFade);
    return i < 0 ? [] : kids.slice(i);
  };
  // while the overlay moves, the screen underneath shows through this one's own copy of it
  function seeThrough(scr) {
    const kids = [...scr.children];
    const i = kids.findIndex(isFade);
    kids.slice(0, Math.max(i, 0)).forEach(c => { c.style.visibility = 'hidden'; c.dataset.ovh = '1'; });
    scr.dataset.ovbg = scr.style.background || ' ';
    scr.style.background = 'transparent';
  }
  function solid(scr) {
    scr.querySelectorAll('[data-ovh]').forEach(c => { c.style.visibility = ''; delete c.dataset.ovh; });
    if (scr.dataset.ovbg) { scr.style.background = scr.dataset.ovbg.trim(); delete scr.dataset.ovbg; }
  }
  function cardMorph(el, card) {
    const a = el.getBoundingClientRect(), b = card.getBoundingClientRect();
    const k = a.width / el.offsetWidth || 1;
    const dx = (b.left + b.width / 2 - (a.left + a.width / 2)) / k;
    const dy = (b.top + b.height / 2 - (a.top + a.height / 2)) / k;
    return `translate(${dx}px, ${dy}px) scale(${Math.max(b.width / a.width, 0.2)})`;
  }

  function animIn(scr, tt, dir, ms) {
    const anims = [];
    if (tt === 'overlay') {
      const card = lastHot;
      lastCard = card && card.dataset.name;
      seeThrough(scr);
      overlayParts(scr).forEach(c => {
        if (isFade(c)) anims.push(c.animate([{ opacity: 0 }, { opacity: 1 }], { duration: ms, easing: 'ease-out' }));
        else if (card) anims.push(c.animate([{ transform: cardMorph(c, card), opacity: 0.6, borderRadius: '16px' }, { transform: 'none', opacity: 1 }], { duration: ms, easing: EASE }));
        else anims.push(c.animate([{ transform: 'translateY(8%)', opacity: 0 }, { transform: 'none', opacity: 1 }], { duration: ms, easing: EASE }));
      });
      return anims;
    }
    if (tt === 'dissolve' || tt === 'smart_animate') {
      anims.push(scr.animate([{ opacity: 0 }, { opacity: 1 }], { duration: ms, easing: 'ease-out' }));
    } else if (tt === 'move_in' || tt === 'slide_in' || tt === 'push') {
      const o = offset(dir);
      if (tt !== 'push' && layered(scr)) {
        const bg = getComputedStyle(scr).backgroundColor;
        if (![...scr.children].some(isBackdrop)) anims.push(scr.animate([{ backgroundColor: 'rgba(0,0,0,0)' }, { backgroundColor: bg }], { duration: ms }));
        [...scr.children].forEach(c => {
          if (isBackdrop(c)) return;
          if (isFade(c)) anims.push(c.animate([{ opacity: 0 }, { opacity: 1 }], { duration: ms, easing: 'ease-out' }));
          else anims.push(c.animate([{ transform: trPx(o) }, { transform: 'none' }], { duration: ms, easing: EASE }));
        });
      } else {
        anims.push(scr.animate([{ transform: tr(o) }, { transform: 'none' }], { duration: ms, easing: EASE }));
      }
    }
    return anims;
  }

  function animOut(scr, tt, dir, ms, next) {
    const anims = [];
    if (tt === 'overlay_out') {
      const card = next && lastCard && next.querySelector(`[data-name="${CSS.escape(lastCard)}"]`);
      seeThrough(scr);
      overlayParts(scr).forEach(c => {
        if (isFade(c)) anims.push(c.animate([{ opacity: 1 }, { opacity: 0 }], { duration: ms, fill: 'forwards' }));
        else if (card) anims.push(c.animate([{ transform: 'none', opacity: 1 }, { transform: cardMorph(c, card), opacity: 0 }], { duration: ms, easing: 'cubic-bezier(.4,0,.6,1)', fill: 'forwards' }));
        else anims.push(c.animate([{ transform: 'none', opacity: 1 }, { transform: 'translateY(8%)', opacity: 0 }], { duration: ms, fill: 'forwards' }));
      });
      return anims;
    }
    if (tt === 'push') {
      const o = offset(dir);
      anims.push(scr.animate([{ transform: 'none' }, { transform: tr(o, -1) }], { duration: ms, easing: EASE, fill: 'forwards' }));
    } else if (tt === 'move_out' || tt === 'slide_out') {
      const o = offset(dir).map(v => -v);
      if (layered(scr)) {
        anims.push(scr.animate([{ backgroundColor: getComputedStyle(scr).backgroundColor }, { backgroundColor: 'rgba(0,0,0,0)' }], { duration: ms, fill: 'forwards' }));
        [...scr.children].forEach(c => {
          if (isBackdrop(c)) { c.style.visibility = 'hidden'; return; }
          if (isFade(c)) anims.push(c.animate([{ opacity: 1 }, { opacity: 0 }], { duration: ms, fill: 'forwards' }));
          else anims.push(c.animate([{ transform: 'none' }, { transform: trPx(o) }], { duration: ms, easing: 'cubic-bezier(.4,0,1,1)', fill: 'forwards' }));
        });
      } else {
        anims.push(scr.animate([{ transform: 'none' }, { transform: tr(o) }], { duration: ms, easing: 'cubic-bezier(.4,0,1,1)', fill: 'forwards' }));
      }
    }
    return anims;
  }

  // `under`: the screen an overlay was opened over; it stays on below the overlay until the overlay closes
  let under = null;
  function dropUnder(keep) {
    if (under && under !== keep) { under.classList.remove('is-on'); under.style.zIndex = ''; }
    under = null;
  }

  function go(id, tt = 'instant', dir = '', td = 0.3, remember = true) {
    const next = screens.get(id);
    if (!next || busy || next === current) return;
    clearTimeout(timer);
    hideTimers.splice(0).forEach(clearTimeout);
    const prev = current;
    const ms = reduce ? 1 : Math.max(1, td * 1000);
    if (remember && prev) trail.push(prev.dataset.id);
    current = next;
    setPanel(id);
    if (scroller(next)) scrollContent(next, 0);   // a long screen always opens at the top (the Bump title is up there)
    const overlayIn = tt === 'overlay', overlayOut = tt === 'overlay_out';
    // leaving an overlay any other way: it becomes a whole screen again
    if (prev && under && !overlayOut) { solid(prev); dropUnder(next); }
    next.classList.add('is-on');
    if (!prev || tt === 'instant') { if (prev) { prev.classList.remove('is-on'); solid(prev); } dropUnder(next); return entered(next); }

    busy = true;
    const outgoing = tt === 'move_out' || tt === 'slide_out' || overlayOut;
    prev.style.zIndex = outgoing ? 2 : 0;
    next.style.zIndex = outgoing ? 0 : 1;
    const anims = outgoing ? animOut(prev, tt, dir, ms, next) : [...animIn(next, tt, dir, ms), ...(tt === 'push' ? animOut(prev, tt, dir, ms) : [])];
    Promise.all(anims.map(a => a.finished)).catch(() => {}).then(() => {
      [prev, next].forEach(s => { s.getAnimations({ subtree: true }).forEach(a => a.cancel()); });
      prev.querySelectorAll('.bg-clone').forEach(c => { c.style.visibility = ''; });
      if (overlayIn) {
        under = prev; prev.style.zIndex = 0; next.style.zIndex = 1;   // keep the list visible under the overlay
      } else {
        prev.classList.remove('is-on'); solid(prev);
        if (overlayOut) dropUnder(next);
        prev.style.zIndex = ''; next.style.zIndex = '';
        if (!under) solid(next);
      }
      busy = false;
      entered(next);
    });
  }

  function entered(scr) {
    scr.querySelectorAll('[data-toast-node]').forEach(el => {
      el.getAnimations().forEach(a => a.cancel());
      el.style.opacity = '0'; el.style.pointerEvents = 'none'; el.style.zIndex = 30;
    });
    if (toastNext) {
      toastNext = false;
      scr.querySelectorAll('[data-toast-node]').forEach(el => {
        el.animate([{ transform: 'translateY(-130%)', opacity: 0 }, { transform: 'none', opacity: 1 }], { duration: reduce ? 1 : 350, easing: 'cubic-bezier(0,0,.2,1)', fill: 'forwards' });
        hideTimers.push(setTimeout(() => el.animate([{ transform: 'none', opacity: 1 }, { transform: 'translateY(-130%)', opacity: 0 }], { duration: reduce ? 1 : 300, easing: 'cubic-bezier(.4,0,1,1)', fill: 'forwards' }), 2800));
      });
    }
    // banners that leave on their own (data-autohide = ms on screen)
    scr.querySelectorAll('[data-autohide]').forEach(el => {
      el.getAnimations().forEach(a => a.cancel());
      el.style.pointerEvents = '';
      el.style.zIndex = 30;   // over the whole layout, the collapsed bar included
      hideTimers.push(setTimeout(() => {
        el.style.pointerEvents = 'none';
        el.animate([{ transform: 'none', opacity: 1 }, { transform: 'translateY(-130%)', opacity: 0 }], { duration: reduce ? 1 : 300, easing: 'cubic-bezier(.4,0,1,1)', fill: 'forwards' });
      }, +el.dataset.autohide));
    });
    const ms = +scr.dataset.after;
    if (ms) timer = setTimeout(() => go(scr.dataset.afterGo, scr.dataset.afterTt || 'dissolve', scr.dataset.afterDir || '', 0.3), ms);
  }

  function back(hot) {
    // the screen we came from; when a screen was opened from the list on the left, the screen it is drawn over
    const id = trail.pop() || (hot && hot.dataset.fallback) || (under && under.dataset.id);
    if (id) go(id, (hot && hot.dataset.tt) || 'dissolve', (hot && hot.dataset.dir) || '', 0.25, false);
  }

  // ---------- scroll: the gold header collapses into a nav bar titled "Liked you" ----------
  const kid = (scr, name) => scr.querySelector(`:scope > [data-name="${name}"]`);
  const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
  function collapsible(scr) {
    if (!P.collapse || !scr || [...scr.children].some(isFade)) return null;
    if (scr._col !== undefined) return scr._col;
    const hdr = kid(scr, 'Gold Header'), grid = kid(scr, 'Likes Grid'), tabs = kid(scr, 'Top Tabs');
    const nav = kid(scr, 'Navigation Bar'), top = nav && nav.querySelector('[data-name="Top Bar"]');
    if (!hdr || !grid || !tabs || !top) return (scr._col = null);
    const content = hdr.querySelector('[data-name="Header Content"]');
    const cta = kid(scr, 'Button · See who liked you') || kid(scr, 'Tab Bar');
    const flow = [...scr.children].filter(c => c.offsetTop >= tabs.offsetTop + tabs.offsetHeight - 1 && c !== cta
      && !/^(Tab Bar|Button ·|Notification|Gold Toast|Home Indicator)/.test(c.dataset.name || ''));
    const H0 = hdr.offsetHeight, barBottom = nav.offsetTop + top.offsetTop + top.offsetHeight;
    const C = Math.max(0, H0 - barBottom);
    const gridBottom = grid.offsetTop + Math.max(...[...grid.children].map(c => c.offsetTop + c.offsetHeight), grid.offsetHeight);
    const max = Math.max(C, gridBottom - (cta ? cta.offsetTop - 16 : 874));
    const ref = content && [...content.querySelectorAll('*')].find(e => e.textContent.trim() === 'Liked you' && !e.children.length);
    const title = document.createElement('div');
    title.className = 'compact-title'; title.textContent = 'Liked you';
    const cs = ref ? getComputedStyle(ref) : null;
    Object.assign(title.style, { position: 'absolute', left: '0', right: '0', top: (nav.offsetTop + top.offsetTop) + 'px', height: top.offsetHeight + 'px',
      display: 'flex', alignItems: 'center', justifyContent: 'center', font: `600 17px/22px ${cs ? cs.fontFamily : 'inherit'}`,
      color: cs ? cs.color : '#000', opacity: '0', pointerEvents: 'none', zIndex: 5 });
    scr.append(title);
    tabs.style.zIndex = 4;   // the tabs (and their underline) stay above the cards that scroll under them
    return (scr._col = { hdr, content, tabs, flow, title, H0, C, max, tabsBottom: tabs.offsetTop + tabs.offsetHeight, y: 0 });
  }
  function scrollTo(scr, y) {
    const k = collapsible(scr); if (!k) return false;
    k.y = clamp(y, 0, k.max);
    const c = Math.min(k.y, k.C), f = k.C ? c / k.C : 1;
    k.hdr.style.height = (k.H0 - c) + 'px';
    if (k.content) { k.content.style.opacity = clamp(1 - f / 0.6); k.content.style.transform = `translateY(${-c * 0.35}px)`; }
    k.title.style.opacity = clamp((f - 0.6) / 0.4);
    k.tabs.style.transform = `translateY(${-c}px)`;
    const line = k.tabsBottom - c;                       // content scrolls under the sticky tabs
    k.flow.forEach(el => {
      el.style.transform = `translateY(${-k.y}px)`;
      const hidden = line - (el.offsetTop - k.y);
      el.style.clipPath = hidden > 0 ? `inset(${hidden}px 0 0 0)` : '';
    });
    return true;
  }
  // ---------- scroll: a long screen (profile, Bump) moves its "Scroll Content" under the fixed bars ----------
  function scroller(scr) {
    if (scr._sc !== undefined) return scr._sc;
    const el = scr.querySelector(':scope > [data-name="Scroll Content"]');
    if (!el) return (scr._sc = null);
    return (scr._sc = { el, y: 0, fade: scr.querySelector(':scope > [data-name="Bottom Fade"]') });
  }
  function scrollContent(scr, y) {
    const k = scroller(scr); if (!k) return false;
    const h = Math.max(0, ...[...k.el.children].map(c => c.offsetTop + c.offsetHeight));   // measured when shown
    k.y = clamp(y, 0, Math.max(0, h - 874));
    k.el.style.transform = `translateY(${-k.y}px)`;
    if (k.fade) k.fade.style.opacity = clamp((k.y - 40) / 120);
    return true;
  }
  device.addEventListener('wheel', e => {
    if (busy || !current) return;
    const k = collapsible(current);
    if (k) { e.preventDefault(); return scrollTo(current, k.y + e.deltaY); }
    const q = scroller(current); if (!q) return;
    e.preventDefault(); scrollContent(current, q.y + e.deltaY);
  }, { passive: false });
  let drag = null, dragged = false;
  device.addEventListener('pointerdown', e => {
    const sc = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--s')) || 1;
    if (current && collapsible(current)) drag = { y: e.clientY, s: current._col.y, sc, f: scrollTo };
    else if (current && scroller(current)) drag = { y: e.clientY, s: current._sc.y, sc, f: scrollContent };
    dragged = false;
  });
  addEventListener('pointermove', e => {
    if (!drag) return;
    const d = (drag.y - e.clientY) / drag.sc;
    if (Math.abs(d) > 6) dragged = true;
    if (dragged) drag.f(current, drag.s + d);
  });
  addEventListener('pointerup', () => { drag = null; });
  device.addEventListener('click', e => { if (dragged) { e.stopImmediatePropagation(); dragged = false; } }, true);

  // ---------- input ----------
  device.addEventListener('click', e => {
    if (!current || busy) return;
    const hot = e.target.closest('[data-go], [data-back]');
    if (hot && current.contains(hot)) {
      lastHot = hot;
      if ('ctx' in hot.dataset) intent = hot.dataset.ctx;   // e.g. a card: after Gold, open that profile
      if (hot.dataset.toast) toastNext = true;              // a purchase: the next screen says "Welcome to Gold"
      if (hot.dataset.back) return back(hot);
      let to = hot.dataset.go;
      if (hot.dataset.goCtx && intent && screens.has(intent)) { to = intent; intent = ''; }
      return go(to, hot.dataset.tt, hot.dataset.dir, parseFloat(hot.dataset.td) || 0.3);
    }
    current.classList.add('flash');
    setTimeout(() => current && current.classList.remove('flash'), 450);
  });
  addEventListener('keydown', e => {
    if (e.key === 'ArrowLeft' || e.key === 'Backspace') back();
    else if (e.key === 'r' || e.key === 'R') { trail.length = 0; intent = ''; go(P.start, 'dissolve', '', 0.25, false); }
  });

  // ---------- start (deep link by #slug) ----------
  const fromHash = P.screens.find(s => '#' + s.slug === location.hash);
  go(fromHash ? fromHash.id : P.start);
})();
