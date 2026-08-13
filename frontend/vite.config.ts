import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

// In dev, proxy the API calls to the FastAPI server on :8000 so the app is
// effectively same-origin (no CORS). In production the built static files are
// served by FastAPI itself at /ui, so these paths hit the same origin directly.
const API = 'http://localhost:8000';

export default defineConfig({
  plugins: [sveltekit()],
  server: {
    proxy: {
      '/random': API,
      '/geo': API,
      '/articles': API,
      '/auth': API,
      '/reading-list': API,
      '/specialties': API,
      '/search': API
    }
  }
});
