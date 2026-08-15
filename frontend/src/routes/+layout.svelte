<script lang="ts">
  import { onMount } from 'svelte';
  import { base } from '$app/paths';
  import { session } from '$lib/session.svelte';
  import { ui } from '$lib/ui.svelte';
  import AuthModal from '$lib/components/AuthModal.svelte';
  import '../app.css';

  let { children } = $props();
  let menuOpen = $state(false);

  onMount(() => {
    session.init();
  });

  function signOut() {
    session.signOut();
    menuOpen = false;
  }
</script>

<header class="topbar">
  <a class="brand" href="{base}/">Paper Heroes</a>

  <nav>
    {#if session.isPaid}
      <a class="navlink" href="{base}/decks">My Decks</a>
    {/if}

    {#if session.isSignedIn}
      <div class="acct">
        <button class="chip" onclick={() => (menuOpen = !menuOpen)} aria-haspopup="menu">
          <span class="tier tier-{session.tier}">
            {session.isPaid ? 'PREMIUM' : 'REGISTERED'}
          </span>
          <span class="who">{session.user?.email}</span>
          <span class="caret">▾</span>
        </button>
        {#if menuOpen}
          <div class="menu" role="menu">
            {#if session.isPaid}
              <a role="menuitem" href="{base}/decks" onclick={() => (menuOpen = false)}>My Decks</a>
            {/if}
            <a
              role="menuitem"
              class="up"
              href="{base}/pricing"
              onclick={() => (menuOpen = false)}>✦ Plans &amp; tiers</a
            >
            <button role="menuitem" onclick={signOut}>Sign out</button>
          </div>
        {/if}
      </div>
    {:else}
      <button class="chip signin" onclick={() => ui.openAuth()}>Sign in</button>
    {/if}
  </nav>
</header>

<main>
  {@render children()}
</main>

<AuthModal open={ui.authOpen} onclose={() => ui.closeAuth()} />

<style>
  .topbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 18px;
  }
  .brand {
    font-weight: 800;
    font-size: 18px;
    letter-spacing: -0.5px;
    color: var(--ink);
    text-decoration: none;
    white-space: nowrap;
  }
  nav {
    display: flex;
    align-items: center;
    gap: 10px;
  }
  @media (max-width: 560px) {
    .topbar {
      gap: 8px;
    }
    .brand {
      font-size: 15px;
    }
    nav {
      gap: 7px;
    }
  }
  .navlink {
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
  }
  .acct {
    position: relative;
  }
  .chip {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    letter-spacing: 0.08em;
    font-weight: 700;
    padding: 7px 12px;
    border: 2px solid var(--ink);
    border-radius: 11px;
    background: #fff;
    color: var(--ink);
    cursor: pointer;
    max-width: 60vw;
  }
  .chip .who {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 34vw;
    text-transform: none;
    letter-spacing: 0;
  }
  .tier {
    padding: 2px 6px;
    border-radius: 6px;
    font-size: 8.5px;
    letter-spacing: 0.12em;
  }
  .tier-paid {
    background: var(--butter);
    color: var(--butter-ink);
  }
  .tier-free_registered {
    background: var(--sky);
    color: var(--ink);
  }
  .signin {
    background: var(--grape);
    color: #fff;
  }
  .caret {
    opacity: 0.6;
  }
  .menu {
    position: absolute;
    right: 0;
    top: calc(100% + 6px);
    background: var(--face);
    border: 2px solid var(--ink);
    border-radius: 12px;
    box-shadow: 0 6px 0 var(--ink);
    padding: 6px;
    display: flex;
    flex-direction: column;
    min-width: 190px;
    z-index: 50;
  }
  .menu a,
  .menu button {
    text-align: left;
    background: none;
    border: none;
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 14px;
    color: var(--ink);
    padding: 9px 10px;
    border-radius: 8px;
    cursor: pointer;
    text-decoration: none;
  }
  .menu a:hover,
  .menu button:hover {
    background: rgba(123, 91, 232, 0.1);
  }
  .menu .up {
    color: var(--grape);
    font-weight: 700;
  }
</style>
