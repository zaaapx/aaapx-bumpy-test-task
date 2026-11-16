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
  let current = null, timer = null, busy = false;
  const trail = [];

  // ---------- scale the phone to the window ----------
  function fit() {
    const mobile = innerWidth <= 820;
    const s = mobile ? Math.min(innerWidth / 402, innerHeight / 874) : Math.min(1, (innerHeight - 48) / 874);
    document.documentElement.style.setProperty('--s', s.toFixed(4));
  }
  addEventListener('resize', fit); fit();

  // ---------- panel ----------
  P.screens.forEach(s => {
    const li = document.createElement('li');
    const b = document.createElement('button');
    b.type = 'button'; b.textContent = s.title; b.dataset.id = s.id;
    b.addEventListener('click', () => go(s.id, 'dissolve', '', 0.2));
    li.append(b); list.append(li);
  });
  document.getElementById('restart').addEventListener('click', () => { trail.length = 0; go(P.start, 'dissolve', '', 0.25, false); });
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

  function animIn(scr, tt, dir, ms) {
    const anims = [];
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

  function animOut(scr, tt, dir, ms) {
    const anims = [];
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

  function go(id, tt = 'instant', dir = '', td = 0.3, remember = true) {
    const next = screens.get(id);
    if (!next || busy || next === current) return;
    clearTimeout(timer);
    const prev = current;
    const ms = reduce ? 1 : Math.max(1, td * 1000);
    if (remember && prev) trail.push(prev.dataset.id);
    current = next;
    setPanel(id);
    next.classList.add('is-on');
    if (!prev || tt === 'instant') { if (prev) prev.classList.remove('is-on'); return entered(next); }

    busy = true;
    const outgoing = tt === 'move_out' || tt === 'slide_out';
    prev.style.zIndex = outgoing ? 2 : 0;
    next.style.zIndex = outgoing ? 0 : 1;
    const anims = outgoing ? animOut(prev, tt, dir, ms) : [...animIn(next, tt, dir, ms), ...(tt === 'push' ? animOut(prev, tt, dir, ms) : [])];
    Promise.all(anims.map(a => a.finished)).catch(() => {}).then(() => {
      prev.classList.remove('is-on');
      [prev, next].forEach(s => { s.style.zIndex = ''; s.getAnimations({ subtree: true }).forEach(a => a.cancel()); });
      prev.querySelectorAll('.bg-clone').forEach(c => { c.style.visibility = ''; });
      busy = false;
      entered(next);
    });
  }

  function entered(scr) {
    const ms = +scr.dataset.after;
    if (ms) timer = setTimeout(() => go(scr.dataset.afterGo, scr.dataset.afterTt || 'dissolve', '', 0.25), ms);
  }

  function back() {
    const id = trail.pop();
    if (id) go(id, 'dissolve', '', 0.2, false);
  }

  // ---------- input ----------
  device.addEventListener('click', e => {
    if (!current || busy) return;
    const hot = e.target.closest('[data-go], [data-back]');
    if (hot && current.contains(hot)) {
      if (hot.dataset.back) return back();
      return go(hot.dataset.go, hot.dataset.tt, hot.dataset.dir, parseFloat(hot.dataset.td) || 0.3);
    }
    current.classList.add('flash');
    setTimeout(() => current && current.classList.remove('flash'), 450);
  });
  addEventListener('keydown', e => {
    if (e.key === 'ArrowLeft' || e.key === 'Backspace') back();
    else if (e.key === 'r' || e.key === 'R') { trail.length = 0; go(P.start, 'dissolve', '', 0.25, false); }
  });

  // ---------- start (deep link by #slug) ----------
  const fromHash = P.screens.find(s => '#' + s.slug === location.hash);
  go(fromHash ? fromHash.id : P.start);
})();
