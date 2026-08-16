import { defineConfig } from 'vitepress'

export default defineConfig({
  title: 'forge',
  description: "maxime's personal operating framework for working with Claude",
  ignoreDeadLinks: true,
  themeConfig: {
    nav: [
      { text: 'Kernel', link: '/generated/kernel' },
      { text: 'Contract', link: '/generated/contract' },
      { text: 'Frictions', link: '/generated/frictions' },
    ],
    sidebar: [
      { text: 'Why forge is shaped this way', link: '/explanation' },
      {
        text: 'Reference',
        items: [
          { text: 'Kernel — the operating mode', link: '/generated/kernel' },
          { text: 'Capability contract v1.0.0', link: '/generated/contract' },
          { text: 'Evidence base (sources)', link: '/generated/sources' },
        ],
      },
      {
        text: 'Capabilities',
        items: [
          { text: 'loop', link: '/generated/capability-loop' },
          { text: 'validate', link: '/generated/capability-validate' },
        ],
      },
      {
        text: 'How-to',
        items: [
          { text: 'Connect GitHub', link: '/how-to/connect-github' },
          { text: 'Build & run these docs', link: '/how-to/docs' },
        ],
      },
      { text: 'Frictions log', link: '/generated/frictions' },
    ],
    socialLinks: [{ icon: 'github', link: 'https://github.com/mde-pach/forge' }],
  },
})
