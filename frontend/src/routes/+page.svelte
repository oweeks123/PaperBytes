<script lang="ts">
  import { onMount } from 'svelte';
  import { fly } from 'svelte/transition';
  import '../app.css';
  import { base } from '$app/paths';
  import EvidenceCard from '$lib/components/EvidenceCard.svelte';
  import ReflectiveCard from '$lib/components/ReflectiveCard.svelte';
  import CardSkeleton from '$lib/components/CardSkeleton.svelte';
  import AddToDeckModal from '$lib/components/AddToDeckModal.svelte';
  import { session } from '$lib/session.svelte';
  import {
    getRandom,
    getCard,
    getReflection,
    toCard,
    downloadPdf,
    type CardModel
  } from '$lib/api';

  let addOpen = $state(false);

  let card = $state<CardModel | null>(null);
  let loading = $state(true);
  let error = $state<string | null>(null);
  let dealing = $state(false);

  // Reflection text bound to the card flip (any signed-in user). For premium it's
  // prefilled from the stored reflection and saved back; for registered it's a
  // transient value included only in the downloaded PDF.
  let reflectionText = $state('');
  let reflectionLoadedFor = $state<string | null>(null);

  $effect(() => {
    const c = card;
    if (!session.isPaid || !c || reflectionLoadedFor === c.pmid) return;
    const pmid = c.pmid;
    let cancelled = false;
    getReflection(pmid)
      .then((r) => {
        if (!cancelled) reflectionText = r.reflection ?? '';
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) reflectionLoadedFor = pmid;
      });
    return () => {
      cancelled = true;
    };
  });

  function resetReflection() {
    reflectionText = '';
    reflectionLoadedFor = null;
  }

  async function deal() {
    dealing = true;
    error = null;
    try {
      resetReflection();
      card = toCard(await getRandom(30));
      // Drop any ?pmid= so a refresh deals a fresh random card again.
      if (typeof history !== 'undefined') history.replaceState(null, '', `${base}/`);
    } catch (e) {
      error = (e as Error).message;
    } finally {
      loading = false;
      dealing = false;
    }
  }

  // Open a specific, already-analysed card (deep link from a deck: /ui/?pmid=…).
  async function openPmid(pmid: string) {
    error = null;
    try {
      resetReflection();
      card = toCard(await getCard(pmid));
    } catch (e) {
      error = (e as Error).message;
    } finally {
      loading = false;
    }
  }

  async function pdf() {
    if (card) {
      try {
        // Include the current reflection (transient for registered, stored for premium).
        await downloadPdf(card.pmid, reflectionText.trim() || null);
      } catch (e) {
        error = (e as Error).message;
      }
    }
  }

  onMount(() => {
    const pmid = new URL(location.href).searchParams.get('pmid');
    if (pmid) openPmid(pmid);
    else deal();
    // Request an ad into the AdSense unit. The loader lives in app.html; if it
    // hasn't finished loading yet, push() queues into the adsbygoogle array and
    // runs once it does. Wrapped so an ad blocker or failed load can never break
    // the page — the labelled box just stays empty as a graceful fallback.
    try {
      const w = window as unknown as { adsbygoogle?: unknown[] };
      (w.adsbygoogle = w.adsbygoogle || []).push({});
    } catch {
      /* AdSense unavailable — leave the slot empty. */
    }
  });
</script>

<div class="bar">
  <div>
    <p class="sub">ONE PAPER, DRAWN AT RANDOM FROM THE LAST 30 DAYS · APPRAISED BY AI.</p>
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
      {#if session.isPaid}
        <button class="deckadd" onclick={() => (addOpen = true)}>＋ Add to deck</button>
      {/if}
      <div class="hint">
        {#if session.isPaid}
          Premium — add to a deck; your reflection is saved and in the PDF.
        {:else if session.isSignedIn}
          Registered — add a reflection; it’s included in your PDF.
        {:else}
          Refresh or “deal” for another card.
        {/if}
      </div>
    {/if}
  </div>

  <div class="cardwrap">
    {#if loading}
      <CardSkeleton />
    {:else if error}
      <div class="errcard" role="alert">
        <div class="erricon">⚠</div>
        <h3>Couldn’t deal a card</h3>
        <p class="errmsg">{error}</p>
        <button class="retry" onclick={deal} disabled={dealing}>
          {dealing ? 'Trying…' : 'Try again'}
        </button>
      </div>
    {:else if card}
      {#if session.isSignedIn}
        {#key card.pmid}
          <div in:fly={{ y: 18, duration: 320 }}>
            <ReflectiveCard {card} pmid={card.pmid} bind:text={reflectionText} canSave={session.isPaid} />
          </div>
        {/key}
      {:else}
        {#key card.pmid}
          <div in:fly={{ y: 18, duration: 320 }}>
            <EvidenceCard {card} />
          </div>
        {/key}
      {/if}
    {/if}
  </div>

  <div class="rail">
    <div class="ad">
      <span>Advertisement</span>
      <ins
        class="adsbygoogle"
        style="display:block"
        data-ad-client="ca-pub-2095036427198725"
        data-ad-slot="3551146009"
        data-ad-format="auto"
        data-full-width-responsive="true"
      ></ins>
    </div>
  </div>
</div>

{#if card}
  <AddToDeckModal open={addOpen} pmid={card.pmid} onclose={() => (addOpen = false)} />
{/if}

<style>
  .deckadd {
    background: var(--grape) !important;
    color: #fff !important;
  }
  .bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    margin-bottom: 22px;
  }
  /* The tagline now leads the page (the brand lives in the top nav). */
  .sub {
    font-family: 'JetBrains Mono', monospace;
    font-size: 16px;
    line-height: 1.55;
    letter-spacing: 0.06em;
    font-weight: 700;
    color: var(--ink);
    max-width: 640px;
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
  .errcard {
    border: 3px solid var(--ink);
    border-radius: 22px;
    box-shadow: 0 8px 0 var(--ink);
    background: var(--face);
    padding: 40px 28px;
    text-align: center;
  }
  .erricon {
    width: 54px;
    height: 54px;
    margin: 0 auto 14px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 24px;
    border-radius: 50%;
    background: #fff;
    border: 2px solid var(--ink);
    color: var(--bad);
  }
  .errcard h3 {
    font-size: 20px;
    font-weight: 800;
    margin-bottom: 8px;
  }
  .errmsg {
    color: var(--muted);
    font-size: 14px;
    margin-bottom: 18px;
    word-break: break-word;
  }
  .retry {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    font-weight: 700;
    padding: 12px 20px;
    border: 2px solid var(--ink);
    border-radius: 13px;
    background: var(--grape);
    color: #fff;
    cursor: pointer;
    box-shadow: 0 4px 0 var(--grape-shadow);
  }
  .retry:disabled {
    opacity: 0.6;
    cursor: default;
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
  .ad ins.adsbygoogle {
    display: block;
    margin-top: 8px;
    min-height: 520px;
    background: #fff;
    border-radius: 14px;
  }

  @media (max-width: 900px) {
    .bar {
      flex-direction: column;
      align-items: stretch;
      gap: 12px;
    }
    .sub {
      font-size: 14px;
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
    .ad ins.adsbygoogle {
      min-height: 250px;
    }
  }
</style>
