<script lang="ts">
  import { page } from '$app/stores';
  import { base } from '$app/paths';
  import { goto } from '$app/navigation';
  import { session } from '$lib/session.svelte';
  import { ui } from '$lib/ui.svelte';
  import { getDeck, renameDeck, deleteDeck, removeCardFromDeck, type Deck } from '$lib/api';

  let deck = $state<Deck | null>(null);
  let error = $state<string | null>(null);
  let editingName = $state(false);
  let nameDraft = $state('');
  let loadedId = $state<number | null>(null);

  const deckId = $derived(Number($page.params.id));

  async function load() {
    error = null;
    deck = null;
    try {
      deck = await getDeck(deckId);
    } catch (e) {
      error = (e as Error).message;
    }
  }

  // (Re)load when the session is ready + paid, or when the deck id in the URL changes.
  $effect(() => {
    if (session.ready && session.isPaid && deckId && loadedId !== deckId) {
      loadedId = deckId;
      load();
    }
  });

  async function saveName() {
    if (!deck) return;
    const name = nameDraft.trim();
    if (name && name !== deck.name) {
      const d = await renameDeck(deck.id, name);
      deck.name = d.name;
    }
    editingName = false;
  }

  async function removeCard(pmid: string) {
    if (!deck) return;
    if (!confirm('Remove this card from the deck? Your reflection stays in your account.')) return;
    await removeCardFromDeck(deck.id, pmid);
    deck.cards = deck.cards.filter((c) => c.pubmed_id !== pmid);
    deck.card_count = deck.cards.length;
  }

  async function removeDeck() {
    if (!deck) return;
    if (!confirm(`Delete the deck “${deck.name}”? Cards stay in your account; only the deck is removed.`))
      return;
    await deleteDeck(deck.id);
    goto(`${base}/decks`);
  }
</script>

<div class="head">
  <a class="back" href="{base}/decks">← My Decks</a>
</div>

{#if !session.ready}
  <div class="msg">Loading…</div>
{:else if !session.isSignedIn}
  <div class="msg">Please <button class="link" onclick={() => ui.openAuth()}>sign in</button> to view decks.</div>
{:else if !session.isPaid}
  <div class="msg">Card Decks are a Premium feature. <a class="link" href="{base}/pricing">See plans</a>.</div>
{:else if error}
  <div class="msg err">{error}</div>
{:else if deck}
  <div class="titlerow">
    {#if editingName}
      <input
        class="nameedit"
        bind:value={nameDraft}
        maxlength="120"
        onkeydown={(e) => e.key === 'Enter' && saveName()}
      />
      <button class="mini" onclick={saveName}>Save</button>
      <button class="mini ghost" onclick={() => (editingName = false)}>Cancel</button>
    {:else}
      <h1 class="ttl">{deck.name}</h1>
      <button
        class="iconbtn"
        title="Rename deck"
        onclick={() => {
          nameDraft = deck!.name;
          editingName = true;
        }}>✎</button
      >
      <button class="iconbtn danger" title="Delete deck" onclick={removeDeck}>🗑</button>
    {/if}
    <span class="count">{deck.card_count} {deck.card_count === 1 ? 'card' : 'cards'}</span>
  </div>

  {#if deck.cards.length === 0}
    <div class="empty">
      This deck is empty. Open a card on the <a href="{base}/">home page</a> and use
      <strong>“Add to deck”</strong>.
    </div>
  {:else}
    <p class="stripnote">Tap a card to open it in a new tab.</p>
    <!-- Scrollable strip of cards (image + title). Each opens the home page for that
         card in a new tab — a fresh page load, so it counts as a new visit. -->
    <div class="strip">
      {#each deck.cards as c (c.pubmed_id)}
        <div class="thumb">
          <a
            class="thumb-link"
            href="{base}/?pmid={encodeURIComponent(c.pubmed_id)}"
            target="_blank"
            rel="noopener"
          >
            <div class="thumb-img">
              <img
                src={c.image_url}
                alt=""
                loading="lazy"
                onerror={(e) => ((e.currentTarget as HTMLImageElement).style.visibility = 'hidden')}
              />
              {#if c.reflection}<span class="badge" title="Has a reflection">📝</span>{/if}
              <span class="open-hint">Open ↗</span>
            </div>
            <div class="thumb-title">{c.title}</div>
          </a>
          <button class="thumb-rm" title="Remove from deck" onclick={() => removeCard(c.pubmed_id)}
            >✕</button
          >
        </div>
      {/each}
    </div>
  {/if}
{/if}

<style>
  .head {
    margin-bottom: 12px;
  }
  .back {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    font-weight: 700;
    color: var(--ink);
    text-decoration: none;
  }
  .titlerow {
    display: flex;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
    margin-bottom: 18px;
  }
  .ttl {
    font-size: 32px;
    font-weight: 800;
    letter-spacing: -1px;
  }
  .count {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    letter-spacing: 0.1em;
    color: var(--muted-2);
  }
  .iconbtn {
    border: 2px solid var(--ink);
    background: #fff;
    border-radius: 10px;
    width: 34px;
    height: 34px;
    cursor: pointer;
    font-size: 15px;
  }
  .iconbtn.danger {
    color: var(--bad);
  }
  .nameedit {
    font-size: 22px;
    font-weight: 800;
    padding: 6px 10px;
    border: 2px solid var(--ink);
    border-radius: 10px;
  }
  .mini {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    font-weight: 700;
    padding: 9px 12px;
    border: 2px solid var(--ink);
    border-radius: 10px;
    background: var(--grape);
    color: #fff;
    cursor: pointer;
  }
  .mini.ghost {
    background: #fff;
    color: var(--ink);
  }

  .stripnote {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--muted-2);
    margin-bottom: 8px;
  }
  .strip {
    display: flex;
    gap: 14px;
    overflow-x: auto;
    padding: 6px 2px 16px;
    scroll-snap-type: x mandatory;
    -webkit-overflow-scrolling: touch;
  }
  .thumb {
    scroll-snap-align: start;
    flex: 0 0 auto;
    width: 148px;
    position: relative;
  }
  .thumb-link {
    display: block;
    text-decoration: none;
    color: var(--ink);
  }
  .thumb-img {
    position: relative;
    width: 148px;
    height: 200px;
    border: 3px solid var(--ink);
    border-radius: 16px;
    overflow: hidden;
    background: var(--sky);
    box-shadow: 0 5px 0 var(--ink);
    transition: transform 0.1s ease;
  }
  .thumb-link:hover .thumb-img {
    transform: translateY(-3px);
  }
  .thumb-img img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
  .open-hint {
    position: absolute;
    left: 6px;
    bottom: 6px;
    background: var(--ink);
    color: #fff;
    border-radius: 8px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 9px;
    letter-spacing: 0.08em;
    padding: 3px 6px;
    opacity: 0;
    transition: opacity 0.1s ease;
  }
  .thumb-link:hover .open-hint {
    opacity: 1;
  }
  .badge {
    position: absolute;
    right: 6px;
    bottom: 6px;
    background: #fff;
    border: 2px solid var(--ink);
    border-radius: 8px;
    font-size: 12px;
    padding: 1px 5px;
  }
  .thumb-rm {
    position: absolute;
    top: -8px;
    right: -8px;
    width: 26px;
    height: 26px;
    border-radius: 50%;
    border: 2px solid var(--ink);
    background: #fff;
    color: var(--bad);
    font-weight: 700;
    cursor: pointer;
    line-height: 1;
    box-shadow: 0 2px 0 var(--ink);
  }
  .thumb-title {
    font-size: 12px;
    font-weight: 700;
    line-height: 1.25;
    margin-top: 8px;
    display: -webkit-box;
    -webkit-line-clamp: 3;
    line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
  .empty {
    border: 2px dashed var(--muted-2);
    border-radius: 16px;
    padding: 28px;
    color: var(--muted);
  }
  .empty a {
    color: var(--grape);
    font-weight: 700;
  }
  .msg {
    color: var(--muted);
    padding: 20px 0;
  }
  .msg.err {
    color: var(--bad);
  }
  .link {
    background: none;
    border: none;
    color: var(--grape);
    font: inherit;
    text-decoration: underline;
    cursor: pointer;
    padding: 0;
  }
</style>
