/**
 * Render flow tests — R1 through R5
 */
const RenderFlowTests = [
  {
    id: 'R1',
    name: 'wizardsave fires on last step (07-confirm)',
    async run() {
      await Wizard.enterWizard(2, 0);  // 07-confirm
      Wizard.setBlocked(false);
      let fired = false;
      document.getElementById('wizard-content').addEventListener('wizardsave', () => {
        fired = true;
      }, { once: true });
      document.getElementById('btn-next').click();
      await tick(100);
      assert(fired, 'wizardsave event should fire on confirm step');
    },
  },
  {
    id: 'R2',
    name: 'render.html polls getProgress',
    async run() {
      let calls = 0;
      const orig = Api.getProgress;
      Api.getProgress = () => { calls++; return Promise.resolve({ progress: 0, done: true, error: null, gif_b64: null }); };
      await Wizard.showRender();
      await tick(200);
      Api.getProgress = orig;
      assert(calls >= 1, 'getProgress should be called at least once');
    },
  },
  {
    id: 'R3',
    name: 'GIF preview appears when gif_b64 populated',
    async run() {
      Api.getProgress = () => Promise.resolve({
        progress: 100, done: true, error: null, gif_b64: 'abc123',
      });
      await Wizard.showRender();
      await tick(200);
      const gifWrap = document.getElementById('gif-preview');
      assert(!gifWrap.hidden, 'gif-preview should be visible when gif_b64 is set');
    },
  },
  {
    id: 'R4',
    name: 'Error shown when getProgress returns error',
    async run() {
      Api.getProgress = () => Promise.resolve({
        progress: 0, done: true, error: 'Something went wrong', gif_b64: null,
      });
      await Wizard.showRender();
      await tick(200);
      const errorBox = document.getElementById('error-box');
      assert(!errorBox.hidden, 'error-box should be visible on error');
      assert(errorBox.textContent.includes('Something went wrong'), 'Error message should be shown');
    },
  },
  {
    id: 'R5',
    name: 'New Render returns to landing',
    async run() {
      await Wizard.showRender();
      await tick(50);
      // Simulate "done" so the buttons appear
      document.getElementById('post-render-btns').hidden = false;
      document.getElementById('btn-new-render').click();
      await tick(100);
      const content = document.getElementById('wizard-content').innerHTML;
      assert(content.includes('step-landing'), 'Should return to landing after New Render');
    },
  },
];

function tick(ms = 50) { return new Promise(r => setTimeout(r, ms)); }
