/**
 * Wizard-of-wizards controller for Brand Image Generator.
 * Adapted from Mad-Financial-Planning proto-app standard.
 * Differences: no portfolioId, skipWhen step support, state._blocked nav gate,
 * showRender/newRender flow replaces mark-complete/landing finish.
 */
const Wizard = (() => {
  const PHASES = [
    {
      id: 'setup', label: 'Setup',
      steps: [
        { id: '01-input',   label: 'Input',  view: 'views/01-input.html' },
        { id: '02-process', label: 'Image',  view: 'views/02-process.html' },
        { id: '03-output',  label: 'Output', view: 'views/03-output.html' },
        { id: '04-sizes',   label: 'Sizes',  view: 'views/04-sizes.html' },
      ],
    },
    {
      id: 'effects', label: 'Effects',
      steps: [
        { id: '05-layers',  label: 'Layers',  view: 'views/05-layers.html' },
        { id: '06-tagline', label: 'Tagline', view: 'views/06-tagline.html',
          skipWhen: () => {
            const stack = state.config.effectStack || [];
            const tag = stack.find(l => l.id === 'tagline');
            return tag ? !tag.enabled : true;
          } },
      ],
    },
    {
      id: 'render', label: 'Render',
      steps: [
        { id: '07-confirm', label: 'Confirm', view: 'views/07-confirm.html' },
      ],
    },
  ];

  const defaultState = () => ({
    config: {
      inputPath:  '',
      outputDir:  '',
      imgProc: {
        remove_bg:       true,
        crop_to_subject: true,
        crop_padding:    0.12,
        rotate_degrees:  0,
        resize_pct:      100,
      },
      sizes: {
        youtube_thumbnail: true,
        channel_art:       true,
        podcast_square:    true,
      },
      output_static: false,
      output: { gif: true, webp: false, mp4: false, apng: false, png_peak: true },
      // effectStack is the v5 layer system; layers is kept for legacy compat
      effectStack: buildDefaultEffectStack(),
      layers: {},
      tagline: {
        text:          'Brand Name',
        anchor:        'center',
        offset_y:      0,
        font_size_pct: 8,
        align:         'center',
        orientation:   'horizontal',
        color_hex:     '#DCBE78',
        shadow:        true,
        glow:          true,
      },
    },
    previewSrc:  null,
    gpuInfo:     null,
    _blocked:    false,
  });

  const state = defaultState();

  let currentPhase = 0;
  let currentStep  = 0;
  let saving       = false;
  let inWizard     = false;

  const $content  = () => document.getElementById('wizard-content');
  const $nav      = () => document.getElementById('wizard-nav');
  const $controls = () => document.getElementById('wizard-controls');
  const $btnBack  = () => document.getElementById('btn-back');
  const $btnNext  = () => document.getElementById('btn-next');

  const flatTotal = () => PHASES.reduce((n, p) => n + p.steps.length, 0);
  const flatIndex = () => {
    let idx = 0;
    for (let p = 0; p < currentPhase; p++) idx += PHASES[p].steps.length;
    return idx + currentStep;
  };

  const shouldSkip = (pi, si) => {
    const step = PHASES[pi]?.steps[si];
    return step?.skipWhen ? step.skipWhen() : false;
  };

  const loadView = async (step) => {
    window.onViewLoad = null;
    const html   = await fetch(step.view).then(r => r.text());
    const parser = new DOMParser();
    const doc    = parser.parseFromString(html, 'text/html');

    const scripts = [...doc.querySelectorAll('script')];
    const styles  = [...doc.querySelectorAll('style')];
    scripts.forEach(s => s.remove());
    styles.forEach(s => s.remove());

    $content().innerHTML = doc.body.innerHTML;

    styles.forEach(orig => {
      const s = document.createElement('style');
      s.textContent = orig.textContent;
      $content().prepend(s);
    });

    scripts.forEach(orig => {
      const s = document.createElement('script');
      s.textContent = orig.textContent;
      document.head.appendChild(s);
      document.head.removeChild(s);
    });

    if (typeof window.onViewLoad === 'function') {
      window.onViewLoad({ step, state });
    }
  };

  const renderNav = () => {
    $nav().innerHTML = PHASES.map((phase, pi) => {
      const phaseClass = pi === currentPhase ? 'active' : pi < currentPhase ? 'done' : '';
      const stepsHtml  = phase.steps.map((step, si) => {
        const stepClass = (pi === currentPhase && si === currentStep) ? 'active'
                        : (pi < currentPhase || (pi === currentPhase && si < currentStep)) ? 'done'
                        : '';
        return `<span class="nav-step ${stepClass}" title="${step.label}"></span>`;
      }).join('');
      return `
        <div class="nav-phase ${phaseClass}">
          <div class="nav-phase-label">${phase.label}</div>
          <div class="nav-steps">${stepsHtml}</div>
        </div>`;
    }).join('');
  };

  const updateControls = () => {
    $btnBack().hidden      = !inWizard || flatIndex() === 0;
    $btnNext().textContent = flatIndex() === flatTotal() - 1 ? 'Run' : 'Next';
    $btnNext().disabled    = saving || state._blocked;
  };

  const setBlocked = (v) => {
    state._blocked = !!v;
    if (inWizard) updateControls();
  };

  const goTo = async (phaseIdx, stepIdx) => {
    currentPhase = phaseIdx;
    currentStep  = stepIdx;
    state._blocked = false;
    try {
      await loadView(PHASES[phaseIdx].steps[stepIdx]);
    } catch {
      $content().innerHTML = '<div class="error-box">Could not load this step. Please try again.</div>';
    }
    renderNav();
    updateControls();
  };

  // ── Landing ───────────────────────────────────────────────────────────────
  const showLanding = async () => {
    inWizard = false;
    $nav().hidden      = true;
    $controls().hidden = true;
    state._blocked = false;
    await loadView({ id: 'landing', label: 'Home', view: 'views/landing.html' });
  };

  // ── Render view (outside phases) ─────────────────────────────────────────
  const showRender = async () => {
    inWizard = false;
    $nav().hidden      = true;
    $controls().hidden = true;
    state._blocked = false;
    await loadView({ id: 'render', label: 'Render', view: 'views/render.html' });
  };

  const newRender = async () => {
    state.previewSrc = null;
    await showLanding();
  };

  // ── Enter wizard from landing ─────────────────────────────────────────────
  const enterWizard = async (phaseIdx = 0, stepIdx = 0) => {
    inWizard = true;
    $nav().hidden      = false;
    $controls().hidden = false;
    await goTo(phaseIdx, stepIdx);
  };

  // ── Landing action ────────────────────────────────────────────────────────
  const startNewRender = async () => {
    Object.assign(state, defaultState());
    await enterWizard(0, 0);
  };

  // ── Navigation ────────────────────────────────────────────────────────────
  const next = async () => {
    if (saving || state._blocked) return;
    saving = true;
    $btnNext().disabled = true;

    const saveEvent = new CustomEvent('wizardsave', { detail: { state }, cancelable: true });
    const proceed   = $content().dispatchEvent(saveEvent);

    if (!proceed) {
      saving = false;
      updateControls();
      return;
    }

    if (saveEvent.detail.asyncDone) {
      await saveEvent.detail.asyncDone.catch(() => null);
    }

    const fi = flatIndex();
    if (fi >= flatTotal() - 1) {
      saving = false;
      await showRender();
      return;
    }

    // Advance, skipping any skipWhen steps
    let nextPhase = currentPhase;
    let nextStep  = currentStep + 1;

    if (nextStep >= PHASES[nextPhase].steps.length) {
      nextPhase++;
      nextStep = 0;
    }

    while (
      nextPhase < PHASES.length &&
      nextStep  < PHASES[nextPhase].steps.length &&
      shouldSkip(nextPhase, nextStep)
    ) {
      nextStep++;
      if (nextStep >= PHASES[nextPhase].steps.length) {
        nextPhase++;
        nextStep = 0;
      }
    }

    saving = false;
    await goTo(nextPhase, nextStep);
  };

  const back = async () => {
    if (currentPhase === 0 && currentStep === 0) {
      await showLanding();
      return;
    }

    let prevPhase = currentPhase;
    let prevStep  = currentStep - 1;

    if (prevStep < 0) {
      prevPhase--;
      prevStep = PHASES[prevPhase].steps.length - 1;
    }

    while (prevPhase >= 0 && shouldSkip(prevPhase, prevStep)) {
      prevStep--;
      if (prevStep < 0) {
        prevPhase--;
        if (prevPhase < 0) { await showLanding(); return; }
        prevStep = PHASES[prevPhase].steps.length - 1;
      }
    }

    await goTo(prevPhase, prevStep);
  };

  const init = async () => {
    $btnNext().addEventListener('click', next);
    $btnBack().addEventListener('click', back);
    await showLanding();
  };

  return {
    init,
    goTo,
    enterWizard,
    showLanding,
    showRender,
    newRender,
    startNewRender,
    setBlocked,
    state,
    PHASES,
    flatIndex,
  };
})();

document.addEventListener('DOMContentLoaded', () => Wizard.init());
