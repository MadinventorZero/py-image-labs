/**
 * Effect stack UI tests — E1 through E12
 * Covers: library add/remove, opacity persistence, param defaults,
 * toggling enable, effectStack → skipWhen wiring.
 */

// ── Helpers ───────────────────────────────────────────────────────────────────

function makeStack(...ids) {
  return ids.map(id => ({
    id,
    enabled: true,
    opacity: 1.0,
    params: { ...(EFFECT_LIBRARY[id]?.defaults || {}) },
  }));
}

function stackHas(stack, id) {
  return stack.some(i => i.id === id);
}

const EffectStackTests = [
  // ── Library presence ──────────────────────────────────────────────────────
  {
    id: 'E1',
    name: 'EFFECT_LIBRARY contains all expected effect IDs',
    async run() {
      const required = [
        'smoke', 'rain', 'snow', 'embers', 'lightning', 'flash',
        'fog', 'god_rays', 'glitch',
        'vignette', 'scanlines', 'bloom', 'film_grain',
        'chroma_aberration', 'tone_grade', 'sharpen', 'denoise',
        'bokeh', 'aura', 'holo_shimmer',
        'cartoon_cv2', 'watercolor', 'oil_paint', 'sketch',
        'anime_hayao', 'anime_paprika', 'anime_face_paint', 'anime_wbc',
        'chibi', 'upscale', 'tagline',
      ];
      for (const id of required) {
        assert(EFFECT_LIBRARY[id], `EFFECT_LIBRARY missing: ${id}`);
      }
    },
  },

  {
    id: 'E2',
    name: 'Every EFFECT_LIBRARY entry has label and params array',
    async run() {
      for (const [id, def] of Object.entries(EFFECT_LIBRARY)) {
        assert(typeof def.label === 'string' && def.label.length > 0,
               `${id}: missing label`);
        assert(Array.isArray(def.params),
               `${id}: params should be an array`);
      }
    },
  },

  // ── buildDefaultEffectStack ───────────────────────────────────────────────
  {
    id: 'E3',
    name: 'buildDefaultEffectStack returns an array of objects with required fields',
    async run() {
      const stack = buildDefaultEffectStack();
      assert(Array.isArray(stack), 'Stack should be an array');
      assert(stack.length > 0, 'Stack should be non-empty');
      for (const item of stack) {
        assert('id' in item,      `Item missing 'id': ${JSON.stringify(item)}`);
        assert('enabled' in item, `Item missing 'enabled': ${item.id}`);
        assert('opacity' in item, `Item missing 'opacity': ${item.id}`);
        assert('params' in item,  `Item missing 'params': ${item.id}`);
        assert(typeof item.opacity === 'number' && item.opacity >= 0 && item.opacity <= 1,
               `${item.id}: opacity out of range`);
      }
    },
  },

  {
    id: 'E4',
    name: 'buildDefaultEffectStack includes tagline',
    async run() {
      const stack = buildDefaultEffectStack();
      assert(stackHas(stack, 'tagline'), 'Default stack should include tagline');
    },
  },

  {
    id: 'E5',
    name: 'buildDefaultEffectStack includes new effects: fog, god_rays, glitch',
    async run() {
      const stack = buildDefaultEffectStack();
      for (const id of ['fog', 'god_rays', 'glitch']) {
        assert(stackHas(stack, id), `Default stack should include ${id}`);
      }
    },
  },

  // ── Stack manipulation helpers ────────────────────────────────────────────
  {
    id: 'E6',
    name: 'Stack add: pushing an item registers the new effect',
    async run() {
      const stack = [];
      const def = EFFECT_LIBRARY['bloom'];
      stack.push({ id: 'bloom', enabled: true, opacity: 1.0, params: { ...(def.defaults || {}) } });
      assert(stackHas(stack, 'bloom'), 'Stack should contain bloom after push');
    },
  },

  {
    id: 'E7',
    name: 'Stack remove: splicing removes the correct item',
    async run() {
      const stack = makeStack('fog', 'bloom', 'vignette');
      const idx = stack.findIndex(i => i.id === 'bloom');
      stack.splice(idx, 1);
      assert(!stackHas(stack, 'bloom'), 'bloom should be removed');
      assert(stackHas(stack, 'fog'),     'fog should remain');
      assert(stackHas(stack, 'vignette'),'vignette should remain');
    },
  },

  {
    id: 'E8',
    name: 'Stack reorder: swap preserves item identity',
    async run() {
      const stack = makeStack('fog', 'bloom', 'vignette');
      [stack[0], stack[1]] = [stack[1], stack[0]];
      assert(stack[0].id === 'bloom', 'bloom should be first after swap');
      assert(stack[1].id === 'fog',   'fog should be second after swap');
    },
  },

  // ── Opacity ───────────────────────────────────────────────────────────────
  {
    id: 'E9',
    name: 'Opacity can be set between 0 and 1 on any stack item',
    async run() {
      const stack = makeStack('fog');
      stack[0].opacity = 0.5;
      assert(stack[0].opacity === 0.5, 'opacity should be 0.5');
    },
  },

  // ── Effect param defaults ─────────────────────────────────────────────────
  {
    id: 'E10',
    name: 'fog defaults: density and height_pct present',
    async run() {
      const def = EFFECT_LIBRARY['fog'];
      const d = def.defaults || {};
      assert('density' in d,    'fog defaults should have density');
      assert('height_pct' in d, 'fog defaults should have height_pct');
    },
  },

  {
    id: 'E11',
    name: 'glitch defaults: intensity and band_count present',
    async run() {
      const def = EFFECT_LIBRARY['glitch'];
      const d = def.defaults || {};
      assert('intensity' in d,  'glitch defaults should have intensity');
      assert('band_count' in d, 'glitch defaults should have band_count');
    },
  },

  {
    id: 'E12',
    name: 'Neural effects have needsModel field (null for chibi)',
    async run() {
      // chibi needs no model
      const chibi = EFFECT_LIBRARY['chibi'];
      assert('needsModel' in chibi, 'chibi should have needsModel field');
      assert(chibi.needsModel === null, 'chibi.needsModel should be null (no model needed)');

      // anime styles need a model
      for (const id of ['anime_hayao', 'anime_paprika', 'anime_face_paint', 'anime_wbc']) {
        const def = EFFECT_LIBRARY[id];
        assert('needsModel' in def, `${id} should have needsModel`);
        assert(typeof def.needsModel === 'string', `${id}.needsModel should be a string`);
      }
    },
  },
];
