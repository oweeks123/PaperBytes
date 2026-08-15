<script lang="ts">
  import { listDecks, createDeck, addCardToDeck, type DeckSummary } from '$lib/api';

  let {
    open = false,
    pmid,
    onclose
  }: { open?: boolean; pmid: string; onclose: () => void } = $props();

  let decks = $state<DeckSummary[] | null>(null);
  let error = $state<string | null>(null);
  let addedTo = $state<Set<number>>(new Set());
  let creating = $state(false);
  let newName = $state('');
  let busy = $state(false);

  // Load decks whenever the modal opens.
  $effect(() => {
    if (open && decks === null) load();
    if (!open) {
      addedTo = new Set();
      creating = false;
      newName = '';
    }
  });

  async function load() {
    error = null;
    try {
      decks = await listDecks();
    } catch (e) {
      error = (e as Error).message;
    }
  }

  async function add(deckId: number) {
    if (busy) return;
    busy = true;
    error = null;
    try {
      await addCardToDeck(deckId, pmid);
      addedTo = new Set([...addedTo, deckId]);
    } catch (e) {
      error = (e as Error).message;
    } finally {
      busy = false;
    }
  }

  async function createAndAdd() {
    const name = newName.trim();
    if (!name || busy) return;
    busy = true;
    error = null;
    try {
      const d = await createDeck(name);
      await addCardToDeck(d.id, pmid);
      decks = [{ id: d.id, name: d.name, card_count: 1, cover_pmids: [pmid], updated_at: null }, ...(decks ?? [])];
      addedTo = new Set([...addedTo, d.id]);
      newName = '';
      creating = false;
    } catch (e) {
      error = (e as Error).message;
    } finally {
      busy = false;
    }
  }
</script>

{#if open}
  <div
    class="overlay"
    role="presentation"
    onclick={(e) => {
      if (e.target === e.currentTarget) onclose();
    }}
  >
    <div class="dialog" role="dialog" aria-modal="true" aria-label="Add card to a deck">
      <h3>Add to deck</h3>
      {#if error}<div class="derr">{error}</div>{/if}

      <div class="list">
        {#if decks === null}
          <div class="muted">Loading…</div>
        {:else}
          {#each decks as d (d.id)}
            <button class="deckrow" onclick={() => add(d.id)} disabled={busy || addedTo.has(d.id)}>
              <span class="dn">{d.name}</span>
              <span class="dc">{addedTo.has(d.id) ? 'Added ✓' : `${d.card_count} cards`}</span>
            </button>
          {/each}
          {#if decks.length === 0 && !creating}
            <div class="muted">No decks yet — create your first below.</div>
          {/if}
        {/if}
      </div>

      {#if creating}
        <div class="createrow">
          <input
            bind:value={newName}
            placeholder="New deck name"
            maxlength="120"
            onkeydown={(e) => e.key === 'Enter' && createAndAdd()}
          />
          <button class="mbtn" onclick={createAndAdd} disabled={busy}>Create & add</button>
        </div>
      {:else}
        <button class="newbtn" onclick={() => (creating = true)}>＋ New deck</button>
      {/if}

      <div class="foot">
        <button class="mbtn ghost" onclick={onclose}>Done</button>
      </div>
    </div>
  </div>
{/if}

<style>
  .overlay {
    position: fixed;
    inset: 0;
    background: rgba(42, 35, 64, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 20px;
    z-index: 60;
  }
  .dialog {
    background: var(--face);
    border: 3px solid var(--ink);
    border-radius: 20px;
    box-shadow: 0 10px 0 var(--ink);
    padding: 22px;
    width: min(440px, 100%);
  }
  h3 {
    font-size: 22px;
    font-weight: 800;
    margin-bottom: 14px;
  }
  .list {
    display: flex;
    flex-direction: column;
    gap: 8px;
    max-height: 46vh;
    overflow-y: auto;
    margin-bottom: 12px;
  }
  .deckrow {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 10px;
    padding: 12px 14px;
    border: 2px solid var(--ink);
    border-radius: 12px;
    background: #fff;
    cursor: pointer;
    font-size: 15px;
  }
  .deckrow:disabled {
    opacity: 0.7;
    cursor: default;
  }
  .dn {
    font-weight: 700;
  }
  .dc {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    letter-spacing: 0.08em;
    color: var(--muted);
  }
  .newbtn {
    width: 100%;
    padding: 11px;
    border: 2px dashed var(--muted-2);
    border-radius: 12px;
    background: #fff;
    color: var(--grape);
    font-weight: 700;
    cursor: pointer;
    margin-bottom: 12px;
  }
  .createrow {
    display: flex;
    gap: 8px;
    margin-bottom: 12px;
  }
  .createrow input {
    flex: 1;
    padding: 10px;
    border: 2px solid var(--ink);
    border-radius: 11px;
    font-size: 14px;
  }
  .muted {
    color: var(--muted);
    font-size: 14px;
    padding: 6px 2px;
  }
  .derr {
    color: var(--bad);
    font-size: 13px;
    margin-bottom: 10px;
  }
  .foot {
    display: flex;
    justify-content: flex-end;
  }
  .mbtn {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    font-weight: 700;
    padding: 11px 15px;
    border: 2px solid var(--ink);
    border-radius: 11px;
    background: var(--grape);
    color: #fff;
    cursor: pointer;
  }
  .mbtn.ghost {
    background: #fff;
    color: var(--ink);
  }
  .mbtn:disabled {
    opacity: 0.6;
    cursor: default;
  }
</style>
