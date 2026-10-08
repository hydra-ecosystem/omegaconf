module.exports = {
  title: 'OmegaConf',
  tagline: 'Flexible configuration for Python',
  url: 'https://omegaconf.cli.dev',
  baseUrl: '/',
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
        blog: {showReadingTime: true},
        theme: {customCss: require.resolve('./src/css/custom.css')},
      },
    ],
  ],
  themes: [
    [
      require.resolve('@easyops-cn/docusaurus-search-local'),
      {hashed: true, indexBlog: true},
    ],
  ],
  themeConfig: {
    colorMode: {defaultMode: 'dark', respectPrefersColorScheme: false},
    navbar: {
      title: 'OmegaConf',
      logo: {alt: 'Fingi, the OmegaConf mascot', src: 'img/omegaconf-mark.svg', srcDark: 'img/omegaconf-mark-dark.svg'},
      items: [
        {type: 'docSidebar', sidebarId: 'docsSidebar', position: 'left', label: 'Docs'},
        {to: '/blog', label: 'Blog', position: 'left'},
        {type: 'docsVersionDropdown', position: 'right'},
        {href: 'https://github.com/hydra-ecosystem/omegaconf', label: 'GitHub', position: 'right'},
      ],
    },
    footer: {
      style: 'light',
      links: [
        {title: 'Documentation', items: [{label: 'Stable 2.3', to: '/docs/'}, {label: '2.4 prerelease', to: '/docs/next/'}]},
        {title: 'Project', items: [{label: 'Blog', to: '/blog'}, {label: 'GitHub', href: 'https://github.com/hydra-ecosystem/omegaconf'}]},
      ],
    },
  },
};
