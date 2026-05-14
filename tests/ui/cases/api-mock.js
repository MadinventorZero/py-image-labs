/**
 * Stub for all Api methods — used by smoke.html test harness.
 * Overrides the real Api object so tests run without pywebview.
 */
const ApiMock = {
  pickImage:       () => Promise.resolve('/tmp/test-photo.jpg'),
  pickOutputDir:   () => Promise.resolve('/tmp/output'),
  getImagePreview: () => Promise.resolve(''),
  startRender:     () => Promise.resolve({ status: 'started' }),
  getProgress:     () => Promise.resolve({ progress: 0, done: false, error: null, gif_b64: null }),
};

// Inject mock — replaces the real Api built by api.js
Object.assign(Api, ApiMock);
