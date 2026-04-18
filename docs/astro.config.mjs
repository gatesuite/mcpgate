import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

export default defineConfig({
  site: 'https://gatesuite.github.io',
  base: '/mcpgate',
  integrations: [
    starlight({
      title: 'MCPGate',
      description: 'Ultra-fast API key lifecycle and verification service for MCP servers and AI agents.',
      logo: {
        src: './src/assets/logo.svg',
      },
      customCss: ['./src/styles/custom.css'],
      head: [
        {
          tag: 'script',
          content: `
            document.addEventListener('DOMContentLoaded', () => {
              document.querySelectorAll('.social-icons a[href^="http"]').forEach(a => {
                a.target = '_blank';
                a.rel = 'noopener noreferrer';
              });
            });
          `,
        },
      ],
      social: [
        { icon: 'github', label: 'GitHub', href: 'https://github.com/gatesuite/mcpgate' },
      ],
      editLink: {
        baseUrl: 'https://github.com/gatesuite/mcpgate/edit/main/docs/',
      },
      sidebar: [
        {
          label: 'Start here',
          items: [
            { label: 'Introduction', link: '/' },
            { label: 'Quick Start', slug: 'quickstart' },
          ],
        },
        {
          label: 'Guides',
          items: [
            { label: 'How It Works', slug: 'how-it-works' },
            { label: 'Integration Guide', slug: 'integration' },
          ],
        },
        {
          label: 'Reference',
          items: [
            { label: 'API Reference', slug: 'api-reference' },
            { label: 'Deployment', slug: 'deployment' },
            { label: 'Architecture', slug: 'architecture' },
            { label: 'Security', slug: 'security' },
          ],
        },
        {
          label: 'Contributing',
          items: [
            { label: 'Contributing', slug: 'contributing' },
          ],
        },
      ],
    }),
  ],
});
