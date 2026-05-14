/**
 * Thin promise wrapper around window.pywebview.api.
 * Never call window.pywebview.api directly from views.
 */
const Api = (() => {
  const _call = (method, ...args) =>
    new Promise((resolve, reject) => {
      const invoke = () => {
        if (!window.pywebview || !window.pywebview.api) {
          reject(new Error('pywebview API not ready'));
          return;
        }
        window.pywebview.api[method](...args).then(resolve).catch(reject);
      };
      if (window.pywebview && window.pywebview.api) {
        invoke();
      } else {
        window.addEventListener('pywebviewready', invoke, { once: true });
      }
    });

  return {
    pickImage:       ()        => _call('pick_image'),
    pickOutputDir:   ()        => _call('pick_output_dir'),
    getImagePreview: (path)    => _call('get_image_preview', path),
    startRender:     (payload) => _call('run_generation', payload),
    getProgress:     ()        => _call('get_progress'),
  };
})();
