/* =====================================================================
   VOLT ZERO — scene.js
   ---------------------------------------------------------------------
   Unique scène Three.js fixe en arrière-plan.
   Tout est généré par code : profil de canette (LatheGeometry),
   étiquettes (canvas 2D), gouttelettes (InstancedMesh), givre (Points),
   halos (dégradés radiaux en canvas).

   La scène n'anime rien d'elle-même hormis les micro-mouvements
   (flottement, rotation lente du hero, souris). Toutes les poses sont
   lues dans l'objet `state`, que main.js anime avec GSAP.
   ===================================================================== */

import * as THREE from 'three';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';

/* ---------------------------------------------------------------------
   Saveurs
   --------------------------------------------------------------------- */
export const FLAVORS = [
  { id: 'citron',  name: 'Citron électrique', short: 'Citron',  color: '#E8FF2A', deep: '#7d8f00', ink: '#0b0b0b', note: 'Yuzu · lime · zeste' },
  { id: 'berry',   name: 'Fruits rouges',     short: 'Berry',   color: '#FF2D55', deep: '#7a0820', ink: '#0b0b0b', note: 'Framboise · cassis · grenade' },
  { id: 'glacier', name: 'Glacier',           short: 'Glacier', color: '#3DD6FF', deep: '#05507a', ink: '#0b0b0b', note: 'Menthe glaciale · agrumes' },
];

/* ---------------------------------------------------------------------
   Dimensions (unités monde). Canette 33 cl : Ø 66 mm × 115 mm
   → rayon 0.66, hauteur ≈ 2.31
   --------------------------------------------------------------------- */
const R = 0.66;
const BODY_BOTTOM = -0.95;
const BODY_TOP = 0.80;
const BODY_H = BODY_TOP - BODY_BOTTOM;
const LID_Y = 1.095;

/* =====================================================================
   Utilitaires canvas
   ===================================================================== */
function makeCanvas(w, h) {
  const c = document.createElement('canvas');
  c.width = w; c.height = h;
  return c;
}

/** Dégradé radial blanc → transparent, utilisé pour les halos et le givre. */
function radialTexture(size = 256, stops = [[0, 1], [0.35, 0.45], [1, 0]]) {
  const c = makeCanvas(size, size);
  const ctx = c.getContext('2d');
  const g = ctx.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
  stops.forEach(([p, a]) => g.addColorStop(p, `rgba(255,255,255,${a})`));
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, size, size);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

/** Répète un texte sur toute la largeur sans chevauchement à la couture u = 0/1. */
function repeatText(ctx, txt, W, y, offset = 0) {
  const tw = ctx.measureText(txt).width;
  const n = Math.max(1, Math.floor(W / tw));
  const step = W / n;
  for (let i = -1; i <= n; i++) ctx.fillText(txt, offset + i * step, y);
}

/** Mélange deux couleurs hex. */
function mixHex(a, b, t) {
  const ca = new THREE.Color(a), cb = new THREE.Color(b);
  return '#' + ca.lerp(cb, t).getHexString();
}

/** Tracé de l'éclair stylisé, dans une boîte 100 × 200 centrée sur (0,0). */
function boltPath(ctx) {
  ctx.beginPath();
  ctx.moveTo(18, -100);
  ctx.lineTo(-46, 12);
  ctx.lineTo(-4, 12);
  ctx.lineTo(-22, 100);
  ctx.lineTo(48, -20);
  ctx.lineTo(4, -20);
  ctx.lineTo(30, -100);
  ctx.closePath();
}

/* =====================================================================
   Étiquette — dessinée dans un canvas puis enroulée sur le corps.
   Le centre horizontal du canvas (u = 0.5) fait face à la caméra.
   ===================================================================== */
function drawLabel(flavor, W, H) {
  const c = makeCanvas(W, H);
  const ctx = c.getContext('2d');
  const k = H / 1000; // facteur d'échelle : tout est pensé pour H = 1000

  // --- Fond : dégradé vertical + léger vignettage
  const bg = ctx.createLinearGradient(0, 0, 0, H);
  bg.addColorStop(0, mixHex(flavor.color, '#ffffff', 0.12));
  bg.addColorStop(0.45, flavor.color);
  bg.addColorStop(1, mixHex(flavor.color, flavor.deep, 0.75));
  ctx.fillStyle = bg;
  ctx.fillRect(0, 0, W, H);

  // --- Lignes brossées très fines (rendu métal imprimé)
  ctx.globalAlpha = 0.05;
  for (let y = 0; y < H; y += 3) {
    ctx.fillStyle = Math.random() > 0.5 ? '#ffffff' : '#000000';
    ctx.fillRect(0, y, W, 1);
  }
  ctx.globalAlpha = 1;

  // --- Bandeaux haut et bas
  const topBand = 70 * k, botBand = 120 * k;
  ctx.fillStyle = flavor.ink;
  ctx.fillRect(0, 0, W, topBand);
  ctx.fillRect(0, H - botBand, W, botBand);

  // Texte répété dans le bandeau du haut
  ctx.fillStyle = flavor.color;
  ctx.font = `600 ${26 * k}px Inter, sans-serif`;
  ctx.textBaseline = 'middle';
  const topTxt = 'ZERO SUGAR   ·   FULL CHARGE   ·   ENERGY DRINK   ·   ';
  if ('letterSpacing' in ctx) ctx.letterSpacing = `${6 * k}px`;
  repeatText(ctx, topTxt, W, topBand / 2, W * 0.03);

  // Mentions légales dans le bandeau du bas
  if ('letterSpacing' in ctx) ctx.letterSpacing = '0px';
  ctx.fillStyle = 'rgba(245,245,245,0.75)';
  ctx.font = `400 ${17 * k}px Inter, sans-serif`;
  const legal1 = 'Teneur élevée en caféine (48 mg/100 ml). Déconseillé aux enfants et aux femmes enceintes ou allaitantes.   330 ml ℮   ';
  const legal2 = 'Ingrédients : eau gazéifiée, acidifiant (acide citrique), taurine (0,3 %), arômes naturels, caféine, édulcorants, vitamines B3 B5 B6 B12.   Produit fictif — VOLT ZERO.   ';
  repeatText(ctx, legal1, W, H - botBand + 38 * k);
  repeatText(ctx, legal2, W, H - botBand + 72 * k, W * 0.11);

  const cx = W / 2;                 // face avant
  const mid = topBand + (H - topBand - botBand) / 2;

  // --- « VOLT » vertical, géant (lecture de bas en haut)
  const word = 'VOLT';
  ctx.save();
  ctx.translate(cx, mid);
  ctx.rotate(-Math.PI / 2);
  let fs = 400 * k;
  ctx.font = `400 ${fs}px Anton, Impact, sans-serif`;
  const targetLen = (H - topBand - botBand) * 0.86;
  fs *= targetLen / ctx.measureText(word).width;
  ctx.font = `400 ${fs}px Anton, Impact, sans-serif`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillStyle = flavor.ink;
  ctx.fillText(word, 0, fs * 0.04);
  ctx.restore();
  const capW = fs * 0.78; // largeur approximative occupée par le mot sur u

  // --- « ZERO » en contour, à gauche du logo
  ctx.save();
  ctx.translate(cx - capW * 0.62 - 125 * k, mid);
  ctx.rotate(-Math.PI / 2);
  ctx.font = `400 ${150 * k}px Anton, Impact, sans-serif`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.lineWidth = 3 * k;
  ctx.strokeStyle = flavor.ink;
  ctx.strokeText('ZERO', 0, 0);
  ctx.restore();

  // --- Éclair stylisé, à droite du logo
  ctx.save();
  ctx.translate(cx + capW * 0.5 + 80 * k, mid - 150 * k);
  ctx.scale(1.25 * k, 1.25 * k);
  boltPath(ctx);
  ctx.fillStyle = flavor.ink;
  ctx.fill();
  ctx.restore();

  // Mentions sous l'éclair
  ctx.save();
  ctx.translate(cx + capW * 0.5 + 80 * k, mid + 150 * k);
  ctx.rotate(-Math.PI / 2);
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillStyle = flavor.ink;
  ctx.font = `700 ${30 * k}px Inter, sans-serif`;
  ctx.fillText('160 MG', 0, -22 * k);
  ctx.font = `500 ${20 * k}px Inter, sans-serif`;
  ctx.fillText('CAFFEINE', 0, 14 * k);
  ctx.restore();

  // --- Côtés (u = 0.25 et 0.75) : nom de saveur et arguments
  const side = (x, lines) => {
    ctx.save();
    ctx.translate(x, mid);
    ctx.rotate(-Math.PI / 2);
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillStyle = flavor.ink;
    lines.forEach(([txt, font, dy]) => { ctx.font = font; ctx.fillText(txt, 0, dy * k); });
    ctx.restore();
  };
  side(W * 0.29, [
    [flavor.name.toUpperCase(), `400 ${90 * k}px Anton, Impact, sans-serif`, -30],
    [flavor.note.toUpperCase(), `500 ${22 * k}px Inter, sans-serif`, 50],
  ]);
  side(W * 0.71, [
    ['0 G SUGAR', `400 ${70 * k}px Anton, Impact, sans-serif`, -60],
    ['4 KCAL', `400 ${70 * k}px Anton, Impact, sans-serif`, 20],
    ['VITAMINS B3 · B5 · B6 · B12', `500 ${20 * k}px Inter, sans-serif`, 85],
  ]);

  // --- Dos (u = 0 / 1) : tableau nutritionnel + code-barres
  const back = (bx) => {
    const bw = 300 * k, bh = 430 * k;
    const x0 = bx - bw / 2, y0 = mid - bh / 2 - 40 * k;
    ctx.fillStyle = '#f5f5f5';
    ctx.fillRect(x0, y0, bw, bh);
    ctx.fillStyle = '#0b0b0b';
    ctx.textBaseline = 'alphabetic';
    ctx.textAlign = 'left';
    ctx.font = `800 ${30 * k}px Inter, sans-serif`;
    ctx.fillText('Nutrition', x0 + 18 * k, y0 + 44 * k);
    ctx.font = `400 ${17 * k}px Inter, sans-serif`;
    ctx.fillText('Valeurs moyennes pour 330 ml', x0 + 18 * k, y0 + 72 * k);
    ctx.fillRect(x0 + 18 * k, y0 + 86 * k, bw - 36 * k, 5 * k);
    const rows = [['Énergie', '17 kJ / 4 kcal'], ['Matières grasses', '0 g'], ['Glucides', '0,9 g'], ['dont sucres', '0 g'], ['Protéines', '0 g'], ['Sel', '0,2 g'], ['Caféine', '160 mg'], ['Taurine', '1000 mg']];
    rows.forEach(([a, b], i) => {
      const y = y0 + 122 * k + i * 37 * k;
      ctx.textAlign = 'left'; ctx.fillText(a, x0 + 18 * k, y);
      ctx.textAlign = 'right'; ctx.fillText(b, x0 + bw - 18 * k, y);
      ctx.fillRect(x0 + 18 * k, y + 12 * k, bw - 36 * k, 1 * k);
    });
    // Code-barres
    const by = y0 + bh + 30 * k;
    ctx.fillStyle = '#f5f5f5';
    ctx.fillRect(x0, by, bw, 120 * k);
    ctx.fillStyle = '#0b0b0b';
    let x = x0 + 20 * k;
    let seed = 7;
    while (x < x0 + bw - 24 * k) {
      seed = (seed * 9301 + 49297) % 233280;
      const w = (1 + (seed % 4)) * 2.2 * k;
      ctx.fillRect(x, by + 14 * k, w, 74 * k);
      x += w + (1 + (seed % 3)) * 2.4 * k;
    }
    ctx.font = `400 ${16 * k}px Inter, sans-serif`;
    ctx.textAlign = 'center';
    ctx.fillText('3 770 014 160 000', bx, by + 108 * k);
  };
  back(0);
  back(W); // deux moitiés : le dos est à cheval sur la couture u = 0 / 1

  return c;
}

/* =====================================================================
   Géométries — créées une seule fois, partagées par les 3 canettes
   ===================================================================== */
function smoothProfile(points, divisions) {
  return new THREE.SplineCurve(points.map(([x, y]) => new THREE.Vector2(x, y))).getPoints(divisions);
}

function buildGeometries() {
  const SEG = 128;

  // --- Épaule + col + bord roulé + opercule (de bas en haut vers le centre)
  const topProfile = [
    ...smoothProfile([[R, BODY_TOP], [R - 0.004, 0.86], [0.63, 0.93], [0.575, 0.995], [0.53, 1.045], [0.515, 1.075]], 40),
    // bord roulé (petit biseau arrondi)
    ...smoothProfile([[0.515, 1.08], [0.523, 1.11], [0.526, 1.135], [0.516, 1.155], [0.498, 1.16], [0.482, 1.152], [0.476, 1.13]], 24),
    // paroi intérieure + gorge de l'opercule
    ...smoothProfile([[0.475, 1.12], [0.47, 1.095], [0.462, 1.083], [0.45, 1.084], [0.44, 1.092]], 12),
    // panneau de l'opercule, très légèrement bombé
    new THREE.Vector2(0.36, LID_Y + 0.004),
    new THREE.Vector2(0.18, LID_Y + 0.008),
    new THREE.Vector2(0.0001, LID_Y + 0.009),
  ];
  const top = new THREE.LatheGeometry(topProfile, SEG);

  // --- Fond : dôme intérieur, anneau d'appui, pied resserré
  const bottomProfile = smoothProfile([
    [0.0001, -0.985], [0.2, -0.998], [0.34, -1.035], [0.42, -1.095], [0.455, -1.14],
    [0.478, -1.152], [0.505, -1.147], [0.56, -1.115], [0.615, -1.05], [0.648, -0.99], [R, -0.955], [R, BODY_BOTTOM],
  ], 60);
  const bottom = new THREE.LatheGeometry(bottomProfile, SEG);

  // --- Corps cylindrique (porte l'étiquette). thetaStart = π pour que
  //     u = 0.5 (centre du canvas) soit face caméra (+Z).
  const body = new THREE.CylinderGeometry(R, R, BODY_H, SEG, 1, true, Math.PI, Math.PI * 2);
  body.translate(0, (BODY_TOP + BODY_BOTTOM) / 2, 0);
  const bodyInner = new THREE.CylinderGeometry(R - 0.006, R - 0.006, BODY_H, 64, 1, true);
  bodyInner.translate(0, (BODY_TOP + BODY_BOTTOM) / 2, 0);

  // --- Languette : forme extrudée avec trou pour le doigt
  const tabShape = new THREE.Shape();
  const tw = 0.075, tl0 = -0.12, tl1 = 0.24;
  tabShape.moveTo(tl0 + tw, -tw);
  tabShape.lineTo(tl1 - tw, -tw);
  tabShape.absarc(tl1 - tw, 0, tw, -Math.PI / 2, Math.PI / 2, false);
  tabShape.lineTo(tl0 + tw, tw);
  tabShape.absarc(tl0 + tw, 0, tw, Math.PI / 2, Math.PI * 1.5, false);
  const hole = new THREE.Path();
  hole.absellipse(0.135, 0, 0.068, 0.044, 0, Math.PI * 2, true);
  tabShape.holes.push(hole);
  const tab = new THREE.ExtrudeGeometry(tabShape, {
    depth: 0.008, bevelEnabled: true, bevelThickness: 0.004, bevelSize: 0.005, bevelSegments: 2, curveSegments: 24,
  });
  tab.rotateX(-Math.PI / 2);

  // --- Ligne de rupture de l'ouverture : anneau fin en relief
  // Forme simple et lisible : ellipse allongée côté opposé au trou
  const score = new THREE.Shape();
  score.absellipse(-0.24, 0, 0.15, 0.115, 0, Math.PI * 2, false);
  const scoreHole = new THREE.Path();
  scoreHole.absellipse(-0.24, 0, 0.142, 0.107, 0, Math.PI * 2, true);
  score.holes.push(scoreHole);
  const scoreGeo = new THREE.ExtrudeGeometry(score, { depth: 0.003, bevelEnabled: false, curveSegments: 48 });
  scoreGeo.rotateX(-Math.PI / 2);

  const rivet = new THREE.CylinderGeometry(0.028, 0.032, 0.018, 24);

  // --- Gouttelette (sphère basse définition, aplatie par instance)
  const drop = new THREE.SphereGeometry(1, 12, 8);

  return { top, bottom, body, bodyInner, tab, scoreGeo, rivet, drop };
}

/* =====================================================================
   Environment map : RoomEnvironment assombrie + bandes lumineuses
   verticales (softbox) → reflets contrastés typés « studio produit ».
   ===================================================================== */
function studioEnvironment() {
  const room = new RoomEnvironment();
  room.traverse((o) => {
    if (!o.isMesh) return;
    if (o.material.isMeshBasicMaterial) o.material.color.multiplyScalar(0.6); // plafonniers adoucis
    else o.material.color.multiplyScalar(0.18);                              // murs et objets sombres
  });
  const strip = (x, z, w, h, intensity, ry) => {
    const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ color: new THREE.Color(intensity, intensity, intensity), side: THREE.DoubleSide }));
    m.position.set(x, 1, z);
    m.rotation.y = ry;
    room.add(m);
  };
  strip(-6, 2, 1.2, 9, 9, Math.PI / 2);   // grande bande gauche
  strip(6, -1, 0.7, 9, 5, -Math.PI / 2);  // bande droite plus fine
  strip(0, -7, 6, 1.0, 3, 0);             // liseré arrière
  return room;
}

/* =====================================================================
   Création de la scène
   ===================================================================== */
export async function createScene(canvas, { onProgress = () => {}, reducedMotion = false } = {}) {
  const isSmall = Math.min(window.innerWidth, window.innerHeight) < 700;

  // --- Rendu
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: 'high-performance' });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setSize(window.innerWidth, window.innerHeight, false);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.05;
  renderer.setClearColor(0x000000, 0);

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(30, window.innerWidth / window.innerHeight, 0.1, 50);
  camera.position.set(0, 0, 7);

  // --- Environment map procédurale (reflets de studio)
  const pmrem = new THREE.PMREMGenerator(renderer);
  const envTex = pmrem.fromScene(studioEnvironment(), 0.04).texture;
  scene.environment = envTex;
  pmrem.dispose();
  onProgress(0.2);

  // --- Polices nécessaires à l'étiquette
  try {
    await Promise.all([
      document.fonts.load('400 100px Anton'),
      document.fonts.load('400 20px Inter'),
      document.fonts.load('700 20px Inter'),
    ]);
  } catch (e) { /* le dessin retombera sur Impact / sans-serif */ }
  onProgress(0.4);

  // --- Textures d'étiquette (une par saveur)
  const LW = isSmall ? 2048 : 3072;
  const LH = Math.round(LW / ((2 * Math.PI * R) / BODY_H)); // respecte le ratio circonférence / hauteur
  const maxAniso = renderer.capabilities.getMaxAnisotropy();
  const labels = FLAVORS.map((f, i) => {
    const t = new THREE.CanvasTexture(drawLabel(f, LW, LH));
    t.colorSpace = THREE.SRGBColorSpace;
    t.anisotropy = Math.min(8, maxAniso);
    onProgress(0.4 + 0.15 * (i + 1));
    return t;
  });

  const geo = buildGeometries();

  // --- Matériaux partagés
  const aluMat = new THREE.MeshPhysicalMaterial({
    color: 0xdfe2e7, metalness: 1, roughness: 0.16, envMapIntensity: 1.25, side: THREE.DoubleSide,
  });
  const aluInnerMat = new THREE.MeshStandardMaterial({ color: 0x8a8d92, metalness: 1, roughness: 0.45, side: THREE.BackSide });
  const makeBodyMat = (tex) => new THREE.MeshPhysicalMaterial({
    map: tex, metalness: 0.3, roughness: 0.34, clearcoat: 1, clearcoatRoughness: 0.06, envMapIntensity: 0.9,
  });
  const dropMat = new THREE.MeshPhysicalMaterial({
    color: 0xb8c4cc, metalness: 0.1, roughness: 0.02, clearcoat: 1, clearcoatRoughness: 0,
    transparent: true, opacity: 0, envMapIntensity: 3.2, depthWrite: false,
  });

  /** Construit une canette complète : trois groupes (opercule, corps, fond). */
  function buildCan(bodyMat, withDrops = false) {
    const root = new THREE.Group();
    root.rotation.order = 'XZY'; // tourne d'abord sur son axe, puis s'incline

    const top = new THREE.Group();
    top.add(new THREE.Mesh(geo.top, aluMat));
    const tab = new THREE.Mesh(geo.tab, aluMat);
    tab.position.set(0, LID_Y + 0.016, 0);
    tab.rotation.y = 0.15;
    const score = new THREE.Mesh(geo.scoreGeo, aluMat);
    score.position.set(0, LID_Y + 0.006, 0);
    score.rotation.y = 0.15;
    const rivet = new THREE.Mesh(geo.rivet, aluMat);
    rivet.position.set(0, LID_Y + 0.016, 0);
    top.add(tab, score, rivet);

    const body = new THREE.Group();
    body.add(new THREE.Mesh(geo.body, bodyMat));
    body.add(new THREE.Mesh(geo.bodyInner, aluInnerMat));

    const bottom = new THREE.Group();
    bottom.add(new THREE.Mesh(geo.bottom, aluMat));

    root.add(top, body, bottom);
    root.userData = { top, body, bottom, bodyMat };

    if (withDrops) {
      // --- Condensation : ~700 gouttes réparties sur le corps
      const COUNT = isSmall ? 420 : 720;
      const drops = new THREE.InstancedMesh(geo.drop, dropMat, COUNT);
      const d = new THREE.Object3D();
      for (let i = 0; i < COUNT; i++) {
        const a = Math.random() * Math.PI * 2;
        const y = BODY_BOTTOM + 0.08 + Math.random() * (BODY_H - 0.14);
        const big = Math.random() < 0.12;
        const s = big ? 0.016 + Math.random() * 0.016 : 0.005 + Math.random() * 0.009;
        d.position.set(Math.sin(a) * (R + 0.001), y, Math.cos(a) * (R + 0.001));
        d.lookAt(Math.sin(a) * 2, y, Math.cos(a) * 2);
        d.scale.set(s, s * (big ? 1.35 : 1.1), s * 0.42);
        d.updateMatrix();
        drops.setMatrixAt(i, d.matrix);
      }
      drops.visible = false;
      body.add(drops);
      root.userData.drops = drops;
    }
    return root;
  }

  // --- Canette principale + deux canettes du final
  const mainMat = makeBodyMat(labels[0]);
  const can = buildCan(mainMat, true);
  scene.add(can);

  const sideMats = [makeBodyMat(labels[1]), makeBodyMat(labels[2])];
  const sideCans = sideMats.map((m) => {
    const c = buildCan(m);
    c.visible = false;
    scene.add(c);
    return c;
  });

  // --- Halos (dégradés radiaux)
  const glowTex = radialTexture(256, [[0, 0.9], [0.25, 0.42], [0.55, 0.12], [1, 0]]);
  const glowMat = new THREE.MeshBasicMaterial({ map: glowTex, transparent: true, depthWrite: false, opacity: 0.8 });
  const glow = new THREE.Mesh(new THREE.PlaneGeometry(7, 7), glowMat);
  glow.position.z = -2.2;
  glow.renderOrder = -2;
  scene.add(glow);

  const floorTex = radialTexture(256, [[0, 1], [0.3, 0.5], [0.7, 0.08], [1, 0]]);
  const floorMat = new THREE.MeshBasicMaterial({ map: floorTex, transparent: true, depthWrite: false, opacity: 0.9, blending: THREE.AdditiveBlending });
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(3.4, 3.4), floorMat);
  floor.rotation.x = -Math.PI / 2;
  floor.renderOrder = -1;
  scene.add(floor);

  // Ombre de contact (assombrit le halo juste sous la canette)
  const contactTex = radialTexture(128, [[0, 0.85], [0.5, 0.35], [1, 0]]);
  const contactMat = new THREE.MeshBasicMaterial({ map: contactTex, color: 0x000000, transparent: true, depthWrite: false, opacity: 0.75 });
  const contact = new THREE.Mesh(new THREE.PlaneGeometry(1.7, 1.7), contactMat);
  contact.rotation.x = -Math.PI / 2;
  contact.renderOrder = -1;
  scene.add(contact);

  // --- Particules de givre
  const FROST = isSmall ? 220 : 420;
  const frostPos = new Float32Array(FROST * 3);
  const frostSeed = new Float32Array(FROST);
  for (let i = 0; i < FROST; i++) {
    frostPos[i * 3] = (Math.random() - 0.5) * 7;
    frostPos[i * 3 + 1] = (Math.random() - 0.5) * 4.5;
    frostPos[i * 3 + 2] = (Math.random() - 0.5) * 4 - 0.5;
    frostSeed[i] = Math.random() * 100;
  }
  const frostGeo = new THREE.BufferGeometry();
  frostGeo.setAttribute('position', new THREE.BufferAttribute(frostPos, 3));
  const frostMat = new THREE.PointsMaterial({
    map: radialTexture(64, [[0, 1], [0.4, 0.5], [1, 0]]), color: 0xd6f3ff, size: 0.045,
    transparent: true, opacity: 0, depthWrite: false, blending: THREE.AdditiveBlending, sizeAttenuation: true,
  });
  const frost = new THREE.Points(frostGeo, frostMat);
  frost.visible = false;
  scene.add(frost);

  // --- Éclairage studio
  const key = new THREE.DirectionalLight(0xffffff, 2.2);
  key.position.set(-3, 4, 5);
  const fill = new THREE.DirectionalLight(0xffffff, 0.35);
  fill.position.set(4, 0.5, 4);
  const rimL = new THREE.DirectionalLight(0xffffff, 3.2);
  rimL.position.set(-4, 1.5, -3);
  const rimR = new THREE.DirectionalLight(0xffffff, 3.2);
  rimR.position.set(4, 2, -3);
  scene.add(key, fill, rimL, rimR);
  onProgress(1);

  /* -------------------------------------------------------------------
     État piloté par GSAP (main.js)
     ------------------------------------------------------------------- */
  const startColor = new THREE.Color(FLAVORS[0].color);
  const state = {
    // pose de la canette principale
    x: 0, y: 0, z: 0, rotX: 0, rotY: 0, rotZ: 0, scale: 1,
    explode: 0,          // 0 → 1 : vue éclatée
    drops: 0,            // 0 → 1 : condensation
    frost: 0,            // 0 → 1 : givre
    autoSpin: 1,         // poids de la rotation lente du hero
    trio: 0,             // 0 → 1 : canettes latérales du final
    trioGap: 1.55,       // écart horizontal des canettes latérales
    glow: 1,             // intensité du halo arrière
    floor: 1,            // intensité du halo au sol
    spin: 0,             // tour rapide au changement de saveur (radians)
    // couleurs (sRGB 0..1)
    flavor: { r: startColor.r, g: startColor.g, b: startColor.b },
    override: { r: 1, g: 1, b: 1 },
    overrideW: 0,        // 0 = couleur de la saveur, 1 = couleur imposée par la section
  };

  // Pointeur (souris ou doigt), normalisé -1..1
  const pointer = { x: 0, y: 0, sx: 0, sy: 0 };
  if (!reducedMotion) {
    window.addEventListener('pointermove', (e) => {
      pointer.x = (e.clientX / window.innerWidth) * 2 - 1;
      pointer.y = (e.clientY / window.innerHeight) * 2 - 1;
    }, { passive: true });
  }

  /* -------------------------------------------------------------------
     Boucle de rendu
     ------------------------------------------------------------------- */
  const clock = new THREE.Clock();
  const halo = new THREE.Color();
  const tmp = new THREE.Color();
  const v3 = new THREE.Vector3();
  let autoAngle = 0;
  let elapsed = 0;
  let running = false;
  let rafId = 0;
  const listeners = [];

  function currentHalo() {
    halo.setRGB(state.flavor.r, state.flavor.g, state.flavor.b);
    tmp.setRGB(state.override.r, state.override.g, state.override.b);
    return halo.lerp(tmp, state.overrideW);
  }

  function update(dt) {
    elapsed += dt;
    const s = state;

    // Rotation lente du hero ; quand son poids baisse, l'angle accumulé
    // revient en douceur au tour complet le plus proche (aucun saut).
    if (!reducedMotion) autoAngle += dt * 0.45 * s.autoSpin;
    const nearest = Math.round(autoAngle / (Math.PI * 2)) * Math.PI * 2;
    autoAngle += (nearest - autoAngle) * Math.min(1, (1 - s.autoSpin) * dt * 2.5);

    // Souris amortie
    pointer.sx += (pointer.x - pointer.sx) * Math.min(1, dt * 3);
    pointer.sy += (pointer.y - pointer.sy) * Math.min(1, dt * 3);

    const bob = reducedMotion ? 0 : Math.sin(elapsed * 1.1) * 0.035;

    can.position.set(s.x, s.y + bob, s.z);
    can.rotation.set(
      s.rotX + pointer.sy * 0.1,
      s.rotY + autoAngle + s.spin + pointer.sx * 0.22,
      s.rotZ - pointer.sx * 0.04,
    );
    can.scale.setScalar(s.scale);

    // Vue éclatée
    const e = s.explode;
    can.userData.top.position.y = e * 0.8;
    can.userData.top.rotation.y = e * 0.9;
    can.userData.bottom.position.y = -e * 0.72;
    can.userData.bottom.rotation.y = -e * 0.5;

    // Condensation
    const drops = can.userData.drops;
    drops.visible = s.drops > 0.005;
    dropMat.opacity = s.drops * 0.42;
    mainMat.clearcoatRoughness = 0.08 + s.drops * 0.25;
    mainMat.roughness = 0.3 + s.drops * 0.12;

    // Givre : dérive lente vers le haut avec oscillation
    frost.visible = s.frost > 0.005;
    if (frost.visible) {
      frostMat.opacity = s.frost * 0.9;
      const p = frostGeo.attributes.position.array;
      for (let i = 0; i < FROST; i++) {
        p[i * 3 + 1] += dt * (0.08 + (frostSeed[i] % 1) * 0.12);
        p[i * 3] += Math.sin(elapsed * 0.6 + frostSeed[i]) * dt * 0.05;
        if (p[i * 3 + 1] > 2.4) p[i * 3 + 1] = -2.4;
      }
      frostGeo.attributes.position.needsUpdate = true;
    }

    // Canettes latérales (final) : elles sortent de derrière la principale
    const t = s.trio;
    sideCans.forEach((c, i) => {
      c.visible = t > 0.002;
      if (!c.visible) return;
      const dir = i === 0 ? -1 : 1;
      c.position.set(s.x + dir * s.trioGap * t, s.y + Math.sin(elapsed * 1.1 + i * 2) * 0.03 * t, s.z - 0.5 * (1 - t) - 0.15);
      c.rotation.set(0, dir * -0.35 + (reducedMotion ? 0 : Math.sin(elapsed * 0.4 + i) * 0.15), dir * 0.06 * t);
      c.scale.setScalar(s.scale * (0.6 + 0.4 * t));
    });

    // Halos
    const col = currentHalo();
    glowMat.color.copy(col);
    glowMat.opacity = 0.75 * s.glow;
    glow.position.set(s.x * 0.85, s.y + 0.1, s.z - 2.2);
    glow.scale.setScalar(0.7 + s.scale * 0.5 + t * 0.6);

    floorMat.color.copy(col);
    floorMat.opacity = 0.85 * s.floor;
    const baseY = s.y - 1.17 * s.scale - e * 0.72 * s.scale;
    floor.position.set(s.x, baseY, s.z);
    floor.scale.set(s.scale * (1 + t * 1.6), s.scale, 1);
    contact.position.set(s.x, baseY + 0.002, s.z);
    contact.scale.setScalar(s.scale);
    contactMat.opacity = 0.75 * s.floor * (1 - Math.min(1, Math.abs(s.rotZ) * 2));

    // Contre-jours colorés
    rimL.color.copy(col);
    rimR.color.copy(col).lerp(tmp.set(0xffffff), 0.35);

    listeners.forEach((fn) => fn(dt));
  }

  function frame() {
    if (!running) return;
    const dt = Math.min(clock.getDelta(), 1 / 20);
    update(dt);
    renderer.render(scene, camera);
    rafId = requestAnimationFrame(frame);
  }

  function start() {
    if (running || document.hidden) return;
    running = true;
    clock.getDelta();
    rafId = requestAnimationFrame(frame);
  }
  function stop() {
    running = false;
    cancelAnimationFrame(rafId);
  }

  // Rendu en pause quand l'onglet est caché
  document.addEventListener('visibilitychange', () => (document.hidden ? stop() : start()));

  function resize() {
    const w = window.innerWidth, h = window.innerHeight;
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  }
  window.addEventListener('resize', resize);

  /* -------------------------------------------------------------------
     API publique
     ------------------------------------------------------------------- */
  return {
    state,
    flavors: FLAVORS,
    start,
    stop,
    resize,
    /** Ajoute une fonction appelée à chaque frame (après la mise à jour). */
    onFrame(fn) { listeners.push(fn); },
    /** Change l'étiquette de la canette principale. */
    setMainFlavor(i) { mainMat.map = labels[i]; mainMat.needsUpdate = true; },
    /** Étiquettes des deux canettes latérales du final. */
    setSideFlavors(a, b) {
      sideMats[0].map = labels[a]; sideMats[0].needsUpdate = true;
      sideMats[1].map = labels[b]; sideMats[1].needsUpdate = true;
    },
    /** Convertit une couleur hex en composantes de travail {r,g,b} (pour GSAP). */
    colorOf(hex) { const c = new THREE.Color(hex); return { r: c.r, g: c.g, b: c.b }; },
    /** Couleur courante du halo, au format CSS. */
    accentCSS() { return '#' + currentHalo().getHexString(THREE.SRGBColorSpace); },
    /** Projette en pixels écran le centre d'une partie ('top' | 'body' | 'bottom'),
     *  décalé de `side` rayons vers la gauche (-1) ou la droite (+1). */
    project(part, side = 0) {
      const ud = can.userData;
      const obj = ud[part];
      const local = { top: 0.99, body: -0.075, bottom: -1.04 }[part];
      obj.updateWorldMatrix(true, false);
      v3.set(0, local, 0).applyMatrix4(obj.matrixWorld);
      v3.x += side * R * 0.98 * can.scale.x;
      v3.project(camera);
      return { x: (v3.x * 0.5 + 0.5) * window.innerWidth, y: (-v3.y * 0.5 + 0.5) * window.innerHeight, visible: v3.z < 1 };
    },
    renderOnce() { update(0); renderer.render(scene, camera); },
  };
}
