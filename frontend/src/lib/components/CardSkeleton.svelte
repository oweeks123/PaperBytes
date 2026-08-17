<!-- Loading placeholder shaped like the EvidenceCard, so dealing a card feels
     instant and finished rather than a bare line of text. -->
<div class="card" aria-hidden="true">
  <div class="face">
    <div class="hdr">
      <div class="tstack">
        <div class="sk bar w85"></div>
        <div class="sk bar w60"></div>
      </div>
      <div class="sk gem"></div>
    </div>

    <div class="panel">
      <span class="cap">Dealing your card…</span>
    </div>

    <div class="body">
      <div class="sk line w95"></div>
      <div class="sk line w88"></div>
      <div class="sk line w40"></div>
      <div class="stats">
        <div class="srow"><span class="sk lbl"></span><span class="sk seg"></span></div>
        <div class="srow"><span class="sk lbl"></span><span class="sk seg"></span></div>
        <div class="srow"><span class="sk lbl"></span><span class="sk seg"></span></div>
        <div class="srow"><span class="sk lbl"></span><span class="sk seg"></span></div>
      </div>
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
    border-radius: 20px;
    overflow: hidden;
  }
  .hdr {
    display: flex;
    align-items: flex-start;
    gap: 16px;
    padding: 20px 22px 14px;
  }
  .tstack {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding-top: 4px;
  }
  .sk {
    background: var(--seg-off);
    border-radius: 8px;
    animation: pulse 1.3s ease-in-out infinite;
  }
  .bar {
    height: 20px;
  }
  .w85 {
    width: 85%;
  }
  .w60 {
    width: 60%;
  }
  .gem {
    width: 58px;
    height: 58px;
    border-radius: 16px;
    flex: 0 0 auto;
  }
  .panel {
    margin: 0 12px;
    height: 300px;
    border-radius: 16px;
    background: var(--sky);
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: inset 0 0 0 3px var(--ink);
  }
  .cap {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    font-weight: 700;
    color: var(--soft-ink);
    animation: pulse 1.3s ease-in-out infinite;
  }
  .body {
    padding: 20px 22px 24px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .line {
    height: 13px;
  }
  .w95 {
    width: 95%;
  }
  .w88 {
    width: 88%;
  }
  .w40 {
    width: 40%;
  }
  .stats {
    display: flex;
    flex-direction: column;
    gap: 14px;
    margin-top: 10px;
  }
  .srow {
    display: flex;
    align-items: center;
    gap: 16px;
  }
  .lbl {
    height: 10px;
    width: 130px;
    flex: 0 0 auto;
  }
  .seg {
    height: 12px;
    flex: 1;
    border-radius: 6px;
  }
  /* Stagger the pulse a touch so it reads as a soft shimmer, not a flash. */
  .tstack .bar:nth-child(2) {
    animation-delay: 0.15s;
  }
  .body .line:nth-child(2) {
    animation-delay: 0.1s;
  }
  .body .line:nth-child(3) {
    animation-delay: 0.2s;
  }
  .srow:nth-child(2) .seg {
    animation-delay: 0.1s;
  }
  .srow:nth-child(3) .seg {
    animation-delay: 0.2s;
  }
  .srow:nth-child(4) .seg {
    animation-delay: 0.3s;
  }

  @keyframes pulse {
    0%,
    100% {
      opacity: 1;
    }
    50% {
      opacity: 0.45;
    }
  }
  @media (prefers-reduced-motion: reduce) {
    .sk,
    .cap {
      animation: none;
    }
  }
</style>
