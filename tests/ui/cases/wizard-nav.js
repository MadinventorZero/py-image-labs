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
    name: 'Step 6 skipped when tagline is disabled in effectStack',
    async run() {
      // Use the effectStack tagline entry — the skipWhen reads from here, not layers.add_text
      const stack = Wizard.state.config.effectStack;
      const tagEntry = stack.find(l => l.id === 'tagline');
      if (tagEntry) tagEntry.enabled = false;
      await Wizard.enterWizard(1, 0);  // step 05-layers
      Wizard.setBlocked(false);
      document.getElementById('btn-next').click();
      await tick();
      const content = document.getElementById('wizard-content').innerHTML;
      assert(!content.includes('step-tagline'), 'Should skip tagline when disabled in effectStack');
    },
  },
  {
    id: 'N6',
    name: 'Step 6 shown when tagline is enabled in effectStack',
    async run() {
      // Ensure tagline is enabled via effectStack
      const stack = Wizard.state.config.effectStack;
      const tagEntry = stack.find(l => l.id === 'tagline');
      if (tagEntry) tagEntry.enabled = true;
      await Wizard.enterWizard(1, 0);  // step 05-layers
      Wizard.setBlocked(false);
      document.getElementById('btn-next').click();
      await tick();
      const content = document.getElementById('wizard-content').innerHTML;
      assert(content.includes('step-tagline'), 'Should navigate to tagline when enabled in effectStack');
    },
  },
];

function tick(ms = 50) { return new Promise(r => setTimeout(r, ms)); }
