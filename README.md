# VOLT ZERO — landing page 3D pilotée par le scroll

Page produit cinématique pour une boisson énergisante **fictive**. Une seule canette 3D, générée entièrement par code, traverse dix sections au rythme du scroll.

## Lancer en local

Aucun build. Servez simplement la racine :

```bash
python3 -m http.server 8000
# puis http://localhost:8000
```

## Structure

| Fichier | Rôle |
|---|---|
| `index.html` | Balisage des sections, loader, nav, chargement des CDN |
| `css/style.css` | Palette, typographie (Anton / Inter), mise en page, responsive, mouvement réduit |
| `js/scene.js` | Scène Three.js : canette (LatheGeometry + étiquettes canvas), gouttes, givre, halos, lumières |
| `js/main.js` | Lenis + GSAP ScrollTrigger : timeline maîtresse, poses par section, textes, compteurs, saveurs |

## Stack

Three.js 0.160 · GSAP 3.12.5 + ScrollTrigger · Lenis 1.1.13 — via CDN, versions figées. Aucune image ni modèle externe.

## Modifier les poses

Les poses de la canette sont dans `POSES` en haut de `js/main.js` (une table bureau, une table portrait). L'unité de la timeline est un écran de scroll (100vh).
