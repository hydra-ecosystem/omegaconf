module.exports = {
  title: 'OmegaConf',
  tagline: 'Flexible configuration for Python',
  url: 'https://hydra-ecosystem.github.io',
  baseUrl: '/omegaconf/',
  favicon: 'img/omegaconf-mark.svg',
  onBrokenLinks: 'throw',
  onBrokenAnchors: 'throw',
  markdown: {format: 'detect', hooks: {onBrokenMarkdownLinks: 'throw'}},
  presets: [
    [
      'classic',
      {
        docs: {
          sidebarPath: require.resolve('./sidebars.js'),
          lastVersion: '2.3',
          versions: {
            current: {label: '2.4 (prerelease)', path: 'next'},
            '2.3': {label: '2.3', path: ''},
          },
        },
        blog: false,
        theme: {customCss: require.resolve('./src/css/custom.css')},
      },
    ],
  ],
  themes: [
    [
      require.resolve('@easyops-cn/docusaurus-search-local'),
      {hashed: true, indexBlog: false},
    ],
  ],
  themeConfig: {
    colorMode: {defaultMode: 'dark', respectPrefersColorScheme: false},
    navbar: {
      title: 'OmegaConf',
      logo: {alt: 'OmegaConf mark', src: 'img/omegaconf-mark.svg', srcDark: 'img/omegaconf-mark-dark.svg'},
      items: [
        {type: 'docSidebar', sidebarId: 'docsSidebar', position: 'left', label: 'Docs'},
        {type: 'docsVersionDropdown', position: 'right'},
        {href: 'https://github.com/hydra-ecosystem/omegaconf', label: 'GitHub', position: 'right'},
      ],
    },
    footer: {
      style: 'light',
      links: [
        {title: 'Documentation', items: [{label: 'Stable 2.3', to: '/docs/'}, {label: '2.4 prerelease', to: '/docs/next/'}]},
        {title: 'Project', items: [{label: 'GitHub', href: 'https://github.com/hydra-ecosystem/omegaconf'}]},
      ],
    },
  },
};
