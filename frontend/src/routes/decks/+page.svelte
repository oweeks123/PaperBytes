<script lang="ts">
  import { base } from '$app/paths';
  import { goto } from '$app/navigation';
  import { session } from '$lib/session.svelte';
  import { ui } from '$lib/ui.svelte';
  import { listDecks, createDeck, type DeckSummary } from '$lib/api';

  let decks = $state<DeckSummary[] | null>(null);
  let error = $state<string | null>(null);
  let creating = $state(false);
  let newName = $state('');
  let busy = $state(false);

  async function load() {
    error = null;
    try {
      decks = await listDecks();
    } catch (e) {
      error = (e as Error).message;
    }
  }

  // Load once the session is known and the user is paid.
  $effect(() => {
    if (session.ready && session.isPaid && decks === null) load();
  });

  async function create() {
    const name = newName.trim();
    if (!name || busy) return;
    busy = true;
    try {
      const d = await createDeck(name);
      newName = '';
      creating = false;
      goto(`${base}/decks/${d.id}`);
    } catch (e) {
      error = (e as Error).message;
    } finally {
      busy = false;
    }
  }
</script>

<h1 class="ttl">My Decks</h1>
<p class="sub">YOUR SAVED CARDS, ORGANISED INTO DECKS.</p>

{#if !session.ready}
  <div class="msg">Loading…</div>
{:else if !session.isSignedIn}
  <div class="gate">
    <h2>Card Decks are a Premium feature</h2>
    <p>Sign in or register (free), then upgrade to Premium to save cards into decks.</p>
    <button class="cta" onclick={() => ui.openAuth()}>Sign in / register</button>
  </div>
{:else if !session.isPaid}
  <div class="gate">
    <h2>Upgrade to Premium</h2>
    <p>Premium lets you save cards into searchable decks and write a reflection on the back of each card.</p>
    <button class="cta" onclick={() => session.upgrade()}>✦ Upgrade to Premium</button>
  </div>
{:else}
  {#if error}<div class="msg err">Error: {error}</div>{/if}

  <div class="grid">
    <!-- New deck tile -->
    <div class="tile new">
      {#if creating}
        <input
          bind:value={newName}
          placeholder="Deck name"
          maxlength="120"
          onkeydown={(e) => e.key === 'Enter' && create()}
        />
        <div class="row">
          <button class="mini" onclick={create} disabled={busy}>Create</button>
          <button class="mini ghost" onclick={() => (creating = false)}>Cancel</button>
        </div>
      {:else}
        <button class="addbtn" onclick={() => (creating = true)}>
          <span class="plus">＋</span>
          New deck
        </button>
      {/if}
    </div>

    {#if decks}
      {#each decks as d (d.id)}
        <a class="tile" href="{base}/decks/{d.id}">
          <div class="pile">
            {#if d.cover_pmids.length}
              {#each d.cover_pmids.slice(0, 3) as pmid, i (pmid)}
                <div class="mini-card" style="--i:{i}">
                  <img src="/articles/{pmid}/image" alt="" loading="lazy" onerror={(e) => ((e.currentTarget as HTMLImageElement).style.visibility = 'hidden')} />
                </div>
              {/each}
            {:else}
              <div class="mini-card empty"><span>Empty deck</span></div>
            {/if}
          </div>
          <div class="dname">{d.name}</div>
          <div class="dcount">{d.card_count} {d.card_count === 1 ? 'card' : 'cards'}</div>
        </a>
      {/each}
    {/if}
  </div>

  {#if decks && decks.length === 0}
    <p class="hint">No decks yet — create one, then add cards from the home page.</p>
  {/if}
{/if}

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
    margin: 6px 0 22px;
  }
  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(190px, 1fr));
    gap: 24px;
  }
  .tile {
    border: 2px dashed transparent;
    border-radius: 18px;
    text-decoration: none;
    color: var(--ink);
    display: flex;
    flex-direction: column;
    align-items: center;
  }
  .pile {
    position: relative;
    width: 100%;
    height: 210px;
    margin-bottom: 12px;
  }
  .mini-card {
    position: absolute;
    left: 50%;
    top: 8px;
    width: 132px;
    height: 190px;
    margin-left: -66px;
    background: var(--sky);
    border: 3px solid var(--ink);
    border-radius: 16px;
    box-shadow: 0 6px 0 var(--ink);
    overflow: hidden;
    transform: translateX(calc((var(--i) - 1) * 16px)) rotate(calc((var(--i) - 1) * 4deg));
    z-index: calc(3 - var(--i));
  }
  .mini-card img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
  .mini-card.empty {
    display: flex;
    align-items: center;
    justify-content: center;
    background: repeating-linear-gradient(45deg, #fff, #fff 8px, var(--seg-off) 8px, var(--seg-off) 16px);
    transform: none;
    margin-left: -66px;
  }
  .mini-card.empty span {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    letter-spacing: 0.1em;
    color: var(--muted);
  }
  .dname {
    font-weight: 800;
    font-size: 17px;
    text-align: center;
  }
  .dcount {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    letter-spacing: 0.1em;
    color: var(--muted-2);
    margin-top: 3px;
  }
  .tile.new {
    justify-content: center;
    min-height: 250px;
  }
  .addbtn {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    width: 100%;
    height: 210px;
    border: 3px dashed var(--muted-2);
    border-radius: 16px;
    background: #fff;
    color: var(--grape);
    font-weight: 800;
    font-size: 16px;
    cursor: pointer;
    justify-content: center;
  }
  .plus {
    font-size: 40px;
    line-height: 1;
  }
  .tile.new input {
    width: 100%;
    padding: 11px;
    border: 2px solid var(--ink);
    border-radius: 12px;
    font-size: 15px;
    margin-bottom: 10px;
  }
  .row {
    display: flex;
    gap: 8px;
    width: 100%;
  }
  .mini {
    flex: 1;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    font-weight: 700;
    padding: 10px;
    border: 2px solid var(--ink);
    border-radius: 11px;
    background: var(--grape);
    color: #fff;
    cursor: pointer;
  }
  .mini.ghost {
    background: #fff;
    color: var(--ink);
  }
  .gate {
    border: 3px solid var(--ink);
    border-radius: 20px;
    box-shadow: 0 8px 0 var(--ink);
    background: var(--face);
    padding: 30px;
    max-width: 560px;
  }
  .gate h2 {
    font-size: 22px;
    font-weight: 800;
    margin-bottom: 8px;
  }
  .gate p {
    color: var(--muted);
    margin-bottom: 16px;
  }
  .cta {
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    font-weight: 700;
    padding: 13px 20px;
    border: 2px solid var(--ink);
    border-radius: 13px;
    background: var(--grape);
    color: #fff;
    cursor: pointer;
    box-shadow: 0 5px 0 var(--grape-shadow);
  }
  .msg {
    color: var(--muted);
    padding: 20px 0;
  }
  .msg.err {
    color: var(--bad);
  }
  .hint {
    color: var(--muted-2);
    margin-top: 18px;
    font-size: 14px;
  }
</style>
