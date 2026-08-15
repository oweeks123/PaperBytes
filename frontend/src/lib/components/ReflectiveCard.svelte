<script lang="ts">
  import EvidenceCard from './EvidenceCard.svelte';
  import { setReflection, type CardModel } from '$lib/api';

  let {
    card,
    pmid,
    text = $bindable(''),
    canSave = false
  }: {
    card: CardModel;
    pmid: string;
    text?: string;
    canSave?: boolean; // premium: reflection is stored; otherwise it's PDF-only (transient)
  } = $props();

  let flipped = $state(false);
  let busy = $state(false);
  let saved = $state(false);

  async function save() {
    busy = true;
    saved = false;
    try {
      await setReflection(pmid, text);
      saved = true;
    } finally {
      busy = false;
    }
  }
</script>

<div class="wrap">
  <div class="flip" class:flipped>
    <div class="face front" aria-hidden={flipped}>
      <EvidenceCard {card} />
    </div>
    <div class="face back" aria-hidden={!flipped}>
      <div class="backinner">
        <div class="bhead">
          <div class="btag">Reflection</div>
          <div class="bhead-actions">
            {#if canSave}
              {#if saved}<span class="ok">Saved ✓</span>{/if}
              <button class="mbtn" onclick={save} disabled={busy}>
                {busy ? 'Saving…' : 'Save'}
              </button>
            {/if}
            <button class="mbtn ghost" onclick={() => (flipped = false)}>↩ Flip to front</button>
          </div>
        </div>
        <div class="btitle">{card.title}</div>
        <p class="bnote">
          {#if canSave}
            Saved to your account, shared across your decks — and added to your PDF.
          {:else}
            Added to your PDF when you download it. Not saved (clears when you leave).
          {/if}
        </p>
        <textarea
          bind:value={text}
          placeholder="What did you take from this paper? How might it change your practice?"
        ></textarea>
      </div>
    </div>
  </div>

  {#if !flipped}
    <div class="cardbar">
      <button class="flipbtn" onclick={() => (flipped = true)}>
        {text.trim() ? '📝 View reflection' : '＋ Add reflection'}
      </button>
    </div>
  {/if}
</div>

<style>
  .wrap {
    perspective: 2200px;
  }
  .flip {
    position: relative;
    transform-style: preserve-3d;
    transition: transform 0.6s cubic-bezier(0.4, 0.15, 0.2, 1);
  }
  .flip.flipped {
    transform: rotateY(180deg);
  }
  .face {
    backface-visibility: hidden;
    -webkit-backface-visibility: hidden;
  }
  .face.front {
    position: relative;
  }
  /* Back overlays the front and occupies the same box (front sets the height). */
  .face.back {
    position: absolute;
    inset: 0;
    transform: rotateY(180deg);
    display: flex;
  }
  .backinner {
    flex: 1;
    display: flex;
    flex-direction: column;
    background: var(--face);
    border: 3px solid var(--ink);
    border-radius: 22px;
    box-shadow: 0 8px 0 var(--ink);
    padding: 22px;
  }
  .bhead {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
  }
  .bhead-actions {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .btag {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    font-weight: 700;
    background: var(--grape);
    color: #fff;
    padding: 5px 10px;
    border-radius: 8px;
  }
  .btitle {
    font-weight: 800;
    font-size: 16px;
    line-height: 1.25;
    margin: 12px 0 10px;
  }
  textarea {
    /* Fills the writing surface below the controls (which sit at the top). */
    flex: 1;
    min-height: 200px;
    width: 100%;
    resize: none;
    padding: 13px;
    border: 2px solid var(--ink);
    border-radius: 14px;
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 15px;
    line-height: 1.5;
    background: #fff;
  }
  .bnote {
    font-size: 12px;
    color: var(--muted);
    margin-bottom: 12px;
  }
  .ok {
    color: var(--good);
    font-weight: 700;
    font-size: 13px;
  }
  .cardbar {
    display: flex;
    gap: 10px;
    margin-top: 14px;
    flex-wrap: wrap;
    position: relative; /* keep the buttons above the flip's 3D subtree so taps land */
    z-index: 3;
  }
  .flipbtn {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    font-weight: 700;
    padding: 12px 18px;
    border: 2px solid var(--ink);
    border-radius: 13px;
    background: var(--butter);
    color: var(--butter-ink);
    cursor: pointer;
    box-shadow: 0 4px 0 var(--butter-shadow);
  }
  .mbtn {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    font-weight: 700;
    padding: 12px 16px;
    border: 2px solid var(--ink);
    border-radius: 12px;
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
