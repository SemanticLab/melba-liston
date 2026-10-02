// Melba Liston centennial page. Renders docs/data.json (built by
// site/build_site_data.py) into the static markup in index.html.
(function () {
  'use strict';

  const $ = (id) => document.getElementById(id);
  const el = (tag, attrs, ...kids) => {
    const n = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v === null || v === undefined || v === false) continue;
      if (k === 'class') n.className = v;
      else if (k === 'style') n.style.cssText = v;
      else if (k.startsWith('on')) n.addEventListener(k.slice(2), v);
      else n.setAttribute(k, v === true ? '' : v);
    }
    for (const kid of kids.flat()) if (kid != null) n.append(kid);
    return n;
  };
  const ext = (attrs) => Object.assign({ target: '_blank', rel: 'noopener' }, attrs);

  // a row of filter pills; `get` reads the current key, `set` stores a new one
  function pills(host, options, get, set) {
    const draw = () => {
      host.replaceChildren(...options.map((o) =>
        el('button', { type: 'button', 'aria-pressed': String(o.key === get()),
                       onclick: () => { set(o.key); draw(); } }, o.label)));
    };
    draw();
  }

  // ---------------------------------------------------------------- transcript passages
  // Every quote on the page opens here: the turns around it, read in place, with
  // a link to the archive's own copy. transcripts.json is fetched on first use.
  let transcripts = null;
  const loadTranscripts = () => transcripts || (transcripts = fetch('transcripts.json').then((r) => {
    if (!r.ok) throw new Error(r.status);
    return r.json();
  }));
  const PAD = 8, STEP = 14;

  function marked(text, marks) {
    // wrap each quoted phrase found in this turn
    const spans = marks.filter(Boolean).map((m) => [text.indexOf(m), m.length])
      .filter(([at]) => at !== -1).sort((a, b) => a[0] - b[0]);
    const out = [];
    let pos = 0;
    for (const [at, len] of spans) {
      if (at < pos) continue;
      out.push(text.slice(pos, at), el('mark', null, text.slice(at, at + len)));
      pos = at + len;
    }
    out.push(text.slice(pos));
    return out;
  }

  function openPassage(ref) {
    const dlg = $('passage'), body = $('passage-body');
    $('passage-archive').textContent = '';
    $('passage-title').textContent = 'Loading…';
    $('passage-source').textContent = '';
    body.replaceChildren();
    if (!dlg.open) dlg.showModal();
    document.documentElement.style.overflow = 'hidden';

    loadTranscripts().then((all) => {
      const doc = all[ref.doc], blocks = doc.blocks;
      const targets = new Set(ref.blocks);
      const hits = blocks.map((b, i) => (targets.has(b.i) ? i : -1)).filter((i) => i !== -1);
      const first = hits.length ? hits[0] : 0;
      // an event can cite turns far apart; open on the first and whatever sits near it
      const last = hits.filter((i) => i - first <= 20).pop() ?? first;
      let lo = doc.complete ? Math.max(0, first - PAD) : 0;
      let hi = doc.complete ? Math.min(blocks.length, last + PAD + 1) : blocks.length;

      const page = blocks[first].p + 1;
      $('passage-archive').textContent = doc.archive;
      $('passage-title').textContent = doc.title;
      const src = $('passage-source');
      src.href = doc.url + (doc.pdf ? `#page=${page}` : '');
      src.textContent = `Original transcript at ${doc.at}` + (doc.pdf ? ` (PDF, page ${page})` : '') + ' →';

      const row = (b, prev) => el('div', { class: 'turn' + (targets.has(b.i) ? ' target' : '') + (b.n ? ' note' : ''), 'data-i': b.i },
        (b.s || !prev || prev.p !== b.p) ? el('div', { class: 'turn-who' }, el('span', null, b.s),
          (!prev || prev.p !== b.p) ? el('span', { class: 'pg' }, `page ${b.p + 1}`) : null) : null,
        el('p', null, targets.has(b.i) ? marked(b.t, ref.marks || []) : b.t));

      const draw = (keep) => {
        const anchor = keep && body.querySelector(`[data-i="${keep}"]`);
        const before = anchor ? anchor.getBoundingClientRect().top : 0;
        const kids = [];
        if (lo > 0) kids.push(el('button', { type: 'button', class: 'passage-more', onclick: () => { const k = blocks[lo].i; lo = Math.max(0, lo - STEP); draw(k); } }, '↑ Earlier'));
        else if (doc.complete) kids.push(el('div', { class: 'passage-edge' }, 'Start of the transcript'));
        for (let i = lo; i < hi; i++) kids.push(row(blocks[i], i > lo ? blocks[i - 1] : null));
        if (hi < blocks.length) kids.push(el('button', { type: 'button', class: 'passage-more', onclick: () => { const k = blocks[hi - 1].i; hi = Math.min(blocks.length, hi + STEP); draw(k); } }, 'Later ↓'));
        else if (doc.complete) kids.push(el('div', { class: 'passage-edge' }, 'End of the transcript'));
        else kids.push(el('div', { class: 'passage-edge' }, 'The interview continues in the original transcript.'));
        body.replaceChildren(...kids);
        if (keep) {
          const now = body.querySelector(`[data-i="${keep}"]`);
          if (now) body.scrollTop += now.getBoundingClientRect().top - before;
        } else {
          const t = body.querySelector('.turn.target');
          if (t) body.scrollTop = t.offsetTop - body.offsetTop - Math.max(40, (body.clientHeight - t.offsetHeight) / 3);
        }
      };
      draw(null);
    }).catch((e) => { $('passage-title').textContent = `The transcript could not be loaded (${e.message}).`; });
  }

  function initPassage() {
    const dlg = $('passage');
    $('passage-close').addEventListener('click', () => dlg.close());
    dlg.addEventListener('click', (e) => { if (e.target === dlg) dlg.close(); });   // the backdrop
    dlg.addEventListener('close', () => { document.documentElement.style.overflow = ''; });
  }

  // ---------------------------------------------------------------- hero / blurb
  function renderHero(d) {
    $('tagline').textContent = d.hero.tagline;
    $('stats').replaceChildren(...d.hero.stats.map((s) => el('div', null, el('b', null, String(s.n)), s.label)));
    $('blurb').textContent = d.blurb.text;
    $('links').replaceChildren(...d.blurb.links.map((l) =>
      el('a', ext({ href: l.url }), el('span', null, l.label), el('span', null, '→'))));
  }

  // ---------------------------------------------------------------- timeline
  function renderTimeline(tl) {
    const [y0, y1] = tl.range;
    const frac = (y) => (y - y0) / (y1 - y0);
    const pct = (y) => (frac(y) * 100).toFixed(2) + '%';
    const events = tl.events;
    const grid = $('tl-grid');
    let sel = 0;
    $('tl-count').textContent = events.length + ' events';

    // a bar's label shrinks, then abbreviates, then disappears as the bar narrows
    const fitLabel = (px, title, short) => {
      const fits = (s, cw) => px - 8 >= s.length * cw;
      if (fits(title, 7.3)) return [title, 12];
      if (fits(title, 6.1)) return [title, 10];
      if (fits(short, 7.3)) return [short, 12];
      if (fits(short, 6.1)) return [short, 10];
      return ['', 10];
    };

    function draw() {
      grid.replaceChildren();
      const axis = el('div', { class: 'tl-axis' });
      for (let y = y0; y <= y1; y += 10) {
        axis.append(el('div', { class: 'tl-tick', style: `left:${pct(y)}` }, el('span', null, String(y)), el('i')));
      }
      grid.append(el('div'), axis);
      const width = axis.getBoundingClientRect().width || 900;

      for (const lane of tl.lanes) {
        const track = el('div', { class: 'tl-track' });
        for (let y = y0; y < y1; y += 10) track.append(el('i', { style: `left:${pct(y)}` }));
        for (const [a, b, title, color, short] of lane.bars) {
          const w = frac(b) - frac(a);
          const [label, fs] = fitLabel(w * width, title, short || title);
          track.append(el('div', { class: 'tl-bar', title: `${title}, ${a}–${b}`,
            style: `left:${pct(a)};width:${(w * 100).toFixed(2)}%;background:${color};font-size:${fs}px` }, label));
        }
        grid.append(el('div', { class: 'tl-label' }, lane.label), track);
      }

      // the dots: stacked into as many rows as it takes to keep them apart
      const lastX = [];
      const box = el('div', { class: 'tl-events' }, el('div', { class: 'line' }));
      events.forEach((e, i) => {
        const x = frac(e.pos) * width;
        let row = lastX.findIndex((lx) => x - lx >= 15);
        if (row === -1) { row = lastX.length; lastX.push(0); }
        lastX[row] = x;
        box.append(el('button', { type: 'button', class: 'tl-dot' + (e.approx ? ' approx' : ''),
          title: e.when, 'aria-label': `${e.when}: ${e.event}`, 'aria-pressed': String(i === sel),
          style: `left:${pct(e.pos)};top:${7 + row * 17}px`, onclick: () => select(i) }));
      });
      box.style.height = (lastX.length * 17 + 12) + 'px';
      grid.append(el('div', { class: 'tl-label events' }, 'Events'), box);
      grid.append(el('div', { class: 'tl-key' }, el('span', { class: 'tl-dot approx' }),
        'Grey: she gave no year; placed between the dated events around it.'));
    }

    function select(i) {
      const n = events.length;
      sel = ((i % n) + n) % n;
      grid.querySelectorAll('.tl-events .tl-dot').forEach((b, k) => b.setAttribute('aria-pressed', String(k === sel)));
      const e = events[sel];
      const year = $('tl-year');
      year.textContent = e.big || e.when;
      year.classList.toggle('words', !e.big);
      $('tl-event').textContent = e.event;
      const meta = [];
      if (e.big && e.when !== e.big) meta.push(e.when);
      meta.push(e.stated, `${sel + 1} of ${n}`);
      $('tl-meta').replaceChildren(meta.join(' · '), ...(e.blocks.length ? [' · ',
        el('button', { type: 'button', class: 'linkish', onclick: () => openPassage({ doc: 'own', blocks: e.blocks }) },
          'In the transcript →')] : []));
    }

    $('tl-prev').addEventListener('click', () => select(sel - 1));
    $('tl-next').addEventListener('click', () => select(sel + 1));
    let t;
    window.addEventListener('resize', () => { clearTimeout(t); t = setTimeout(() => { draw(); select(sel); }, 120); });
    draw();
    select(0);
  }

  // ---------------------------------------------------------------- voices
  function renderVoices(v) {
    let tier = 'all';
    const initials = (name) => name.replace(/"[^"]*"/g, '').split(/\s+/).filter(Boolean).map((w) => w[0]).join('').slice(0, 3);
    const draw = () => {
      const cards = v.cards.filter((c) => tier === 'all' || c.tiers.includes(tier));
      $('voice-grid').replaceChildren(...cards.map((c) =>
        el('button', { type: 'button', class: 'voice', title: c.source,
            onclick: () => openPassage({ doc: c.doc, blocks: c.blocks, marks: [c.quote, c.second] }) },
          el('div', { class: 'avatar' }, c.img ? el('img', { src: c.img, alt: '', loading: 'lazy' }) : initials(c.name)),
          el('div', null,
            el('div', { class: 'voice-name' }, c.name),
            el('div', { class: 'voice-line' }, c.line),
            el('div', { class: 'voice-quote' }, `“${c.quote}”`),
            c.second ? el('div', { class: 'voice-quote' }, `“${c.second}”`) : null,
            c.note ? el('div', { class: 'voice-note' }, c.note) : null))));
    };
    $('voice-intro').textContent = v.intro;
    pills($('voice-pills'), [{ key: 'all', label: 'All' }, ...v.tiers], () => tier, (k) => { tier = k; draw(); });
    draw();
  }

  // ---------------------------------------------------------------- her words
  function renderOwn(own) {
    const labels = Object.fromEntries(own.categories.map((c) => [c.key, c.label]));
    let cat = 'all', idx = 0;
    const list = () => own.items.filter((i) => cat === 'all' || i.cat === cat);
    let current = null;
    const draw = () => {
      const items = list();
      const it = current = items[idx % items.length];
      const q = $('own-quote');
      q.textContent = `“${it.q}”`;
      q.className = it.q.length > 150 ? 'long' : it.q.length > 80 ? 'medium' : '';
      $('own-theme').textContent = labels[it.cat];
      // a line that leans on the question before it gets a sentence saying what it answers
      $('own-context').textContent = it.alone ? '' : it.sum;
      $('own-counter').textContent = `${(idx % items.length) + 1} of ${items.length} · ${own.source}`;
    };
    $('own-link').addEventListener('click', () => openPassage({ doc: 'own', blocks: [current.b], marks: [current.q] }));
    pills($('own-pills'), [{ key: 'all', label: 'All' }, ...own.categories], () => cat, (k) => { cat = k; idx = 0; draw(); });
    $('own-next').addEventListener('click', () => { idx += 1; draw(); });
    draw();
  }

  // ---------------------------------------------------------------- discography
  function renderDiscography(disc) {
    let role = 'all';
    const draw = () => {
      const rs = disc.releases.filter((r) => role === 'all' || r.role === role);
      $('release-grid').replaceChildren(...rs.map((r) => {
        const cover = el('div', { class: 'cover' + (r.cover ? ' has-img' : ''), style: r.cover ? null : `background:${r.bg}` },
          r.cover ? el('img', { src: r.cover, alt: '', loading: 'lazy' }) : null,
          el('span', null, r.role_label));
        const text = el('div', null,
          el('div', { class: 'release-title' }, r.title),
          el('div', { class: 'release-by' }, [r.leader, r.year].filter(Boolean).join(' · ')));
        return r.url ? el('a', ext({ class: 'release', href: r.url }), cover, text)
                     : el('div', { class: 'release' }, cover, text);
      }));
    };
    pills($('role-pills'),
      [{ key: 'all', label: `All ${disc.count}` }, ...disc.roles],
      () => role, (k) => { role = k; draw(); });
    draw();
  }

  function renderCredits(c) {
    $('credits').replaceChildren(
      ...c.portraits.map((p) => el('li', null, p.name + ': ',
        p.page ? el('a', ext({ href: p.page }), p.attribution) : p.attribution)),
      el('li', null, c.covers));
  }

  fetch('data.json')
    .then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then((d) => {
      initPassage();
      renderHero(d);
      renderTimeline(d.timeline);
      renderVoices(d.voices);
      renderOwn(d.own);
      renderDiscography(d.discography);
      renderCredits(d.credits);
    })
    .catch((e) => {
      document.body.prepend(el('p', { style: 'padding:20px 40px;color:#D63A1F' },
        `The page data could not be loaded (${e.message}).`));
    });
})();
