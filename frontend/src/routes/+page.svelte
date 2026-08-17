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
    sendContact,
    type CardModel
  } from '$lib/api';

  let addOpen = $state(false);
  let aboutOpen = $state(false);

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

  // Contact modal
  let contactOpen = $state(false);
  let contactMessage = $state('');
  let contactEmail = $state('');
  let contactHp = $state(''); // honeypot
  let contactSending = $state(false);
  let contactSent = $state(false);
  let contactError = $state<string | null>(null);

  function openContact() {
    contactOpen = true;
    contactSent = false;
    contactError = null;
  }
  function closeContact() {
    contactOpen = false;
    contactMessage = '';
    contactEmail = '';
    contactError = null;
  }
  async function submitContact() {
    contactError = null;
    if (contactMessage.trim().length < 3) {
      contactError = 'Please enter a message.';
      return;
    }
    contactSending = true;
    try {
      await sendContact({
        message: contactMessage.trim(),
        from_email: contactEmail.trim() || undefined,
        website: contactHp
      });
      contactSent = true;
    } catch (e) {
      contactError = (e as Error).message;
    } finally {
      contactSending = false;
    }
  }

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
    if (location.hash === '#contact') openContact();
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

<footer class="foot">
  <button class="contact-link" onclick={() => (aboutOpen = true)}>About</button>
  <span class="foot-sep">·</span>
  <button class="contact-link" onclick={openContact}>Contact us</button>
</footer>

{#if contactOpen}
  <div
    class="overlay"
    role="presentation"
    onclick={(e) => {
      if (e.target === e.currentTarget) closeContact();
    }}
  >
    <div class="dialog" role="dialog" aria-modal="true" aria-label="Contact the developer">
      {#if contactSent}
        <h3>Message sent 🎉</h3>
        <p class="note">Thanks for getting in touch — we’ll get back to you if you left an email.</p>
        <div class="dialog-actions">
          <button class="mbtn" onclick={closeContact}>Close</button>
        </div>
      {:else}
        <h3>Contact us</h3>
        <p class="note">Feedback, a bug, or just saying hello? Send the developer a message.</p>
        <label>
          Your email <span class="opt">(optional, so we can reply)</span>
          <input type="email" bind:value={contactEmail} placeholder="you@example.com" />
        </label>
        <label>
          Message
          <textarea bind:value={contactMessage} rows="5" placeholder="What’s on your mind?"></textarea>
        </label>
        <input
          class="hp"
          tabindex="-1"
          autocomplete="off"
          aria-hidden="true"
          bind:value={contactHp}
          placeholder="Leave this empty"
        />
        {#if contactError}<div class="derr">{contactError}</div>{/if}
        <div class="dialog-actions">
          <button class="mbtn" onclick={submitContact} disabled={contactSending}>
            {contactSending ? 'Sending…' : 'Send'}
          </button>
          <button class="mbtn ghost" onclick={closeContact}>Cancel</button>
        </div>
      {/if}
    </div>
  </div>
{/if}

{#if aboutOpen}
  <div
    class="overlay"
    role="presentation"
    onclick={(e) => {
      if (e.target === e.currentTarget) aboutOpen = false;
    }}
  >
    <div class="dialog" role="dialog" aria-modal="true" aria-label="About Paper Heroes">
      <h3>About Paper Heroes</h3>
      <p class="note">
        Paper Heroes deals you <strong>one recently-published medical paper at random</strong>,
        drawn from a curated set of journals over the last 30 days. Each paper is summarised and
        critically appraised by AI and shown as a comic-book <strong>trading card</strong> — with an
        AI-generated hero (for beneficial findings) or villain (for harms) illustrating the topic.
      </p>
      <p class="note">
        Registered practitioners can add a reflection to the downloadable PDF. Premium members can
        save cards into <strong>Card Decks</strong> and keep a reflection on the back of each card.
      </p>
      <p class="note caveat-note">
        ⚠ AI-generated summaries, appraisals and illustrations can be wrong — always verify against
        the original article before making any clinical decision.
      </p>
      <div class="dialog-actions">
        <button class="mbtn" onclick={() => (aboutOpen = false)}>Close</button>
      </div>
    </div>
  </div>
{/if}

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

  /* footer contact link */
  .foot {
    text-align: center;
    padding: 26px 0 6px;
    margin-top: 8px;
  }
  .contact-link {
    background: none;
    border: none;
    cursor: pointer;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--muted-2);
    padding: 6px 8px;
  }
  .contact-link:hover {
    color: var(--ink);
    text-decoration: underline;
  }
  .foot-sep {
    color: var(--muted-2);
    font-size: 11px;
  }
  .caveat-note {
    color: var(--warn);
  }

  /* contact + about modal */
  .overlay {
    position: fixed;
    inset: 0;
    z-index: 60;
    background: rgba(42, 35, 64, 0.55);
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 20px;
  }
  .dialog {
    background: #fff;
    border: 3px solid var(--ink);
    border-radius: 22px;
    box-shadow: 0 14px 0 rgba(42, 35, 64, 0.18);
    padding: 24px;
    width: min(460px, 94vw);
  }
  .dialog h3 {
    font-size: 22px;
    font-weight: 800;
    margin-bottom: 6px;
  }
  .dialog .note {
    color: var(--muted);
    font-size: 13px;
    margin-bottom: 16px;
  }
  .dialog label {
    display: block;
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--muted);
    margin-bottom: 14px;
  }
  .dialog label .opt {
    text-transform: none;
    letter-spacing: 0;
  }
  .dialog input,
  .dialog textarea {
    display: block;
    width: 100%;
    margin-top: 6px;
    background: var(--face);
    color: var(--ink);
    border: 2px solid var(--ink);
    border-radius: 12px;
    padding: 10px 12px;
    font-size: 14px;
    font-family: 'Plus Jakarta Sans', sans-serif;
  }
  .dialog textarea {
    resize: vertical;
  }
  .dialog .hp {
    position: absolute;
    left: -9999px;
    width: 1px;
    height: 1px;
    opacity: 0;
  }
  .derr {
    color: var(--bad);
    font-size: 12.5px;
    margin-bottom: 8px;
  }
  .dialog-actions {
    display: flex;
    gap: 10px;
    margin-top: 4px;
  }
  .mbtn {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-weight: 800;
    font-size: 14px;
    background: var(--grape);
    color: #fff;
    border: 2px solid var(--ink);
    border-radius: 12px;
    padding: 11px 20px;
    cursor: pointer;
    box-shadow: 0 4px 0 var(--ink);
  }
  .mbtn:active {
    transform: translateY(2px);
    box-shadow: 0 2px 0 var(--ink);
  }
  .mbtn:disabled {
    opacity: 0.6;
    cursor: default;
  }
  .mbtn.ghost {
    background: #fff;
    color: var(--ink);
    box-shadow: none;
  }
</style>
