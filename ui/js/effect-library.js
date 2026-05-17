/**
 * Effect Library — canonical definition of all available effects,
 * their parameters, and the default effect stack.
 *
 * Loaded globally before wizard.js so all view scripts can reference
 * EFFECT_LIBRARY, buildDefaultEffectStack(), and buildParamUI().
 */

const EFFECT_LIBRARY = {

  // ── Atmosphere ─────────────────────────────────────────────────────────
  smoke: {
    label: 'Smoke / Mist', category: 'atmosphere', layer: 'L1',
    defaults: { density: 0.7 },
    params: [
      { key: 'density', type: 'range', label: 'Density',  min: 0.10, max: 1.00, step: 0.05, default: 0.7 },
    ],
  },
  flash: {
    label: 'Flash', category: 'atmosphere', layer: 'L1',
    defaults: {},
    params: [],
  },
  rain: {
    label: 'Rain / Drizzle', category: 'atmosphere', layer: 'L1',
    defaults: { density: 0.6, angle: 15 },
    params: [
      { key: 'density', type: 'range', label: 'Density',  min: 0.1, max: 1.0, step: 0.05, default: 0.6 },
      { key: 'angle',   type: 'range', label: 'Angle °',  min: -30, max: 30,  step: 5,    default: 15  },
    ],
  },
  snow: {
    label: 'Snow / Hail', category: 'atmosphere', layer: 'L1',
    defaults: {},
    params: [],
  },
  embers: {
    label: 'Embers / Sparks', category: 'atmosphere', layer: 'L1',
    defaults: { count: 60 },
    params: [
      { key: 'count', type: 'range', label: 'Count', min: 10, max: 200, step: 10, default: 60 },
    ],
  },
  lightning: {
    label: 'Lightning', category: 'atmosphere', layer: 'L1',
    defaults: { mode: 'simple', n_bolts: 2, branch_depth: 4, fork_concentration: 3, subbranch_pct: 40 },
    params: [
      { key: 'mode',               type: 'select', label: 'Mode',
        options: ['simple', 'ground_strike', 'atmospheric', 'full_storm'], default: 'simple' },
      { key: 'n_bolts',            type: 'range', label: 'Strikes',            min: 1, max: 6,  step: 1,  default: 2  },
      { key: 'branch_depth',       type: 'range', label: 'Branch depth',       min: 2, max: 6,  step: 1,  default: 4  },
      { key: 'fork_concentration', type: 'range', label: 'Fork concentration', min: 1, max: 6,  step: 1,  default: 3  },
      { key: 'subbranch_pct',      type: 'range', label: 'Sub-branch length',  min: 20, max: 70, step: 5, default: 40 },
    ],
  },

  fog: {
    label: 'Fog / Haze', category: 'atmosphere', layer: 'L1',
    defaults: { density: 0.4, height_pct: 50, tint: [180, 185, 200] },
    params: [
      { key: 'density',    type: 'range', label: 'Density',   min: 0.05, max: 1.0, step: 0.05, default: 0.4 },
      { key: 'height_pct', type: 'range', label: 'Height %',  min: 10,   max: 100, step: 5,    default: 50  },
      { key: 'tint',       type: 'color', label: 'Fog color', default: [180, 185, 200] },
    ],
  },

  // ── Aura ───────────────────────────────────────────────────────────────
  aura: {
    label: 'Aura', category: 'aura', layer: 'L2',
    defaults: { preset: 'dbz_standard', core_radius: 20, corona_radius: 65,
                pulse_speed: 3.0, pulse_depth: 0.12, electric_fringe: true },
    params: [
      { key: 'preset', type: 'select', label: 'Style preset',
        options: ['dbz_standard','dbz_blue','dbz_ultra','magic_fire','magic_ice','magic_arcane','divine','custom'],
        default: 'dbz_standard' },
      { key: 'core_color',      type: 'color',  label: 'Core color',     default: [255, 255, 200] },
      { key: 'corona_color',    type: 'color',  label: 'Corona color',   default: [255, 220,  60] },
      { key: 'core_radius',     type: 'range',  label: 'Core radius px',   min: 5,   max: 80,  step: 5,    default: 20   },
      { key: 'corona_radius',   type: 'range',  label: 'Corona radius px', min: 20,  max: 140, step: 5,    default: 65   },
      { key: 'pulse_speed',     type: 'range',  label: 'Pulse speed',      min: 0.5, max: 8.0, step: 0.5,  default: 3.0  },
      { key: 'pulse_depth',     type: 'range',  label: 'Pulse depth',      min: 0.0, max: 0.3, step: 0.02, default: 0.12 },
      { key: 'electric_fringe', type: 'toggle', label: 'Electric fringe',  default: true },
    ],
  },

  // ── Neural FX ──────────────────────────────────────────────────────────────
  anime_hayao: {
    label: 'AnimeGAN — Hayao', category: 'neural', layer: 'L6',
    needsModel: 'animegan2_hayao',
    defaults: {},
    params: [],
  },
  anime_paprika: {
    label: 'AnimeGAN — Paprika', category: 'neural', layer: 'L6',
    needsModel: 'animegan2_paprika',
    defaults: {},
    params: [],
  },
  anime_face_paint: {
    label: 'AnimeGAN — Face Paint', category: 'neural', layer: 'L6',
    needsModel: 'animegan2_face_paint',
    defaults: {},
    params: [],
  },
  anime_wbc: {
    label: 'White-Box Cartoon', category: 'neural', layer: 'L6',
    needsModel: 'white_box_cartoon',
    defaults: {},
    params: [],
  },
  chibi: {
    label: 'Chibi Portrait', category: 'neural', layer: 'L6',
    needsModel: null,
    defaults: { head_pct: 42, head_scale: 1.45 },
    params: [
      { key: 'head_pct',   type: 'range', label: 'Head split %', min: 25,  max: 60,  step: 1,    default: 42   },
      { key: 'head_scale', type: 'range', label: 'Head scale',   min: 1.1, max: 2.2, step: 0.05, default: 1.45 },
    ],
  },
  upscale: {
    label: '4× Upscale (ESRGAN)', category: 'neural', layer: 'L6',
    needsModel: 'realesrgan_x4',
    defaults: { mode: 'x4' },
    params: [
      { key: 'mode', type: 'select', label: 'Model variant',
        options: ['x4', 'x4_anime'], default: 'x4' },
    ],
  },

  // ── Stylisation ────────────────────────────────────────────────────────
  cartoon_cv2: {
    label: 'Cartoon (OpenCV)', category: 'stylize', layer: 'L6',
    defaults: { sigma_s: 60, sigma_r: 0.45 },
    params: [
      { key: 'sigma_s', type: 'range', label: 'Spatial sigma', min: 20, max: 100, step: 5,    default: 60   },
      { key: 'sigma_r', type: 'range', label: 'Range sigma',   min: 0.05, max: 0.70, step: 0.05, default: 0.45 },
    ],
  },
  watercolor: {
    label: 'Watercolor', category: 'stylize', layer: 'L6',
    defaults: { sigma_s: 60, sigma_r: 0.07 },
    params: [
      { key: 'sigma_s', type: 'range', label: 'Softness',    min: 20, max: 100, step: 5,    default: 60   },
      { key: 'sigma_r', type: 'range', label: 'Color range', min: 0.03, max: 0.20, step: 0.01, default: 0.07 },
    ],
  },
  oil_paint: {
    label: 'Oil Painting', category: 'stylize', layer: 'L6',
    defaults: {},
    params: [],
  },
  sketch: {
    label: 'Pencil Sketch', category: 'stylize', layer: 'L6',
    defaults: { shade_factor: 0.05 },
    params: [
      { key: 'shade_factor', type: 'range', label: 'Shade depth', min: 0.01, max: 0.15, step: 0.01, default: 0.05 },
    ],
  },

  // ── Optical ────────────────────────────────────────────────────────────
  god_rays: {
    label: 'God Rays', category: 'optical', layer: 'L1',
    defaults: { intensity: 0.5, origin_x: 50, origin_y: 15, color: [255, 240, 180] },
    params: [
      { key: 'intensity', type: 'range', label: 'Intensity',  min: 0.05, max: 1.0, step: 0.05, default: 0.5 },
      { key: 'origin_x',  type: 'range', label: 'Origin X %', min: 0,    max: 100, step: 5,    default: 50  },
      { key: 'origin_y',  type: 'range', label: 'Origin Y %', min: 0,    max: 50,  step: 5,    default: 15  },
      { key: 'color',     type: 'color', label: 'Ray color',  default: [255, 240, 180] },
    ],
  },
  glitch: {
    label: 'Glitch', category: 'optical', layer: 'L5',
    defaults: { intensity: 0.5, band_count: 6, channel_split: true },
    params: [
      { key: 'intensity',     type: 'range',  label: 'Intensity',     min: 0.1, max: 1.0, step: 0.05, default: 0.5  },
      { key: 'band_count',    type: 'range',  label: 'Band count',    min: 1,   max: 20,  step: 1,    default: 6    },
      { key: 'channel_split', type: 'toggle', label: 'Channel split', default: true },
    ],
  },
  chroma_aberration: {
    label: 'Chromatic Aberration', category: 'optical', layer: 'L5',
    defaults: { shift: 5 },
    params: [
      { key: 'shift', type: 'range', label: 'Shift px', min: 1, max: 20, step: 1, default: 5 },
    ],
  },
  bloom: {
    label: 'Bloom / Glow', category: 'optical', layer: 'L5',
    defaults: { radius: 12, strength: 0.40 },
    params: [
      { key: 'radius',   type: 'range', label: 'Radius px', min: 2,   max: 40,  step: 2,    default: 12   },
      { key: 'strength', type: 'range', label: 'Strength',  min: 0.1, max: 1.5, step: 0.05, default: 0.40 },
    ],
  },
  bokeh: {
    label: 'Bokeh (BG Blur)', category: 'optical', layer: 'L1',
    defaults: { radius: 18 },
    params: [
      { key: 'radius', type: 'range', label: 'Blur radius px', min: 2, max: 50, step: 2, default: 18 },
    ],
  },
  vignette: {
    label: 'Vignette', category: 'optical', layer: 'L8',
    defaults: { strength: 0.72 },
    params: [
      { key: 'strength', type: 'range', label: 'Strength', min: 0.1, max: 1.5, step: 0.05, default: 0.72 },
    ],
  },

  // ── Post-Process ───────────────────────────────────────────────────────
  sharpen: {
    label: 'Sharpen / Clarity', category: 'post', layer: 'L5',
    defaults: { mode: 'usm', amount: 1.0, radius: 2.0, threshold: 3 },
    params: [
      { key: 'mode',      type: 'select', label: 'Mode',
        options: ['usm', 'clarity', 'detail_enhance'], default: 'usm' },
      { key: 'amount',    type: 'range', label: 'Amount',    min: 0.1, max: 3.0, step: 0.1, default: 1.0 },
      { key: 'radius',    type: 'range', label: 'Radius px', min: 0.5, max: 5.0, step: 0.5, default: 2.0 },
      { key: 'threshold', type: 'range', label: 'Threshold', min: 0,   max: 20,  step: 1,   default: 3   },
    ],
  },
  denoise: {
    label: 'Denoise', category: 'post', layer: 'L5',
    defaults: { strength: 10, mode: 'nlm' },
    params: [
      { key: 'strength', type: 'range',  label: 'Strength',  min: 1, max: 30, step: 1, default: 10 },
      { key: 'mode',     type: 'select', label: 'Algorithm',
        options: ['nlm', 'bilateral', 'gaussian'], default: 'nlm' },
    ],
  },
  film_grain: {
    label: 'Film Grain', category: 'post', layer: 'L4',
    defaults: { intensity: 0.04 },
    params: [
      { key: 'intensity', type: 'range', label: 'Intensity', min: 0.01, max: 0.15, step: 0.01, default: 0.04 },
    ],
  },

  // ── Overlay ────────────────────────────────────────────────────────────
  holo_shimmer: {
    label: 'Holographic Shimmer', category: 'overlay', layer: 'L7',
    defaults: {},
    params: [],
  },
  scanlines: {
    label: 'Scan Lines (CRT)', category: 'overlay', layer: 'L9',
    defaults: { alpha: 20 },
    params: [
      { key: 'alpha', type: 'range', label: 'Opacity', min: 5, max: 80, step: 5, default: 20 },
    ],
  },

  // ── Tone & Color ───────────────────────────────────────────────────────
  tone_grade: {
    label: 'Tone & Color', category: 'tone', layer: 'L3',
    defaults: { mode: 'color' },
    params: [
      { key: 'mode', type: 'select', label: 'Mode',
        options: ['color','bw','sepia','negative','solarize','historical'], default: 'color' },
    ],
  },

  // ── Text / HUD ─────────────────────────────────────────────────────────
  tagline: {
    label: 'Gothic Text Overlay', category: 'hud', layer: 'L9',
    defaults: {},
    params: [],   // params live in the dedicated Tagline step
  },
};

// ── Library categories for the picker UI ─────────────────────────────────────
const EFFECT_CATEGORIES = [
  { id: 'atmosphere', label: 'Atmosphere',
    ids: ['smoke','flash','rain','snow','embers','lightning','fog'] },
  { id: 'aura',       label: 'Aura',
    ids: ['aura'] },
  { id: 'neural',     label: 'Neural FX',
    ids: ['anime_hayao','anime_paprika','anime_face_paint','anime_wbc','chibi','upscale'] },
  { id: 'stylize',    label: 'Stylisation',
    ids: ['cartoon_cv2','watercolor','oil_paint','sketch'] },
  { id: 'optical',    label: 'Optical',
    ids: ['god_rays','glitch','chroma_aberration','bloom','bokeh','vignette'] },
  { id: 'post',       label: 'Post-Process',
    ids: ['sharpen','denoise','film_grain'] },
  { id: 'overlay',    label: 'Overlay',
    ids: ['holo_shimmer','scanlines'] },
  { id: 'tone',       label: 'Tone & Color',
    ids: ['tone_grade'] },
  { id: 'hud',        label: 'Text / HUD',
    ids: ['tagline'] },
];

// ── Default stack (mirrors the original flat layers defaults) ─────────────────
function buildDefaultEffectStack() {
  return [
    { id: 'smoke',            enabled: true,  opacity: 1.0, params: { density: 0.7 } },
    { id: 'lightning',        enabled: true,  opacity: 1.0,
      params: { mode: 'simple', n_bolts: 2, branch_depth: 4, fork_concentration: 3, subbranch_pct: 40 } },
    { id: 'flash',            enabled: true,  opacity: 1.0, params: {} },
    { id: 'embers',           enabled: false, opacity: 1.0, params: { count: 60 } },
    { id: 'rain',             enabled: false, opacity: 1.0, params: { density: 0.6, angle: 15 } },
    { id: 'snow',             enabled: false, opacity: 1.0, params: {} },
    { id: 'anime_hayao',      enabled: false, opacity: 1.0, params: {} },
    { id: 'anime_paprika',    enabled: false, opacity: 1.0, params: {} },
    { id: 'anime_face_paint', enabled: false, opacity: 1.0, params: {} },
    { id: 'anime_wbc',        enabled: false, opacity: 1.0, params: {} },
    { id: 'chibi',            enabled: false, opacity: 1.0, params: { head_pct: 42, head_scale: 1.45 } },
    { id: 'upscale',          enabled: false, opacity: 1.0, params: { mode: 'x4' } },
    { id: 'fog',              enabled: false, opacity: 1.0, params: { density: 0.4, height_pct: 50, tint: [180, 185, 200] } },
    { id: 'god_rays',         enabled: false, opacity: 1.0, params: { intensity: 0.5, origin_x: 50, origin_y: 15, color: [255, 240, 180] } },
    { id: 'glitch',           enabled: false, opacity: 1.0, params: { intensity: 0.5, band_count: 6, channel_split: true } },
    { id: 'vignette',         enabled: true,  opacity: 1.0, params: { strength: 0.72 } },
    { id: 'tone_grade',       enabled: true,  opacity: 1.0, params: { mode: 'color' } },
    { id: 'chroma_aberration',enabled: false, opacity: 1.0, params: { shift: 5 } },
    { id: 'bloom',            enabled: false, opacity: 1.0, params: { radius: 12, strength: 0.40 } },
    { id: 'film_grain',       enabled: false, opacity: 1.0, params: { intensity: 0.04 } },
    { id: 'holo_shimmer',     enabled: false, opacity: 1.0, params: {} },
    { id: 'bokeh',            enabled: false, opacity: 1.0, params: { radius: 18 } },
    { id: 'scanlines',        enabled: false, opacity: 1.0, params: { alpha: 20 } },
    { id: 'tagline',          enabled: true,  opacity: 1.0, params: {} },
  ];
}

// ── Migrate legacy flat layers object into effectStack ─────────────────────────
const LEGACY_KEY_MAP = {
  smoke: 'add_smoke', flash: 'add_flash', rain: 'add_rain', snow: 'add_snow',
  embers: 'add_embers', vignette: 'add_vignette', scanlines: 'add_scanlines',
  chroma_aberration: 'add_chroma_aberration', bloom: 'add_bloom',
  film_grain: 'add_film_grain', holo_shimmer: 'add_holo', bokeh: 'add_bokeh',
  tagline: 'add_text',
};

function migrateToEffectStack(stack, legacyLayers) {
  for (const item of stack) {
    const lk = LEGACY_KEY_MAP[item.id];
    if (lk && legacyLayers[lk] !== undefined) {
      item.enabled = !!legacyLayers[lk];
    }
    if (item.id === 'lightning') {
      item.enabled = legacyLayers.lightning_mode !== 'off';
      item.params.mode             = legacyLayers.lightning_mode  || 'simple';
      item.params.n_bolts          = legacyLayers.n_bolts          ?? 2;
      item.params.branch_depth     = legacyLayers.branch_depth     ?? 4;
      item.params.fork_concentration = legacyLayers.fork_concentration ?? 3;
      item.params.subbranch_pct    = (legacyLayers.subbranch_pct ?? 40);
    }
    if (item.id === 'tone_grade') {
      item.params.mode = legacyLayers.tone_mode || 'color';
    }
  }
}

// ── Per-effect param UI builder ───────────────────────────────────────────────
function buildParamUI(effectDef, layerItem) {
  const frag = document.createDocumentFragment();

  for (const p of effectDef.params) {
    const val = layerItem.params[p.key] ?? p.default;
    const row = document.createElement('div');
    row.className = 'fx-param-row';

    if (p.type === 'range') {
      const displayVal = typeof val === 'number' && !Number.isInteger(val)
        ? val.toFixed(String(p.step).split('.')[1]?.length ?? 2)
        : val;
      row.innerHTML = `
        <span class="field-label">${p.label}</span>
        <input type="range" min="${p.min}" max="${p.max}" step="${p.step}" value="${val}">
        <span class="range-val">${displayVal}</span>`;
      const inp = row.querySelector('input');
      const display = row.querySelector('.range-val');
      inp.addEventListener('input', () => {
        const v = parseFloat(inp.value);
        layerItem.params[p.key] = v;
        const dec = String(p.step).split('.')[1]?.length ?? 0;
        display.textContent = dec ? v.toFixed(dec) : v;
      });

    } else if (p.type === 'select') {
      const opts = p.options.map(o =>
        `<option value="${o}"${o === val ? ' selected' : ''}>${o.replace(/_/g, ' ')}</option>`
      ).join('');
      row.innerHTML = `<span class="field-label">${p.label}</span><select>${opts}</select>`;
      row.querySelector('select').addEventListener('change', e => {
        layerItem.params[p.key] = e.target.value;
      });

    } else if (p.type === 'toggle') {
      const on = val !== undefined ? val : p.default;
      row.innerHTML = `
        <div class="tog-track${on ? ' on' : ''}"><div class="tog-thumb"></div></div>
        <span class="tog-label">${p.label}</span>`;
      row.querySelector('.tog-track').addEventListener('click', function () {
        layerItem.params[p.key] = !layerItem.params[p.key];
        this.classList.toggle('on', layerItem.params[p.key]);
      });

    } else if (p.type === 'color') {
      const rgb = val || p.default || [128, 128, 128];
      const hex = '#' + rgb.map(c => c.toString(16).padStart(2, '0')).join('');
      row.innerHTML = `
        <span class="field-label">${p.label}</span>
        <input type="color" value="${hex}">`;
      row.querySelector('input').addEventListener('input', e => {
        const h = e.target.value.slice(1);
        layerItem.params[p.key] = [
          parseInt(h.slice(0, 2), 16),
          parseInt(h.slice(2, 4), 16),
          parseInt(h.slice(4, 6), 16),
        ];
      });

    } else if (p.type === 'file') {
      row.innerHTML = `
        <span class="field-label">${p.label}</span>
        <button class="btn-browse">Browse…</button>
        <span class="fx-file-name muted">${val ? val.split(/[\\/]/).pop() : '(none)'}</span>`;
      row.querySelector('.btn-browse').addEventListener('click', async () => {
        const path = await Api.browseFile({ title: p.label, extensions: ['png', 'jpg', 'webp'] });
        if (path) {
          layerItem.params[p.key] = path;
          row.querySelector('.fx-file-name').textContent = path.split(/[\\/]/).pop();
        }
      });
    }

    frag.appendChild(row);
  }
  return frag;
}
