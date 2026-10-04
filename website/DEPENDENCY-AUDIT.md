# Annual npm dependency audit

Run: 2026-10-04T17:58:28.214164+00:00

This is a best-effort upgrade drive. Remaining vulnerabilities are accepted between annual reviews; this report does not certify that the project is free of vulnerabilities. Review compatibility and validation before merging.

## Proposed direct dependency upgrades

- react: `19.2.0` → `19.3.0`
- react-dom: `19.2.0` → `19.3.0`

## Audit results

npm counts affected package entries, including propagated findings in parent packages. These are not counts of distinct advisories or demonstrated exploit paths. Fix candidates can require manual migrations.

Before: info: 0, low: 0, moderate: 0, high: 29, critical: 0, total: 29

- @docusaurus/babel: high; affected range `<=4.0.0-canary-6835`; npm fix candidate not available.
- @docusaurus/bundler: high; affected range `<=4.0.0-canary-6835`; npm fix candidate not available.
- @docusaurus/core: high; affected range `<=4.0.0-canary-6835`; npm fix candidate not available.
- @docusaurus/mdx-loader: high; affected range `<=4.0.0-canary-6835`; npm fix candidate not available.
- @docusaurus/plugin-content-blog: high; affected range `<=4.0.0-canary-6835`; npm fix candidate not available.
- @docusaurus/plugin-content-docs: high; affected range `<=4.0.0-canary-6835`; npm fix candidate not available.
- @docusaurus/plugin-content-pages: high; affected range `<=4.0.0-canary-6835`; npm fix candidate not available.
- @docusaurus/plugin-css-cascade-layers: high; affected range `<=4.0.0-canary-6835`; npm fix candidate not available.
- @docusaurus/plugin-debug: high; affected range `<=4.0.0-canary-6835`; npm fix candidate not available.
- @docusaurus/plugin-google-analytics: high; affected range `*`; npm fix candidate not available.
- @docusaurus/plugin-google-gtag: high; affected range `<=4.0.0-canary-6835`; npm fix candidate not available.
- @docusaurus/plugin-google-tag-manager: high; affected range `<=4.0.0-canary-6835`; npm fix candidate not available.
- @docusaurus/plugin-sitemap: high; affected range `<=4.0.0-canary-6835`; npm fix candidate not available.
- @docusaurus/plugin-svgr: high; affected range `<=4.0.0-canary-6835`; npm fix candidate not available.
- @docusaurus/preset-classic: high; affected range `<=4.0.0-canary-6835`; npm fix candidate not available.
- @docusaurus/theme-classic: high; affected range `<=4.0.0-canary-6835`; npm fix candidate not available.
- @docusaurus/theme-common: high; affected range `<=4.0.0-canary-6835`; npm fix candidate not available.
- @docusaurus/theme-search-algolia: high; affected range `<=4.0.0-canary-6835`; npm fix candidate not available.
- @docusaurus/utils: high; affected range `<=4.0.0-canary-6835`; npm fix candidate not available.
- @docusaurus/utils-validation: high; affected range `<=4.0.0-canary-6835`; npm fix candidate not available.
- braces: high; affected range `*`; npm fix candidate not available.
- chokidar: high; affected range `2.0.0 - 3.6.0`; npm fix candidate not available.
- copy-webpack-plugin: high; affected range `6.0.0 - 12.0.2`; npm fix candidate not available.
- fast-glob: high; affected range `*`; npm fix candidate not available.
- globby: high; affected range `>=8.0.0`; npm fix candidate not available.
- http-cache-semantics: high; affected range `<=4.2.0`; npm fix candidate available.
- http-proxy-middleware: high; affected range `>=0.3.0`; npm fix candidate not available.
- micromatch: high; affected range `>=0.2.0`; npm fix candidate not available.
- webpack-dev-server: high; affected range `>=1.15.0`; npm fix candidate not available.

After: info: 0, low: 0, moderate: 0, high: 29, critical: 0, total: 29

- @docusaurus/babel: high; affected range `<=4.0.0-canary-6835`; npm fix candidate requires breaking changes; manual review.
- @docusaurus/bundler: high; affected range `<=4.0.0-canary-6835`; npm fix candidate requires breaking changes; manual review.
- @docusaurus/core: high; affected range `<=4.0.0-canary-6835`; npm fix candidate requires breaking changes; manual review.
- @docusaurus/mdx-loader: high; affected range `<=4.0.0-canary-6835`; npm fix candidate requires breaking changes; manual review.
- @docusaurus/plugin-content-blog: high; affected range `<=4.0.0-canary-6835`; npm fix candidate not available.
- @docusaurus/plugin-content-docs: high; affected range `<=4.0.0-canary-6835`; npm fix candidate requires breaking changes; manual review.
- @docusaurus/plugin-content-pages: high; affected range `<=4.0.0-canary-6835`; npm fix candidate not available.
- @docusaurus/plugin-css-cascade-layers: high; affected range `<=4.0.0-canary-6835`; npm fix candidate not available.
- @docusaurus/plugin-debug: high; affected range `<=4.0.0-canary-6835`; npm fix candidate not available.
- @docusaurus/plugin-google-analytics: high; affected range `*`; npm fix candidate not available.
- @docusaurus/plugin-google-gtag: high; affected range `<=4.0.0-canary-6835`; npm fix candidate not available.
- @docusaurus/plugin-google-tag-manager: high; affected range `<=4.0.0-canary-6835`; npm fix candidate not available.
- @docusaurus/plugin-sitemap: high; affected range `<=4.0.0-canary-6835`; npm fix candidate not available.
- @docusaurus/plugin-svgr: high; affected range `<=4.0.0-canary-6835`; npm fix candidate not available.
- @docusaurus/preset-classic: high; affected range `<=4.0.0-canary-6835`; npm fix candidate not available.
- @docusaurus/theme-classic: high; affected range `<=4.0.0-canary-6835`; npm fix candidate not available.
- @docusaurus/theme-common: high; affected range `<=4.0.0-canary-6835`; npm fix candidate requires breaking changes; manual review.
- @docusaurus/theme-search-algolia: high; affected range `<=4.0.0-canary-6835`; npm fix candidate not available.
- @docusaurus/utils: high; affected range `<=4.0.0-canary-6835`; npm fix candidate requires breaking changes; manual review.
- @docusaurus/utils-validation: high; affected range `<=4.0.0-canary-6835`; npm fix candidate requires breaking changes; manual review.
- @easyops-cn/docusaurus-search-local: high; affected range `>=0.27.0`; npm fix candidate requires breaking changes; manual review.
- braces: high; affected range `*`; npm fix candidate requires breaking changes; manual review.
- chokidar: high; affected range `2.0.0 - 3.6.0`; npm fix candidate requires breaking changes; manual review.
- copy-webpack-plugin: high; affected range `6.0.0 - 12.0.2`; npm fix candidate requires breaking changes; manual review.
- fast-glob: high; affected range `*`; npm fix candidate requires breaking changes; manual review.
- globby: high; affected range `>=8.0.0`; npm fix candidate requires breaking changes; manual review.
- http-proxy-middleware: high; affected range `>=0.3.0`; npm fix candidate requires breaking changes; manual review.
- micromatch: high; affected range `>=0.2.0`; npm fix candidate requires breaking changes; manual review.
- webpack-dev-server: high; affected range `>=1.15.0`; npm fix candidate requires breaking changes; manual review.

## Production build

Passed.

## Remaining work

Review retained overrides and peer constraints, transitive dependency fixes, and any major-version migration requirements. Build and installation logs are available in the workflow run.

- Automatic audit fix returned exit 1; remaining findings or a tool error require manual review.
