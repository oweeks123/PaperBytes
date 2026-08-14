<script lang="ts">
  import type { CardModel, Tone } from '$lib/api';

  let { card }: { card: CardModel } = $props();

  const pipCls: Record<Tone, string> = { ink: 'f', good: 'g', warn: 'a', bad: 'r' };
  const SIX = [0, 1, 2, 3, 4, 5];
</script>

<div class="card">
  <div class="face">
    <div class="hdr">
      <h2>{card.title}</h2>
      <div class="gem"><b>{card.levelOfEvidence}</b><i>CEBM</i></div>
    </div>

    <div class="tags">
      {#if card.fresh}<span class="new">Freshly appraised</span>{/if}
      {#if card.mock}<span class="warnt">Mock — no AI credits</span>{/if}
      {#each card.specialties as s}<span>{s}</span>{/each}
      {#each card.warnings as w}<span class="warnt">{w}</span>{/each}
    </div>

    <div class="typeline">
      <span>{card.design}{card.specialties[0] ? ' — ' + card.specialties[0] : ''}</span>
      <span>PMID {card.pmid}</span>
    </div>

    <div class="rules">
      {#each card.summaryParagraphs as p}<p>{p}</p>{/each}
    </div>

    <div class="grid2">
      <div class="blk">
        <h4>Stat block</h4>
        {#each card.pips as s}
          <div class="st">
            <b>{s.label}</b>
            <div class="pips">
              {#each SIX as i}<i class={i < s.filled ? pipCls[s.tone] : ''}></i>{/each}
            </div>
            <u>{s.value}</u>
          </div>
        {/each}
      </div>
      <div class="blk">
        <h4>Appraisal</h4>
        <dl class="pico">
          {#each card.appraisalRows as r}
            <dt>{r.label}</dt>
            <dd class:soft={r.soft}>{r.value}</dd>
          {/each}
        </dl>
      </div>
    </div>

    {#if card.limitations}
      <div class="flavour">
        <b>Limitations — printed on every card</b>“{card.limitations}”
      </div>
    {/if}

    <div class="foot2">
      <span>{card.journal}{card.date ? ' · ' + card.date : ''}{card.authors ? ' · ' + card.authors : ''}</span>
      <span>{#if card.doi}DOI {card.doi}{/if}</span>
    </div>
  </div>
</div>

<style>
  .card {
    border-radius: 16px;
    padding: 6px;
    background: linear-gradient(160deg, var(--frame-top), var(--frame-bottom));
    box-shadow: 0 18px 44px rgba(0, 0, 0, 0.45);
  }
  .face {
    background: var(--card);
    border-radius: 13px;
    color: var(--ink);
    overflow: hidden;
  }
  .hdr {
    display: flex;
    align-items: flex-start;
    gap: 16px;
    padding: 16px 20px 12px;
  }
  .hdr h2 {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 35px;
    line-height: 0.97;
    letter-spacing: 0.01em;
    flex: 1;
  }
  .gem {
    width: 54px;
    height: 54px;
    border-radius: 50%;
    flex: none;
    background: var(--accent);
    box-shadow: inset 0 0 0 2px rgba(255, 255, 255, 0.25), 0 2px 6px rgba(0, 0, 0, 0.3);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    line-height: 1;
    overflow: hidden; /* defensive: never let a long level code spill out */
    padding: 2px;
  }
  .gem b {
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .gem b {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 24px;
    color: #fff;
  }
  .gem i {
    font-family: 'JetBrains Mono', monospace;
    font-size: 6px;
    letter-spacing: 0.1em;
    font-style: normal;
    color: rgba(255, 255, 255, 0.72);
    margin-top: 1px;
  }
  .tags {
    display: flex;
    gap: 7px;
    padding: 0 20px 12px;
    flex-wrap: wrap;
  }
  .tags span {
    font-family: 'JetBrains Mono', monospace;
    font-size: 9px;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    border: 1px solid rgba(22, 28, 40, 0.3);
    padding: 4px 8px;
    border-radius: 4px;
    color: #3f4859;
  }
  .tags .new {
    background: var(--ink);
    color: var(--card);
    border-color: var(--ink);
  }
  .tags .warnt {
    border-color: var(--amber);
    color: #8a5a12;
    background: rgba(217, 146, 47, 0.14);
  }
  .typeline {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin: 0 20px;
    padding: 12px 0 10px;
    border-top: 1px solid rgba(22, 28, 40, 0.2);
    border-bottom: 1px solid rgba(22, 28, 40, 0.2);
    color: #3b4453;
    display: flex;
    justify-content: space-between;
    gap: 12px;
  }
  .rules {
    margin: 12px 20px 0;
    font-size: 14.5px;
    line-height: 1.58;
    color: #232a38;
  }
  .rules p {
    margin-bottom: 9px;
  }
  .grid2 {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0 26px;
    margin: 14px 20px 0;
    padding-top: 13px;
    border-top: 1px solid rgba(22, 28, 40, 0.2);
  }
  .blk h4 {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 15px;
    letter-spacing: 0.14em;
    color: var(--muted);
    margin-bottom: 9px;
  }
  .st {
    display: flex;
    align-items: center;
    gap: 9px;
    margin-bottom: 7px;
  }
  .st b {
    font-family: 'JetBrains Mono', monospace;
    font-size: 8.5px;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--muted);
    width: 84px;
    font-weight: 400;
    white-space: nowrap;
  }
  .pips {
    display: flex;
    gap: 2.5px;
    flex: 1;
  }
  .pips i {
    height: 9px;
    flex: 1;
    background: #dbd4c3;
    border-radius: 1px;
  }
  .pips i.f {
    background: var(--ink);
  }
  .pips i.g {
    background: var(--green);
  }
  .pips i.r {
    background: var(--red);
  }
  .pips i.a {
    background: var(--amber);
  }
  .st u {
    font-family: 'JetBrains Mono', monospace;
    font-size: 9px;
    text-decoration: none;
    width: 110px;
    text-align: right;
    font-weight: 700;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .pico dt {
    font-family: 'JetBrains Mono', monospace;
    font-size: 8.5px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--muted);
  }
  .pico dd {
    font-size: 13px;
    line-height: 1.4;
    margin: 1px 0 8px;
    font-weight: 600;
  }
  .pico dd.soft {
    font-weight: 400;
    color: #4a5261;
  }
  .flavour {
    margin: 12px 20px 0;
    font-size: 12.5px;
    font-style: italic;
    color: #565e6e;
    line-height: 1.5;
    border-top: 1px dashed rgba(22, 28, 40, 0.28);
    padding-top: 10px;
  }
  .flavour b {
    font-style: normal;
    font-family: 'JetBrains Mono', monospace;
    font-size: 8.5px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--amber);
    display: block;
    margin-bottom: 4px;
  }
  .foot2 {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 8.5px;
    letter-spacing: 0.06em;
    color: var(--muted);
    padding: 12px 20px;
  }

  @media (max-width: 900px) {
    .card {
      padding: 6px;
      border-radius: 15px;
    }
    .hdr {
      padding: 13px 14px 9px;
      gap: 10px;
    }
    .hdr h2 {
      font-size: 25px;
    }
    .gem {
      width: 46px;
      height: 46px;
    }
    .gem b {
      font-size: 21px;
    }
    .tags {
      padding: 0 14px 10px;
    }
    .typeline {
      margin: 0 14px;
      font-size: 8.5px;
    }
    .rules {
      margin: 11px 14px 0;
      font-size: 13.5px;
    }
    .grid2 {
      grid-template-columns: 1fr;
      margin: 12px 14px 0;
      gap: 14px;
    }
    .foot2 {
      padding: 11px 14px;
      font-size: 7.5px;
      flex-direction: column;
      gap: 3px;
    }
    .flavour {
      margin: 11px 14px 0;
    }
  }
</style>
