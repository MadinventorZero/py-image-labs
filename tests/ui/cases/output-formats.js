/**
 * Output format and wizard config tests — F1 through F8
 * Covers: default output flags, format payload assembly,
 * effectStack → tagline skip wiring.
 */

const OutputFormatTests = [
  // ── Default state ─────────────────────────────────────────────────────────
  {
    id: 'F1',
    name: 'Default output has gif:true and webp/mp4/apng:false',
    async run() {
      // Reset to a fresh wizard state
      const cfg = Wizard.state.config;
      assert(cfg.output.gif  === true,  'gif should default to true');
      assert(cfg.output.webp === false, 'webp should default to false');
      assert(cfg.output.mp4  === false, 'mp4 should default to false');
      assert(cfg.output.apng === false, 'apng should default to false');
    },
  },

  {
    id: 'F2',
    name: 'effectStack is an array on fresh state',
    async run() {
      const cfg = Wizard.state.config;
      assert(Array.isArray(cfg.effectStack), 'effectStack should be an array');
      assert(cfg.effectStack.length > 0, 'effectStack should be non-empty from buildDefaultEffectStack');
    },
  },

  {
    id: 'F3',
    name: 'Output format flags can be toggled',
    async run() {
      const cfg = Wizard.state.config;
      const prev = cfg.output.webp;
      cfg.output.webp = !prev;
      assert(cfg.output.webp !== prev, 'webp flag should toggle');
      cfg.output.webp = prev; // restore
    },
  },

  // ── effectStack → skipWhen integration ───────────────────────────────────
  {
    id: 'F4',
    name: 'Tagline step is skipped when tagline is disabled in effectStack',
    async run() {
      const stack = Wizard.state.config.effectStack;
      const tagEntry = stack.find(l => l.id === 'tagline');
      assert(tagEntry, 'effectStack should include a tagline entry');

      tagEntry.enabled = false;
      const taglineStep = Wizard.PHASES
        ? Wizard.PHASES[1]?.steps.find(s => s.id === '06-tagline')
        : null;

      if (taglineStep?.skipWhen) {
        assert(taglineStep.skipWhen() === true, 'skipWhen should return true when tagline disabled');
      } else {
        // skipWhen is inside the wizard closure; test via navigation instead
        await Wizard.enterWizard(1, 0);
        Wizard.setBlocked(false);
        document.getElementById('btn-next').click();
        await tick();
        const content = document.getElementById('wizard-content').innerHTML;
        assert(!content.includes('step-tagline'), 'Should skip tagline when disabled in effectStack');
      }

      tagEntry.enabled = true; // restore
    },
  },

  {
    id: 'F5',
    name: 'Tagline step is shown when tagline is enabled in effectStack',
    async run() {
      const stack = Wizard.state.config.effectStack;
      const tagEntry = stack.find(l => l.id === 'tagline');
      assert(tagEntry, 'effectStack should include a tagline entry');

      tagEntry.enabled = true;
      await Wizard.enterWizard(1, 0);
      Wizard.setBlocked(false);
      document.getElementById('btn-next').click();
      await tick();
      const content = document.getElementById('wizard-content').innerHTML;
      assert(content.includes('step-tagline'), 'Should show tagline when enabled in effectStack');
    },
  },

  // ── Sizes ─────────────────────────────────────────────────────────────────
  {
    id: 'F6',
    name: 'All three size flags are true by default',
    async run() {
      const sizes = Wizard.state.config.sizes;
      assert(sizes.youtube_thumbnail === true, 'youtube_thumbnail should be enabled');
      assert(sizes.channel_art       === true, 'channel_art should be enabled');
      assert(sizes.podcast_square    === true, 'podcast_square should be enabled');
    },
  },

  // ── imgProc defaults ──────────────────────────────────────────────────────
  {
    id: 'F7',
    name: 'imgProc defaults are correct',
    async run() {
      const ip = Wizard.state.config.imgProc;
      assert(ip.remove_bg       === true,  'remove_bg should default true');
      assert(ip.crop_to_subject === true,  'crop_to_subject should default true');
      assert(ip.crop_padding    === 0.12,  'crop_padding should be 0.12');
      assert(ip.rotate_degrees  === 0,     'rotate_degrees should be 0');
      assert(ip.resize_pct      === 100,   'resize_pct should be 100');
    },
  },

  // ── effectStack item structure ────────────────────────────────────────────
  {
    id: 'F8',
    name: 'All effectStack items have id, enabled, opacity, params',
    async run() {
      const stack = Wizard.state.config.effectStack;
      for (const item of stack) {
        assert(typeof item.id      === 'string',  `Stack item missing id`);
        assert(typeof item.enabled === 'boolean', `${item.id}: enabled should be boolean`);
        assert(typeof item.opacity === 'number',  `${item.id}: opacity should be number`);
        assert(typeof item.params  === 'object',  `${item.id}: params should be object`);
      }
    },
  },
];
