<script lang="ts">
  import { base } from '$app/paths';
  import { goto } from '$app/navigation';
  import { session } from '$lib/session.svelte';
  import { ui } from '$lib/ui.svelte';

  let busy = $state(false);
  let wantPremiumAfterAuth = $state(false);

  // Anonymous user chose Premium → after they register, complete the upgrade.
  $effect(() => {
    if (wantPremiumAfterAuth && session.isSignedIn) {
      wantPremiumAfterAuth = false;
      if (!session.isPaid) session.upgrade().then(() => goto(`${base}/decks`));
      else goto(`${base}/decks`);
    }
  });

  async function selectFree() {
    if (session.isSignedIn) session.signOut();
    goto(`${base}/`);
  }
  async function selectRegistered() {
    if (!session.isSignedIn) {
      ui.openAuth(); // register → free_registered
      return;
    }
    if (session.isPaid) {
      busy = true;
      try {
        await session.downgrade();
      } finally {
        busy = false;
      }
    }
    goto(`${base}/`);
  }
  async function selectPremium() {
    if (!session.isSignedIn) {
      wantPremiumAfterAuth = true;
      ui.openAuth();
      return;
    }
    if (!session.isPaid) {
      busy = true;
      try {
        await session.upgrade();
      } finally {
        busy = false;
      }
    }
    goto(`${base}/decks`);
  }

  const tier = $derived(session.tier);
</script>

<h1 class="ttl">Choose your plan</h1>
<p class="sub">FREE · REGISTERED · PREMIUM — SWITCH ANY TIME.</p>

<div class="grid">
  <!-- FREE -->
  <div class="plan" class:current={tier === 'anon'}>
    <div class="pname">Free</div>
    <div class="price">£0</div>
    <ul>
      <li>One random appraised paper per visit</li>
      <li>AI summary, critical appraisal &amp; stats</li>
      <li>Hero / villain illustration</li>
      <li class="muted">Generic advertising</li>
    </ul>
    {#if tier === 'anon'}
      <div class="badge-current">Current plan</div>
    {:else}
      <button class="pick ghost" onclick={selectFree} disabled={busy}>Continue free</button>
    {/if}
  </div>

  <!-- FREE-REGISTERED -->
  <div class="plan" class:current={tier === 'free_registered'}>
    <div class="pname">Registered</div>
    <div class="price">£0<span>· verified practitioner</span></div>
    <ul>
      <li>Everything in Free</li>
      <li>Registered practitioner account</li>
      <li class="soon">Full pharma / POM advertising <em>(coming soon)</em></li>
      <li class="soon">Add a reflection to the PDF <em>(coming soon)</em></li>
    </ul>
    {#if tier === 'free_registered'}
      <div class="badge-current">Current plan</div>
    {:else}
      <button class="pick" onclick={selectRegistered} disabled={busy}>
        {session.isSignedIn ? 'Switch to Registered' : 'Register free'}
      </button>
    {/if}
  </div>

  <!-- PREMIUM -->
  <div class="plan premium" class:current={tier === 'paid'}>
    <div class="ribbon">Most features</div>
    <div class="pname">Premium</div>
    <div class="price">Simulated<span>· no charge yet</span></div>
    <ul>
      <li>Everything in Registered</li>
      <li><strong>Card Decks</strong> — save &amp; organise cards</li>
      <li>Scrollable decks; open any card</li>
      <li>Write a <strong>reflection on the back</strong> of a card (shared across decks)</li>
      <li>Reflection included in the PDF</li>
    </ul>
    {#if tier === 'paid'}
      <div class="badge-current">Current plan</div>
    {:else}
      <button class="pick primary" onclick={selectPremium} disabled={busy}>
        {busy ? 'Please wait…' : '✦ Go Premium'}
      </button>
    {/if}
  </div>
</div>

<p class="foot">Payments aren’t wired up yet — “Go Premium” upgrades your account instantly for now.</p>

<style>
  .ttl {
    font-size: 34px;
    font-weight: 800;
    letter-spacing: -1px;
  }
  .sub {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    letter-spacing: 0.14em;
    color: var(--muted-2);
    margin: 6px 0 24px;
  }
  .grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 20px;
    align-items: stretch;
  }
  @media (max-width: 820px) {
    .grid {
      grid-template-columns: 1fr;
    }
  }
  .plan {
    position: relative;
    border: 3px solid var(--ink);
    border-radius: 20px;
    box-shadow: 0 8px 0 var(--ink);
    background: var(--face);
    padding: 24px;
    display: flex;
    flex-direction: column;
  }
  .plan.premium {
    background: #fffaf0;
  }
  .plan.current {
    outline: 4px solid var(--grape);
    outline-offset: 3px;
  }
  .ribbon {
    position: absolute;
    top: -14px;
    right: 16px;
    background: var(--grape);
    color: #fff;
    font-family: 'JetBrains Mono', monospace;
    font-size: 9px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    font-weight: 700;
    padding: 5px 10px;
    border: 2px solid var(--ink);
    border-radius: 8px;
  }
  .pname {
    font-size: 22px;
    font-weight: 800;
  }
  .price {
    font-size: 26px;
    font-weight: 800;
    margin: 6px 0 16px;
    color: var(--grape);
  }
  .price span {
    display: block;
    font-size: 11px;
    font-weight: 500;
    letter-spacing: 0.06em;
    color: var(--muted);
    margin-top: 2px;
  }
  ul {
    list-style: none;
    padding: 0;
    margin: 0 0 20px;
    flex: 1;
  }
  li {
    position: relative;
    padding: 7px 0 7px 24px;
    font-size: 14px;
    line-height: 1.35;
    border-top: 1px solid var(--line);
  }
  li::before {
    content: '✓';
    position: absolute;
    left: 0;
    color: var(--good);
    font-weight: 800;
  }
  li.muted {
    color: var(--muted);
  }
  li.soon {
    color: var(--muted);
  }
  li.soon em {
    font-style: normal;
    font-family: 'JetBrains Mono', monospace;
    font-size: 9px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--warn);
  }
  .pick {
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    font-weight: 700;
    padding: 13px 16px;
    border: 2px solid var(--ink);
    border-radius: 13px;
    background: #fff;
    color: var(--ink);
    cursor: pointer;
  }
  .pick.primary {
    background: var(--grape);
    color: #fff;
    box-shadow: 0 5px 0 var(--grape-shadow);
  }
  .pick:disabled {
    opacity: 0.6;
    cursor: default;
  }
  .badge-current {
    text-align: center;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    font-weight: 700;
    color: var(--grape);
    padding: 13px;
    border: 2px dashed var(--grape);
    border-radius: 13px;
  }
  .foot {
    margin-top: 20px;
    font-size: 13px;
    color: var(--muted-2);
  }
</style>
