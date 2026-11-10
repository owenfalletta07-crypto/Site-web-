/* =====================================================================
   VOLT ZERO — main.js
   ---------------------------------------------------------------------
   Orchestration : chargement, scroll fluide (Lenis), timeline maîtresse
   GSAP liée au scroll (scrub) qui fait passer la canette d'une pose à
   l'autre, apparitions de texte, compteurs, sélection de saveur.

   Unité de temps de la timeline : 1 = un écran (100vh) de scroll.
   ===================================================================== */

import { createScene, FLAVORS } from './scene.js';

const { gsap, ScrollTrigger, Lenis } = window;
gsap.registerPlugin(ScrollTrigger);
ScrollTrigger.config({ ignoreMobileResize: true });

const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const MOBILE_Q = '(max-width: 767px), (orientation: portrait) and (max-width: 1024px)';

const $ = (sel, ctx = document) => ctx.querySelector(sel);
const $$ = (sel, ctx = document) => [...ctx.querySelectorAll(sel)];
const root = document.documentElement;
const TAU = Math.PI * 2;

/* =====================================================================
   Poses de la canette par section
   x, y, z : position · rotX/Y/Z : radians · scale : échelle
   ===================================================================== */
const DEG = Math.PI / 180;
const POSES = {
  desktop: {
    hero:     { x: 0,     y: -0.05, z: 0,    rotX: 0,    rotY: 0,             rotZ: 0,        scale: 1 },
    sugar:    { x: 1.45,  y: -0.05, z: 0,    rotX: 0.05, rotY: 0.75,          rotZ: 20 * DEG, scale: 1 },
    caffeine: { x: 0.95,  y: 0.05,  z: 3.4,  rotX: 0,    rotY: -0.08,         rotZ: -6 * DEG, scale: 1 },
    cold:     { x: -1.35, y: -0.05, z: 0.3,  rotX: 0.05, rotY: TAU + 0.35,    rotZ: -8 * DEG, scale: 1 },
    anatomy:  { x: 0,     y: -0.2,  z: -1.1, rotX: 0.26, rotY: TAU + 1.1,     rotZ: 0,        scale: 0.6 },
    flavors:  { x: 1.3,   y: -0.05, z: 0,    rotX: 0,    rotY: 2 * TAU,       rotZ: 0,        scale: 0.95 },
    compare:  { x: -1.7,  y: -0.1,  z: -0.6, rotX: 0,    rotY: 2 * TAU + 0.5, rotZ: 10 * DEG, scale: 0.85 },
    final:    { x: 0,     y: -0.1,  z: -0.3, rotX: 0,    rotY: 3 * TAU,       rotZ: 0,        scale: 0.7 },
    trioGap: 1.35,
  },
  // Portrait : canette dans la moitié haute, texte en bas
  mobile: {
    hero:     { x: 0,     y: 0.35,  z: 0,    rotX: 0,    rotY: 0,             rotZ: 0,        scale: 0.72 },
    sugar:    { x: 0.1,   y: 0.8,   z: 0,    rotX: 0.05, rotY: 0.75,          rotZ: 20 * DEG, scale: 0.54 },
    caffeine: { x: 0,     y: 1.0,   z: 2.0,  rotX: 0,    rotY: -0.08,         rotZ: -6 * DEG, scale: 1 },
    cold:     { x: 0,     y: 0.8,   z: 0,    rotX: 0.05, rotY: TAU + 0.35,    rotZ: -8 * DEG, scale: 0.56 },
    anatomy:  { x: -0.3,  y: 0.55,  z: -0.5, rotX: 0.3,  rotY: TAU + 1.1,     rotZ: 0,        scale: 0.5 },
    flavors:  { x: 0,     y: 0.75,  z: 0,    rotX: 0,    rotY: 2 * TAU,       rotZ: 0,        scale: 0.56 },
    compare:  { x: 0,     y: 1.0,   z: -0.5, rotX: 0,    rotY: 2 * TAU + 0.5, rotZ: 10 * DEG, scale: 0.42 },
    final:    { x: 0,     y: 0.1,   z: 0,    rotX: 0,    rotY: 3 * TAU,       rotZ: 0,        scale: 0.42 },
    trioGap: 0.56,
  },
};

/* =====================================================================
   Grain de film : une tuile de bruit générée une fois, animée en CSS
   ===================================================================== */
function makeGrain() {
  const size = 220;
  const c = document.createElement('canvas');
  c.width = c.height = size;
  const ctx = c.getContext('2d');
  const img = ctx.createImageData(size, size);
  for (let i = 0; i < img.data.length; i += 4) {
    const v = Math.random() * 255;
    img.data[i] = img.data[i + 1] = img.data[i + 2] = v;
    img.data[i + 3] = 255;
  }
  ctx.putImageData(img, 0, 0);
  $('.grain').style.backgroundImage = `url(${c.toDataURL('image/png')})`;
}

/* =====================================================================
   Scroll fluide
   ===================================================================== */
let lenis = null;
function initLenis() {
  if (reduced || !Lenis) return;
  lenis = new Lenis({ lerp: 0.09, smoothWheel: true });
  lenis.on('scroll', ScrollTrigger.update);
  gsap.ticker.add((t) => lenis.raf(t * 1000));
  gsap.ticker.lagSmoothing(0);
  lenis.stop();
}

/* =====================================================================
   Chargement
   ===================================================================== */
async function boot() {
  makeGrain();
  initLenis();
  window.scrollTo(0, 0);
  if ('scrollRestoration' in history) history.scrollRestoration = 'manual';

  const countEl = $('.js-load-count');
  const barEl = $('.js-load-bar');
  let target = 0.05;
  let shown = 0;
  let resolveCount;
  const counted = new Promise((r) => (resolveCount = r));

  // Compteur 0 → 100 % : suit la progression réelle, sans dépasser ~70 %/s
  const speed = reduced ? 400 : 75;
  const tick = (t, dt) => {
    shown = Math.min(shown + (dt / 1000) * speed, target * 100);
    countEl.textContent = Math.floor(shown);
    barEl.style.transform = `scaleX(${shown / 100})`;
    if (shown >= 100) { gsap.ticker.remove(tick); resolveCount(); }
  };
  gsap.ticker.add(tick);

  let scene;
  try {
    scene = await createScene($('.webgl'), { onProgress: (p) => (target = Math.max(target, p)), reducedMotion: reduced });
  } catch (err) {
    console.warn('WebGL indisponible, la page reste lisible sans 3D.', err);
    target = 1;
  }
  target = 1;
  if (scene) {
    scene.start();
    window.__scene = scene; // utile pour le débogage
  }
  await counted;

  if (scene) initChoreography(scene);
  openCurtain(scene);
}

/** Rideau qui s'ouvre puis intro du hero. */
function openCurtain(scene) {
  const tl = gsap.timeline({
    defaults: { ease: 'expo.inOut' },
    onComplete: () => {
      $('.loader').remove();
      document.body.classList.remove('is-loading');
      ScrollTrigger.refresh();
      lenis?.start();
      window.__ready = true;
    },
  });
  const d = reduced ? 0.01 : 1;

  tl.to('.loader__ui', { autoAlpha: 0, y: -30, duration: 0.6 * d, ease: 'power2.in' })
    .to('.loader__curtain--top', { yPercent: -100, duration: 1.3 * d }, '<0.3')
    .to('.loader__curtain--bottom', { yPercent: 100, duration: 1.3 * d }, '<')
    .from('.js-backdrop-word span', { yPercent: 140, duration: 1.4 * d, stagger: 0.07 * d, ease: 'expo.out' }, '<0.55')
    .from('.js-hero-in', { autoAlpha: 0, y: 18, duration: 0.9 * d, stagger: 0.1 * d, ease: 'power3.out' }, '<0.4');

  if (scene) {
    const s = scene.state;
    tl.from(s, { y: s.y - 1.4, rotY: -Math.PI * 1.1, scale: s.scale * 0.7, glow: 0, floor: 0, duration: 2 * d, ease: 'expo.out' }, 0.75 * d);
  }
}

/* =====================================================================
   Chorégraphie liée au scroll
   ===================================================================== */
function initChoreography(scene) {
  const s = scene.state;
  const stage = $('.js-stage');
  const COLD = scene.colorOf('#5fd8ff');
  const NEUTRAL = scene.colorOf('#dfe8ff');
  Object.assign(s.override, COLD);

  const TOTAL = 14.6; // durée de la timeline en écrans de scroll
  let master = null;

  const mm = gsap.matchMedia();
  mm.add({ isMobile: MOBILE_Q, any: 'all' }, (ctx) => {
    const P = ctx.conditions.isMobile ? POSES.mobile : POSES.desktop;
    Object.assign(s, P.hero, { trioGap: P.trioGap });

    const tl = gsap.timeline({
      defaults: { ease: 'none' },
      scrollTrigger: {
        trigger: stage,
        start: 'top top',
        end: () => '+=' + TOTAL * window.innerHeight,
        pin: true,
        scrub: reduced ? true : 1,
        invalidateOnRefresh: true,
      },
    });
    master = tl;

    /* --- Helpers ------------------------------------------------------ */
    const scr = (name) => $(`[data-screen="${name}"]`);
    const lines = (name) => $$(`[data-screen="${name}"] .reveal .line > span`);
    const blurIn = reduced ? 'blur(0px)' : 'blur(12px)';
    const blurOut = reduced ? 'blur(0px)' : 'blur(8px)';

    const pose = (p, at, dur = 1, ease = 'power2.inOut') => tl.to(s, { ...p, duration: dur, ease }, at);
    const show = (name, tIn, tOut) => {
      tl.set(scr(name), { autoAlpha: 1 }, tIn);
      if (tOut != null) tl.set(scr(name), { autoAlpha: 0 }, tOut);
    };
    // Apparition ligne par ligne, avec masque et léger flou
    const textIn = (name, at, span = 0.45) => {
      const els = lines(name);
      tl.fromTo(els,
        { yPercent: 115, opacity: 0, filter: blurIn },
        { yPercent: 0, opacity: 1, filter: 'blur(0px)', duration: 0.3, ease: 'power3.out', stagger: (span - 0.3) / Math.max(1, els.length - 1) },
        at);
    };
    const textOut = (name, at) => {
      tl.to(lines(name), { yPercent: -105, opacity: 0, filter: blurOut, duration: 0.24, ease: 'power2.in', stagger: 0.02 }, at);
    };
    // Compteur animé
    const counter = (el, from, to, at, dur = 0.5) => {
      const o = { v: from };
      el.textContent = from;
      tl.to(o, { v: to, duration: dur, ease: 'power2.out', onUpdate: () => { el.textContent = Math.round(o.v) || 0; } }, at);
    };

    /* --- 2. Hero : sortie ------------------------------------------- */
    tl.to('.js-hero-in', { autoAlpha: 0, y: -24, duration: 0.3, stagger: 0.04 }, 0.35);
    tl.to('.js-backdrop-word span', { yPercent: -60, opacity: 0, filter: blurOut, duration: 0.35, stagger: 0.03, ease: 'power2.in' }, 0.4);
    tl.set(scr('hero'), { autoAlpha: 0 }, 0.95);
    tl.to(s, { autoSpin: 0, duration: 0.9, ease: 'power1.inOut' }, 0.4);

    /* --- 3. Zero sugar ---------------------------------------------- */
    pose(P.sugar, 0.5, 1);
    show('sugar', 0.95, 2.55);
    textIn('sugar', 1.0);
    counter($('.js-count-sugar'), 36, 0, 1.05, 0.55);
    textOut('sugar', 2.2);

    /* --- 4. 160 mg : zoom serré sur l'étiquette ---------------------- */
    pose(P.caffeine, 2.2, 1, 'power3.inOut');
    show('caffeine', 2.65, 4.35);
    textIn('caffeine', 2.7);
    counter($('.js-count-160'), 0, 160, 2.8, 0.7);
    tl.to(s, { rotY: '+=0.12', duration: 0.8 }, 3.2); // micro-dérive pendant la pause
    textOut('caffeine', 4.0);

    /* --- 5. -4° : froid, gouttes, givre ------------------------------ */
    pose(P.cold, 4.0, 1);
    tl.to(s, { overrideW: 1, duration: 0.8, ease: 'power1.inOut' }, 4.0);
    tl.to('.backdrop', { backgroundColor: '#050a10', duration: 0.8 }, 4.0);
    tl.to(s, { frost: 1, duration: 0.7 }, 4.3);
    tl.to(s, { drops: 1, duration: 0.8, ease: 'power1.out' }, 4.45);
    show('cold', 4.65, 6.25);
    textIn('cold', 4.7);
    counter($('.js-count-cold'), 12, -4, 4.8, 0.6);
    textOut('cold', 5.9);

    /* --- 6. Vue éclatée --------------------------------------------- */
    tl.to(s, { frost: 0, duration: 0.6 }, 5.95);
    tl.to(s, { drops: 0, duration: 0.6 }, 6.1);
    tl.to(s.override, { ...NEUTRAL, duration: 0.7 }, 6.0);
    tl.to('.backdrop', { backgroundColor: '#050505', duration: 0.8 }, 6.0);
    pose(P.anatomy, 5.9, 0.9);
    show('anatomy', 6.3, 9.05);
    textIn('anatomy', 6.35, 0.35);
    tl.to(s, { explode: 1, duration: 0.8, ease: 'power3.inOut' }, 6.8);
    tl.to(s, { rotY: '+=0.7', rotX: '-=0.08', duration: 1.5 }, 6.8);
    tl.fromTo('.js-legend', { autoAlpha: 0 }, { autoAlpha: 1, duration: 0.25, stagger: 0.12 }, 7.25);
    tl.fromTo('.legend__line', { scaleX: 0 }, { scaleX: 1, duration: 0.25, stagger: 0.12 }, 7.25);
    tl.to('.js-legend', { autoAlpha: 0, duration: 0.2, stagger: 0.05 }, 8.1);
    tl.to(s, { explode: 0, duration: 0.7, ease: 'power3.inOut' }, 8.3);
    textOut('anatomy', 8.75);

    /* --- 7. Saveurs -------------------------------------------------- */
    pose(P.flavors, 8.8, 0.85);
    tl.to(s, { overrideW: 0, duration: 0.6 }, 8.9);
    show('flavors', 9.25, 10.95);
    textIn('flavors', 9.3);
    textOut('flavors', 10.6);

    /* --- 8. Built different ---------------------------------------- */
    pose(P.compare, 10.6, 0.85);
    show('compare', 11.0, 12.85);
    textIn('compare', 11.05, 0.3);
    const rows = $$('.table__row');
    tl.fromTo(rows, { autoAlpha: 0, y: 26, filter: blurIn }, { autoAlpha: 1, y: 0, filter: 'blur(0px)', duration: 0.3, ease: 'power3.out', stagger: 0.2 }, 11.25);
    tl.fromTo('.table .bar', { '--p': 0 }, { '--p': 1, duration: 0.35, ease: 'power2.out', stagger: 0.1 }, 11.45);
    tl.to(rows, { autoAlpha: 0, y: -20, duration: 0.22, stagger: 0.04 }, 12.45);
    textOut('compare', 12.5);

    /* --- 9. Final : trois canettes ---------------------------------- */
    pose(P.final, 12.5, 0.9);
    tl.to(s, { trio: 1, duration: 0.85, ease: 'power3.out' }, 12.9);
    tl.fromTo('.js-backdrop-word span', { yPercent: 140, opacity: 1, filter: 'blur(0px)' }, { yPercent: 0, duration: 0.6, stagger: 0.05, ease: 'power3.out', immediateRender: false }, 12.95);
    show('final', 13.25);
    textIn('final', 13.3, 0.5);

    // Remplissage jusqu'à TOTAL pour que 1 unité = 100vh de scroll
    tl.set({}, {}, TOTAL);

    return () => { master = null; };
  });

  /* --- Pied de page : la scène 3D et le fond remontent avec lui ------ */
  const footer = $('.footer');
  gsap.to(['.webgl', '.backdrop'], {
    y: () => -footer.offsetHeight,
    ease: 'none',
    scrollTrigger: { trigger: footer, start: 'top bottom', end: 'bottom bottom', scrub: true, invalidateOnRefresh: true },
  });

  /* --- Légendes de la vue éclatée, collées aux pièces --------------- */
  const legends = $$('.js-legend').map((el) => ({ el, part: el.dataset.part, left: el.classList.contains('legend--left') }));
  const anatomy = $('[data-screen="anatomy"]');
  const isMobile = () => window.matchMedia(MOBILE_Q).matches;

  let lastAccent = '';
  scene.onFrame(() => {
    // Couleur d'accent de la page = couleur du halo
    const a = scene.accentCSS();
    if (a !== lastAccent) { root.style.setProperty('--accent', a); lastAccent = a; }

    if (anatomy.style.visibility !== 'visible' && getComputedStyle(anatomy).visibility !== 'visible') return;
    const mob = isMobile();
    legends.forEach((l) => {
      const left = l.left && !mob;
      const p = scene.project(l.part, left ? -1 : 1);
      const w = l.el.offsetWidth, h = l.el.offsetHeight;
      const x = left ? p.x - w + 4.5 : p.x - 4.5;
      l.el.classList.toggle('legend--left', left);
      l.el.style.transform = `translate3d(${x.toFixed(1)}px, ${(p.y - h / 2).toFixed(1)}px, 0)`;
    });
  });

  /* --- Sélection de saveur ------------------------------------------ */
  let current = 0;
  const swatches = $$('.swatch');
  const nameEl = $('.js-flavor-name');
  const noteEl = $('.js-flavor-note');
  scene.setSideFlavors(1, 2);

  function pickFlavor(i) {
    if (i === current) return;
    current = i;
    const f = FLAVORS[i];
    swatches.forEach((b, j) => {
      b.classList.toggle('is-active', j === i);
      b.setAttribute('aria-checked', String(j === i));
    });
    // Tour rapide, changement d'étiquette à mi-rotation (face cachée)
    gsap.to(s, { spin: s.spin + TAU, duration: reduced ? 0 : 1.1, ease: 'power3.inOut', overwrite: 'auto' });
    gsap.delayedCall(reduced ? 0 : 0.42, () => scene.setMainFlavor(i));
    gsap.to(s.flavor, { ...scene.colorOf(f.color), duration: reduced ? 0 : 1.1, ease: 'power2.inOut' });
    const others = [0, 1, 2].filter((k) => k !== i);
    scene.setSideFlavors(others[0], others[1]);
    // Nom de la saveur
    gsap.timeline()
      .to([nameEl, noteEl], { yPercent: -100, opacity: 0, duration: reduced ? 0 : 0.25, ease: 'power2.in' })
      .add(() => { nameEl.textContent = f.name; noteEl.textContent = f.note; })
      .fromTo([nameEl, noteEl], { yPercent: 100, opacity: 0 }, { yPercent: 0, opacity: 1, duration: reduced ? 0 : 0.4, ease: 'power3.out', stagger: 0.05 });
  }
  swatches.forEach((b) => b.addEventListener('click', () => pickFlavor(+b.dataset.flavor)));

  /* --- Liens « Order » : défilement jusqu'au final ------------------ */
  const goFinal = (e) => {
    e.preventDefault();
    const st = master?.scrollTrigger;
    if (!st) return;
    const y = st.start + (13.9 / TOTAL) * (st.end - st.start);
    if (lenis) lenis.scrollTo(y, { duration: 2.4 });
    else window.scrollTo({ top: y, behavior: reduced ? 'auto' : 'smooth' });
  };
  $$('.js-order').forEach((a) => a.addEventListener('click', goFinal));
  $$('.footer a[href="#final"]').forEach((a) => a.addEventListener('click', goFinal));
  $$('a[href="#top"]').forEach((a) => a.addEventListener('click', (e) => {
    e.preventDefault();
    if (lenis) lenis.scrollTo(0, { duration: 2 }); else window.scrollTo({ top: 0, behavior: reduced ? 'auto' : 'smooth' });
  }));

  // Bouton final : boutique fictive
  const big = $('.btn--big');
  big.addEventListener('click', (e) => {
    e.preventDefault();
    const label = big.firstChild;
    const prev = label.textContent;
    label.textContent = 'Bientôt disponible ';
    setTimeout(() => (label.textContent = prev), 2200);
  });
}

boot();
