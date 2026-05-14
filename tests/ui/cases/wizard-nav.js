/**
 * Navigation tests — N1 through N6
 */
const WizardNavTests = [
  {
    id: 'N1',
    name: 'Back hidden on landing',
    async run() {
      await Wizard.showLanding();
      const back = document.getElementById('btn-back');
      assert(back.hidden, 'Back button should be hidden on landing');
    },
  },
  {
    id: 'N2',
    name: 'Next advances step index from 0 to 1',
    async run() {
      await Wizard.enterWizard(0, 0);
      // Unblock (step 1 needs an inputPath)
      Wizard.state.config.inputPath = '/tmp/test.jpg';
      Wizard.setBlocked(false);
      const before = Wizard.flatIndex();
      document.getElementById('btn-next').click();
      await tick();
      assert(Wizard.flatIndex() === before + 1, 'flatIndex should advance by 1');
    },
  },
  {
    id: 'N3',
    name: 'Next blocked when inputPath is empty',
    async run() {
      Wizard.state.config.inputPath = '';
      await Wizard.enterWizard(0, 0);
      assert(document.getElementById('btn-next').disabled, 'Next should be disabled when inputPath empty');
    },
  },
  {
    id: 'N4',
    name: 'Next blocked when outputDir is empty',
    async run() {
      Wizard.state.config.outputDir = '';
      await Wizard.enterWizard(0, 2);  // step 03-output
      assert(document.getElementById('btn-next').disabled, 'Next should be disabled when outputDir empty');
    },
  },
  {
    id: 'N5',
    name: 'Step 6 skipped when add_text is false',
    async run() {
      Wizard.state.config.layers.add_text = false;
      await Wizard.enterWizard(1, 0);  // step 05-layers
      Wizard.setBlocked(false);
      document.getElementById('btn-next').click();
      await tick();
      // Should jump to phase 2 (render/confirm), not step 06-tagline
      const step = Wizard.PHASES[Wizard.state ? 2 : 0]?.steps[0];
      assert(step?.id === '07-confirm', 'Should skip tagline and land on 07-confirm');
    },
  },
  {
    id: 'N6',
    name: 'Step 6 shown when add_text is true',
    async run() {
      Wizard.state.config.layers.add_text = true;
      await Wizard.enterWizard(1, 0);  // step 05-layers
      Wizard.setBlocked(false);
      document.getElementById('btn-next').click();
      await tick();
      const content = document.getElementById('wizard-content').innerHTML;
      assert(content.includes('step-tagline'), 'Should navigate to tagline step');
    },
  },
];

function tick(ms = 50) { return new Promise(r => setTimeout(r, ms)); }
