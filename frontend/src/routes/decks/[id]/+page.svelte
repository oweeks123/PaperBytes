<script lang="ts">
  import { page } from '$app/stores';
  import { base } from '$app/paths';
  import { goto } from '$app/navigation';
  import { session } from '$lib/session.svelte';
  import { ui } from '$lib/ui.svelte';
  import {
    getDeck,
    renameDeck,
    deleteDeck,
    removeCardFromDeck,
    type Deck
  } from '$lib/api';
  import ReflectiveCard from '$lib/components/ReflectiveCard.svelte';

  let deck = $state<Deck | null>(null);
  let error = $state<string | null>(null);
  let selected = $state<string | null>(null);
  let editingName = $state(false);
  let nameDraft = $state('');
  let loadedId = $state<number | null>(null);

  const deckId = $derived(Number($page.params.id));
  const selectedCard = $derived(deck?.cards.find((c) => c.pubmed_id === selected) ?? null);

  async function load() {
    error = null;
    deck = null;
    try {
      const d = await getDeck(deckId);
      deck = d;
      selected = d.cards[0]?.pubmed_id ?? null;
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

  async function removeSelected() {
    if (!deck || !selected) return;
    const pmid = selected;
    await removeCardFromDeck(deck.id, pmid);
    deck.cards = deck.cards.filter((c) => c.pubmed_id !== pmid);
    deck.card_count = deck.cards.length;
    selected = deck.cards[0]?.pubmed_id ?? null;
  }

  function onReflection(pmid: string, text: string | null) {
    if (!deck) return;
    deck.cards = deck.cards.map((c) => (c.pubmed_id === pmid ? { ...c, reflection: text } : c));
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
  <div class="msg">Card Decks are a Premium feature. <button class="link" onclick={() => session.upgrade()}>Upgrade</button>.</div>
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
    <!-- Scrollable strip of cards: image + title. Click to open. -->
    <div class="strip" role="listbox" aria-label="Cards in this deck">
      {#each deck.cards as c (c.pubmed_id)}
        <button
          class="thumb"
          class:active={c.pubmed_id === selected}
          role="option"
          aria-selected={c.pubmed_id === selected}
          onclick={() => (selected = c.pubmed_id)}
        >
          <div class="thumb-img">
            <img
              src={c.image_url}
              alt=""
              loading="lazy"
              onerror={(e) => ((e.currentTarget as HTMLImageElement).style.visibility = 'hidden')}
            />
            {#if c.reflection}<span class="badge" title="Has a reflection">📝</span>{/if}
          </div>
          <div class="thumb-title">{c.title}</div>
        </button>
      {/each}
    </div>

    {#if selectedCard}
      {#key selectedCard.pubmed_id}
        <div class="opened">
          <ReflectiveCard
            card={selectedCard}
            onremove={removeSelected}
            onreflection={(t) => onReflection(selectedCard.pubmed_id, t)}
          />
        </div>
      {/key}
    {/if}
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
    background: none;
    border: none;
    cursor: pointer;
    padding: 0;
    text-align: left;
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
  .thumb.active .thumb-img {
    outline: 4px solid var(--grape);
    outline-offset: 2px;
  }
  .thumb:hover .thumb-img {
    transform: translateY(-3px);
  }
  .thumb-img img {
    width: 100%;
    height: 100%;
    object-fit: cover;
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
  .opened {
    max-width: 880px;
    margin-top: 8px;
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
