import adapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

/** @type {import('@sveltejs/kit').Config} */
const config = {
  preprocess: vitePreprocess(),
  kit: {
    // SPA: a single fallback shell, client-rendered, served by FastAPI at /ui.
    adapter: adapter({ fallback: 'index.html' }),
    paths: { base: '/ui' }
  }
};

export default config;
