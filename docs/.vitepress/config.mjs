import { defineConfig } from 'vitepress'
import { readdirSync, existsSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const gen = join(dirname(fileURLToPath(import.meta.url)), '../generated')
const capabilityItems = existsSync(gen)
  ? readdirSync(gen)
      .filter((f) => f.startsWith('capability-') && f.endsWith('.md'))
      .map((f) => {
        const n = f.slice('capability-'.length, -'.md'.length)
        return { text: n, link: `/generated/capability-${n}` }
      })
  : []

export default defineConfig({
  base: '/forge/',
  title: 'forge',
  description: "maxime's personal operating framework for working with Claude",
  // A dead link is a documentation bug; the build should say so.
  ignoreDeadLinks: false,
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
          { text: 'A base CLAUDE.md', link: '/generated/claude-md' },
        ],
      },
      {
        text: 'Capabilities',
        items: capabilityItems,
      },
      {
        text: 'How-to',
        items: [
          { text: 'Start a project', link: '/how-to/start-a-project' },
          { text: 'Set up the session monitor', link: '/how-to/monitor' },
          { text: 'Connect GitHub', link: '/how-to/connect-github' },
          { text: 'Build & run these docs', link: '/how-to/docs' },
        ],
      },
      { text: 'Frictions log', link: '/generated/frictions' },
    ],
    socialLinks: [{ icon: 'github', link: 'https://github.com/mde-pach/forge' }],
  },
})
