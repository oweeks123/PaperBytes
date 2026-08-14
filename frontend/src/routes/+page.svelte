<script lang="ts">
  import { onMount } from 'svelte';
  import { fly } from 'svelte/transition';
  import '../app.css';
  import EvidenceCard from '$lib/components/EvidenceCard.svelte';
  import { getRandom, getGeo, toCard, downloadPdf, type CardModel, type Geo } from '$lib/api';

  let card = $state<CardModel | null>(null);
  let geo = $state<Geo | null>(null);
  let loading = $state(true);
  let error = $state<string | null>(null);
  let dealing = $state(false);

  async function deal() {
    dealing = true;
    error = null;
    try {
      card = toCard(await getRandom(30));
    } catch (e) {
      error = (e as Error).message;
    } finally {
      loading = false;
      dealing = false;
    }
  }

  async function pdf() {
    if (card) {
      try {
        await downloadPdf(card.pmid);
      } catch (e) {
        error = (e as Error).message;
      }
    }
  }

  onMount(() => {
    const country = new URLSearchParams(location.search).get('country') ?? undefined;
    getGeo(country)
      .then((g) => (geo = g))
      .catch(() => {});
    deal();
  });
</script>

<div class="bar">
  <div>
    <h1>Today's pull</h1>
    <div class="sub">
      {#if geo}{geo.flag} {geo.country_name.toUpperCase()} ·
      {/if}ONE PAPER, DRAWN AT RANDOM FROM THE LAST 30 DAYS · APPRAISED ONCE, THEN KEPT
    </div>
  </div>
  <button class="deal" onclick={deal} disabled={dealing}>
    {dealing ? 'Dealing…' : 'Deal another card'}
  </button>
</div>

<div class="stage">
  <div class="acts">
    {#if card && !loading}
      <a class="primary" href={card.url} target="_blank" rel="noreferrer">Read on PubMed</a>
      <button onclick={pdf}>Download summary (PDF)</button>
      <div class="hint">Free tier — refresh or “deal” for another card.</div>
    {/if}
  </div>

  <div class="cardwrap">
    {#if loading}
      <div class="msg">Dealing your card… new papers are appraised on the fly (a few seconds).</div>
    {:else if error}
      <div class="msg err">Error: {error}</div>
    {:else if card}
      {#key card.pmid}
        <div in:fly={{ y: 18, duration: 320 }}>
          <EvidenceCard {card} />
        </div>
      {/key}
    {/if}
  </div>

  <div class="rail">
    <div class="ad">
      <span>Advertisement</span>
      <div>Ad slot · 300 × 600</div>
    </div>
  </div>
</div>

<style>
  .bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    margin-bottom: 22px;
  }
  .bar h1 {
    font-size: 40px;
    letter-spacing: -1.2px;
    line-height: 1;
    font-weight: 800;
    color: var(--ink);
  }
  .sub {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    letter-spacing: 0.14em;
    color: var(--muted-2);
    margin-top: 6px;
  }
  .deal {
    font-size: 23px;
    font-weight: 800;
    letter-spacing: -0.3px;
    background: var(--melon);
    color: #fff;
    border: none;
    border-radius: 16px;
    padding: 14px 30px;
    cursor: pointer;
    box-shadow: 0 6px 0 var(--melon-shadow);
    white-space: nowrap;
    transition: transform 0.05s ease, box-shadow 0.05s ease;
  }
  .deal:hover {
    filter: brightness(1.03);
  }
  .deal:active {
    transform: translateY(4px);
    box-shadow: 0 2px 0 var(--melon-shadow);
  }
  .deal:disabled {
    opacity: 0.6;
    cursor: default;
  }

  .stage {
    display: grid;
    grid-template-columns: minmax(170px, 1fr) minmax(0, 880px) minmax(170px, 1fr);
    gap: 30px;
    align-items: start;
  }

  .acts {
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding-top: 4px;
  }
  .acts a,
  .acts button {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    text-decoration: none;
    padding: 13px 15px;
    text-align: center;
    border: 2px solid var(--ink);
    border-radius: 14px;
    color: var(--ink);
    font-weight: 700;
    background: #fff;
    cursor: pointer;
  }
  .acts a.primary {
    background: var(--grape);
    color: #fff;
    border-color: var(--ink);
    box-shadow: 0 4px 0 var(--ink);
  }
  .acts a:active,
  .acts button:active {
    transform: translateY(2px);
  }
  .acts .hint {
    font-family: 'JetBrains Mono', monospace;
    font-size: 8.5px;
    letter-spacing: 0.06em;
    color: var(--muted-2);
    line-height: 1.6;
    padding: 4px 2px;
    text-transform: none;
    text-align: left;
  }

  .cardwrap {
    min-height: 220px;
  }
  .msg {
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    letter-spacing: 0.06em;
    color: var(--muted);
    padding: 40px 0;
    text-align: center;
  }
  .msg.err {
    color: var(--bad);
  }

  .rail {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }
  .ad {
    border: 2px dashed #c9bfe0;
    border-radius: 18px;
    padding: 12px;
    text-align: center;
  }
  .ad span {
    font-family: 'JetBrains Mono', monospace;
    font-size: 8px;
    letter-spacing: 0.2em;
    color: var(--muted-2);
  }
  .ad div {
    margin-top: 8px;
    height: 520px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: 'JetBrains Mono', monospace;
    font-size: 9.5px;
    letter-spacing: 0.12em;
    color: var(--muted-2);
    background: #fff;
    border-radius: 14px;
  }

  @media (max-width: 900px) {
    .bar {
      flex-direction: column;
      align-items: stretch;
      gap: 12px;
    }
    .bar h1 {
      font-size: 30px;
    }
    .deal {
      text-align: center;
      font-size: 19px;
      padding: 14px;
    }
    .stage {
      grid-template-columns: 1fr;
      gap: 18px;
    }
    .stage .acts {
      order: 2;
      flex-direction: row;
      flex-wrap: wrap;
    }
    .stage .cardwrap {
      order: 1;
    }
    .stage .rail {
      order: 3;
    }
    .acts a,
    .acts button {
      flex: 1 1 46%;
    }
    .acts .hint {
      flex: 1 1 100%;
    }
    .ad div {
      height: 250px;
    }
  }
</style>
