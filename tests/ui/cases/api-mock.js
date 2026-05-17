/**
 * Stub for all Api methods — used by smoke.html test harness.
 * Overrides the real Api object so tests run without pywebview.
 */
const ApiMock = {
  pickImage:       () => Promise.resolve('/tmp/test-photo.jpg'),
  pickOutputDir:   () => Promise.resolve('/tmp/output'),
  browseFile:      () => Promise.resolve('/tmp/test-file.png'),
  getImagePreview: () => Promise.resolve(''),
  startRender:     () => Promise.resolve({ status: 'started' }),
  getProgress:     () => Promise.resolve({ progress: 0, done: false, error: null, gif_b64: null }),
  // Returns a minimal device info — no GPU in test environment
  getDeviceInfo:   () => Promise.resolve({ backend: 'cpu', name: 'CPU (test)' }),
  // Returns a tiny blank JPEG data URI so preview tests don't stall
  previewStack:    () => Promise.resolve(
    'data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8U'
    + 'HRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIy'
    + 'MjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAABAAEDASIAAhEBAxEB/8QAFgABAQEA'
    + 'AAAAAAAAAAAAAAAABgUEB/8QAHRAAAQQDAQEAAAAAAAAAAAAAAQACAxEEITFB/8QAFAEBAAAAAAAAAAAAAAAAAAAAAP/'
    + 'EABQRAQAAAAAAAAAAAAAAAAAAAAD/2gAMAwEAAhEDEQA/AKgARgBjAH//2Q=='
  ),
};

// Inject mock — replaces the real Api built by api.js
Object.assign(Api, ApiMock);
