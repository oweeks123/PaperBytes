<script lang="ts">
  import { base } from '$app/paths';

  let {
    title,
    updated,
    children
  }: {
    title: string;
    updated?: string;
    children: import('svelte').Snippet;
  } = $props();
</script>

<a class="back" href="{base}/">← Back to Paper Heroes</a>

<article class="page">
  <h1>{title}</h1>
  {#if updated}
    <p class="updated">Last updated {updated}</p>
  {/if}
  <div class="prose">
    {@render children()}
  </div>
</article>

<style>
  .back {
    display: inline-block;
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    font-weight: 700;
    color: var(--ink);
    text-decoration: none;
    padding: 8px 12px;
    border: 2px solid var(--ink);
    border-radius: 11px;
    background: #fff;
    margin-bottom: 22px;
  }
  .back:hover {
    background: var(--sky);
  }
  .page {
    max-width: 760px;
    margin: 0 auto;
    background: var(--face);
    border: 3px solid var(--ink);
    border-radius: 24px;
    box-shadow: 0 12px 0 var(--ink);
    padding: 40px 44px 46px;
  }
  h1 {
    font-size: 34px;
    font-weight: 800;
    letter-spacing: -0.5px;
    line-height: 1.1;
    margin-bottom: 6px;
  }
  .updated {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--muted-2);
    margin-bottom: 24px;
  }
  .prose :global(h2) {
    font-size: 20px;
    font-weight: 800;
    margin: 30px 0 10px;
  }
  .prose :global(h2:first-child) {
    margin-top: 0;
  }
  .prose :global(p) {
    font-size: 15px;
    line-height: 1.65;
    color: var(--ink);
    margin-bottom: 14px;
  }
  .prose :global(ul) {
    margin: 0 0 16px 20px;
  }
  .prose :global(li) {
    font-size: 15px;
    line-height: 1.6;
    margin-bottom: 8px;
  }
  .prose :global(strong) {
    font-weight: 700;
  }
  .prose :global(a) {
    color: var(--grape);
    font-weight: 700;
  }
  .prose :global(.callout) {
    border: 2px solid var(--ink);
    border-radius: 14px;
    background: #fff;
    padding: 16px 18px;
    margin: 18px 0;
  }
  .prose :global(.callout.warn) {
    background: #fff6ef;
    border-color: var(--warn);
  }
  .prose :global(.callout p:last-child) {
    margin-bottom: 0;
  }
  @media (max-width: 900px) {
    .page {
      padding: 28px 22px 32px;
    }
    h1 {
      font-size: 27px;
    }
  }
</style>
