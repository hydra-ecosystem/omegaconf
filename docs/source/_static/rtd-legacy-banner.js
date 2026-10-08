// Configure RTD's Custom Script addon to load this shared asset from:
// https://omegaconf.readthedocs.io/en/latest/_static/rtd-legacy-banner.js
(() => {
  function showBanner() {
    if (document.querySelector('.docs-moved-banner')) return;

    const style = document.createElement('style');
    style.textContent = `
      .docs-moved-banner {
        background: #fff3cd;
        border-bottom: 4px solid #b45309;
        color: #422006;
        font-family: system-ui, sans-serif;
        font-size: 1rem;
        line-height: 1.5;
        padding: 1rem 1.5rem;
        text-align: center;
      }
      .docs-moved-banner strong {
        display: block;
        font-size: 1.25rem;
        margin-bottom: 0.25rem;
      }
      .docs-moved-banner a {
        color: #78350f;
        font-weight: 700;
        text-decoration: underline;
      }
    `;
    document.head.append(style);

    const banner = document.createElement('aside');
    banner.className = 'docs-moved-banner';
    banner.setAttribute('role', 'note');
    banner.setAttribute('aria-label', 'Documentation has moved');
    banner.innerHTML = `
      <strong>Documentation has moved</strong>
      <a href="https://omegaconf.cli.dev/">Read the OmegaConf documentation at omegaconf.cli.dev</a>.
      These pages are retained as legacy documentation.
    `;
    document.body.prepend(banner);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', showBanner, {once: true});
  } else {
    showBanner();
  }
})();
