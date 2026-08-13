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
      <div>Google AdSense<br />(placeholder)<br />300 × 600</div>
    </div>
  </div>
</div>

<style>
  .bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    margin-bottom: 24px;
  }
  .bar h1 {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 38px;
    letter-spacing: 0.03em;
    line-height: 1;
    background: linear-gradient(92deg, var(--h1), var(--h2) 50%, var(--h3));
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
  }
  .sub {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    letter-spacing: 0.14em;
    color: #8296b5;
    margin-top: 5px;
  }
  .deal {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 23px;
    letter-spacing: 0.07em;
    background: linear-gradient(92deg, var(--h1), var(--h2));
    color: #0f1b30;
    padding: 14px 30px;
    border: none;
    border-radius: 11px;
    cursor: pointer;
    box-shadow: 0 6px 22px rgba(140, 120, 240, 0.35);
    white-space: nowrap;
  }
  .deal:disabled {
    opacity: 0.6;
    cursor: default;
  }

  .stage {
    display: grid;
    grid-template-columns: minmax(160px, 1fr) minmax(0, 780px) minmax(160px, 1fr);
    align-items: start;
    gap: 34px;
  }

  .acts {
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding-top: 6px;
  }
  .acts a,
  .acts button {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    text-decoration: none;
    color: #c6d5ec;
    background: transparent;
    border: 1px solid #2e4468;
    border-radius: 11px;
    padding: 13px 15px;
    text-align: center;
    cursor: pointer;
  }
  .acts a.primary {
    background: #eaf0fa;
    color: var(--felt);
    border-color: #eaf0fa;
    font-weight: 700;
  }
  .acts .hint {
    font-family: 'JetBrains Mono', monospace;
    font-size: 8.5px;
    letter-spacing: 0.06em;
    color: #6f86aa;
    line-height: 1.6;
    padding: 4px 2px;
  }

  .cardwrap {
    min-height: 200px;
  }
  .msg {
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    letter-spacing: 0.06em;
    color: #8fa2be;
    padding: 40px 0;
    text-align: center;
  }
  .msg.err {
    color: #f5a8c8;
  }

  .rail {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }
  .ad {
    border: 1px dashed #33507a;
    border-radius: 14px;
    padding: 12px;
    text-align: center;
  }
  .ad span {
    font-family: 'JetBrains Mono', monospace;
    font-size: 8px;
    letter-spacing: 0.2em;
    color: #6f86aa;
  }
  .ad div {
    margin-top: 8px;
    height: 520px;
    border-radius: 9px;
    background: rgba(255, 255, 255, 0.04);
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: 'JetBrains Mono', monospace;
    font-size: 9.5px;
    letter-spacing: 0.12em;
    color: #7f93b4;
    text-align: center;
    line-height: 2;
  }

  @media (max-width: 900px) {
    .bar {
      flex-direction: column;
      align-items: stretch;
      gap: 14px;
      margin-bottom: 16px;
    }
    .bar h1 {
      font-size: 30px;
    }
    .deal {
      text-align: center;
      font-size: 20px;
      padding: 15px;
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
    .ad div {
      height: 250px;
    }
  }
</style>
