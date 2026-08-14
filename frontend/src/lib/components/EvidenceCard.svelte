<script lang="ts">
  import type { CardModel, Tone } from '$lib/api';

  let { card }: { card: CardModel } = $props();

  const toneCls: Record<Tone, string> = { ink: '', good: 'g', warn: 'w', bad: 'b' };
  const SIX = [0, 1, 2, 3, 4, 5];

  // Real AI illustration fades in over the placeholder once it loads (or has been
  // generated + cached). Stays on the placeholder if the endpoint 404s (no key).
  let imgOk = $state(false);
</script>

<div class="card">
  <div class="face">
    <div class="hdr">
      <h2>{card.title}</h2>
      <div class="gem"><b>{card.levelOfEvidence}</b><i>CEBM</i></div>
    </div>

    <div class="tags">
      {#if card.fresh}<span class="new">Freshly appraised</span>{/if}
      {#if card.mock}<span class="mock">Mock — no AI credits</span>{/if}
      {#each card.specialties as s}<span>{s}</span>{/each}
    </div>

    <div class="artwrap">
      <svg class="art" viewBox="0 0 560 200" xmlns="http://www.w3.org/2000/svg" role="img"
           aria-label="Decorative illustration placeholder">
        <rect width="560" height="200" fill="#9be8ff" />
        <circle cx="86" cy="58" r="48" fill="#5bd6a6" opacity="0.55" />
        <circle cx="486" cy="150" r="64" fill="#7b5be8" opacity="0.26" />
        <rect x="0" y="162" width="560" height="38" fill="#5bd6a6" opacity="0.45" />
        <rect x="250" y="70" width="60" height="76" rx="8" fill="#fffdf7"
              stroke="#2a2340" stroke-width="4" />
        <line x1="262" y1="90" x2="298" y2="90" stroke="#2a2340" stroke-width="4" stroke-linecap="round" />
        <line x1="262" y1="104" x2="298" y2="104" stroke="#2a2340" stroke-width="4" stroke-linecap="round" />
        <line x1="262" y1="118" x2="286" y2="118" stroke="#2a2340" stroke-width="4" stroke-linecap="round" />
        <circle cx="330" cy="64" r="9" fill="#ffc94d" stroke="#2a2340" stroke-width="3" />
        <circle cx="214" cy="132" r="7" fill="#ff5f7e" stroke="#2a2340" stroke-width="3" />
      </svg>
      <img
        class="art-img"
        class:show={imgOk}
        src={`/articles/${encodeURIComponent(card.pmid)}/image`}
        alt="AI illustration generated from the paper title"
        onload={() => (imgOk = true)}
        onerror={() => (imgOk = false)}
      />
      <div class="aitag">AI illustration · {imgOk ? 'from the title' : 'placeholder'}</div>
    </div>

    <div class="typeline">
      <span>{card.design}{card.specialties[0] ? ' — ' + card.specialties[0] : ''}</span>
      <span>PMID {card.pmid}</span>
    </div>

    <div class="rules">
      {#each card.summaryParagraphs as p}<p>{p}</p>{/each}
    </div>

    {#if card.stats.length}
      <div class="sect">
        <h4>Reported statistics</h4>
        <div class="nums">
          {#each card.stats as o}
            <div class="num">
              <div class="num-name">{o.name}</div>
              <div class="num-vals">
                {#if o.measure}<span class="meas">{o.measure}</span>{/if}
                {#if o.value}<b>{o.value}</b>{/if}
                {#if o.ci}<span class="mut">95% CI {o.ci}</span>{/if}
                {#if o.p}<span class="mut">p {o.p}</span>{/if}
                {#if o.sig === 'sig'}
                  <span class="sig sig-y">Significant</span>
                {:else if o.sig === 'ns'}
                  <span class="sig sig-n">Not significant</span>
                {/if}
              </div>
            </div>
          {/each}
        </div>
        {#if card.significanceComment}
          <div class="sig-comment">{card.significanceComment}</div>
        {/if}
      </div>
    {/if}

    <div class="sect">
      <h4>Stat block</h4>
      <table>
        <tbody>
          {#each card.pips as s}
            <tr>
              <th>{s.label}</th>
              <td class="bar">
                {#each SIX as i}<i class={i < s.filled ? 'on ' + toneCls[s.tone] : ''}></i>{/each}
              </td>
              <td class="val">{s.value}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>

    <div class="sect">
      <h4>Appraisal</h4>
      <dl class="pico">
        {#each card.appraisalRows as r}
          <div class:soft={r.soft}>
            <dt>{r.label}</dt>
            <dd>{r.value}</dd>
          </div>
        {/each}
      </dl>
    </div>

    {#if card.limitations}
      <div class="flavour">
        <b>Limitations — printed on every card</b>“{card.limitations}”
      </div>
    {/if}

    <div class="foot2">
      <span>{[card.journal, card.date, card.authors].filter(Boolean).join(' · ').toUpperCase()}</span>
      <span>{#if card.doi}DOI {card.doi.toUpperCase()}{/if}</span>
    </div>
  </div>
</div>

<style>
  .card {
    border-radius: 30px;
    padding: 12px;
    background: var(--card);
    box-shadow: 0 18px 40px rgba(42, 35, 64, 0.18), inset 0 0 0 3px var(--ink);
  }
  .face {
    background: var(--face);
    color: var(--ink);
    overflow: hidden;
    border-radius: 20px;
  }
  .hdr {
    display: flex;
    align-items: flex-start;
    gap: 16px;
    padding: 18px 22px 12px;
  }
  .hdr h2 {
    font-size: 27px;
    line-height: 1.18;
    letter-spacing: -0.7px;
    flex: 1;
    font-weight: 800;
  }
  .gem {
    width: 62px;
    height: 62px;
    flex: none;
    border-radius: 18px;
    background: var(--butter);
    box-shadow: 0 4px 0 var(--butter-shadow);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    line-height: 1;
    overflow: hidden;
    padding: 3px;
  }
  .gem b {
    font-size: 27px;
    color: var(--butter-ink);
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .gem i {
    font-family: 'JetBrains Mono', monospace;
    font-size: 6.5px;
    letter-spacing: 0.1em;
    font-style: normal;
    color: var(--butter-ink);
    opacity: 0.75;
    margin-top: 1px;
  }
  .tags {
    display: flex;
    gap: 7px;
    padding: 0 22px 13px;
    flex-wrap: wrap;
  }
  .tags span {
    font-family: 'JetBrains Mono', monospace;
    font-size: 9px;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    padding: 5px 9px;
    border: 2px solid var(--ink);
    border-radius: 20px;
    color: var(--ink);
    font-weight: 700;
  }
  .tags .new {
    background: var(--mint);
    color: var(--mint-ink);
  }
  .tags .mock {
    background: var(--butter);
    color: var(--butter-ink);
  }
  .artwrap {
    position: relative;
    margin: 0 22px;
    border-radius: 16px;
    border: 3px solid var(--ink);
    overflow: hidden;
  }
  .art {
    width: 100%;
    display: block;
  }
  .art-img {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
    opacity: 0;
    transition: opacity 0.4s ease;
  }
  .art-img.show {
    opacity: 1;
  }
  .aitag {
    position: absolute;
    right: 11px;
    bottom: 11px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 8px;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    padding: 5px 8px;
    border-radius: 4px;
    background: rgba(0, 0, 0, 0.32);
    color: #ffffff;
  }
  .typeline {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin: 13px 22px 0;
    padding-bottom: 11px;
    border-bottom: 1px solid var(--line);
    color: var(--muted);
    display: flex;
    justify-content: space-between;
    gap: 12px;
  }
  .rules {
    margin: 13px 22px 0;
    font-size: 14.5px;
    line-height: 1.6;
    color: var(--ink);
  }
  .rules p {
    margin-bottom: 9px;
  }
  .rules :global(b) {
    background: linear-gradient(180deg, transparent 56%, var(--sky) 56%);
    font-weight: 800;
  }
  .sect {
    margin: 16px 22px 0;
    padding-top: 14px;
    border-top: 1px solid var(--line);
  }
  h4 {
    font-size: 13px;
    letter-spacing: 0.1em;
    color: var(--muted);
    margin-bottom: 9px;
    font-weight: 800;
  }

  /* Reported statistics */
  .nums {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .num-name {
    font-size: 12.5px;
    font-weight: 700;
    color: var(--ink);
    line-height: 1.3;
  }
  .num-vals {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 7px;
    margin-top: 4px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: var(--muted);
  }
  .num-vals b {
    color: var(--ink);
    font-weight: 700;
    font-size: 12px;
  }
  .num-vals .meas {
    background: var(--seg-off);
    color: var(--ink);
    border-radius: 5px;
    padding: 2px 6px;
    font-size: 9.5px;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    font-weight: 700;
  }
  .sig {
    border-radius: 20px;
    padding: 2px 9px;
    font-size: 8.5px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    font-weight: 700;
    border: 2px solid;
  }
  .sig-y {
    color: var(--good);
    border-color: var(--good);
    background: rgba(40, 180, 135, 0.12);
  }
  .sig-n {
    color: var(--muted);
    border-color: var(--seg-off);
    background: var(--seg-off);
  }
  .sig-comment {
    margin-top: 12px;
    font-size: 12.5px;
    line-height: 1.5;
    color: var(--ink);
    background: #f3f0fb;
    border-radius: 10px;
    border-left: 4px solid var(--grape);
    padding: 9px 12px;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
  }
  table th {
    text-align: left;
    font-family: 'JetBrains Mono', monospace;
    font-size: 9.5px;
    letter-spacing: 0.09em;
    text-transform: uppercase;
    color: var(--muted);
    font-weight: 700;
    padding: 7px 10px 7px 0;
    width: 160px;
    white-space: nowrap;
  }
  table td.bar {
    padding: 7px 14px 7px 0;
    width: auto;
    white-space: nowrap;
  }
  table td.bar i {
    display: inline-block;
    width: 13.5%;
    height: 11px;
    background: var(--seg-off);
    margin-right: 1.2%;
    border-radius: 6px;
  }
  table td.bar i.on {
    background: var(--grape);
  }
  table td.bar i.on.g {
    background: var(--good);
  }
  table td.bar i.on.w {
    background: var(--warn);
  }
  table td.bar i.on.b {
    background: var(--bad);
  }
  table td.val {
    text-align: right;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11.5px;
    font-weight: 700;
    white-space: nowrap;
    width: 150px;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  table tr {
    border-bottom: 1px solid var(--line);
  }
  table tr:last-child {
    border: 0;
  }
  .pico {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0 26px;
    margin-top: 2px;
  }
  .pico dt {
    font-family: 'JetBrains Mono', monospace;
    font-size: 8.5px;
    letter-spacing: 0.09em;
    text-transform: uppercase;
    color: var(--muted);
    margin-top: 8px;
  }
  .pico dd {
    font-size: 13px;
    line-height: 1.45;
    font-weight: 600;
    margin-top: 2px;
  }
  .pico .soft dd {
    font-weight: 400;
    color: var(--soft-ink);
  }
  .flavour {
    margin: 14px 22px 0;
    font-size: 12.5px;
    font-style: italic;
    color: var(--soft-ink);
    line-height: 1.5;
    border-top: 1px dashed var(--line);
    padding-top: 11px;
  }
  .flavour b {
    font-style: normal;
    font-family: 'JetBrains Mono', monospace;
    font-size: 8.5px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--warn);
    display: block;
    margin-bottom: 4px;
  }
  .foot2 {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 8.5px;
    letter-spacing: 0.05em;
    color: var(--muted);
    padding: 13px 22px;
  }

  @media (max-width: 900px) {
    .card {
      padding: 8px;
      border-radius: 22px;
    }
    .face {
      border-radius: 15px;
    }
    .hdr {
      padding: 14px 15px 10px;
      gap: 10px;
    }
    .hdr h2 {
      font-size: 22px;
    }
    .gem {
      width: 48px;
      height: 48px;
      border-radius: 14px;
    }
    .gem b {
      font-size: 21px;
    }
    .tags,
    .artwrap,
    .typeline,
    .rules,
    .sect,
    .flavour,
    .foot2 {
      margin-left: 15px;
      margin-right: 15px;
    }
    .tags {
      padding: 0 0 12px;
    }
    table th {
      width: 112px;
      font-size: 8.5px;
      white-space: normal;
    }
    table td.val {
      width: 90px;
      font-size: 10px;
    }
    table td.bar i {
      height: 9px;
    }
    .pico {
      grid-template-columns: 1fr;
    }
    .foot2 {
      flex-direction: column;
      gap: 4px;
      font-size: 7.5px;
      padding-left: 0;
      padding-right: 0;
    }
  }
</style>
