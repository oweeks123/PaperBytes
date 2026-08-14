<!-- Animated placeholder shown while the AI illustration is being generated:
     a caped scientist-hero sketching at an easel, with a speech bubble. -->
<svg viewBox="0 0 560 200" class="scene" role="img" aria-label="A scientist hero is drawing your card">
  <rect width="560" height="200" fill="#fffdf7" />
  <rect x="0" y="168" width="560" height="32" fill="#5bd6a6" opacity="0.4" />

  <!-- twinkles -->
  <g fill="#ffc94d" stroke="#2a2340" stroke-width="2">
    <path class="spark s1" d="M406 92 l4 9 9 4 -9 4 -4 9 -4 -9 -9 -4 9 -4 z" />
    <path class="spark s2" d="M250 34 l3 6 6 3 -6 3 -3 6 -3 -6 -6 -3 6 -3 z" />
    <path class="spark s3" d="M382 148 l3 6 6 3 -6 3 -3 6 -3 -6 -6 -3 6 -3 z" />
  </g>

  <!-- easel -->
  <line x1="314" y1="150" x2="314" y2="196" stroke="#2a2340" stroke-width="6" stroke-linecap="round" />
  <rect x="256" y="50" width="118" height="98" rx="8" fill="#ffffff" stroke="#2a2340" stroke-width="4" />
  <path class="scribble" d="M276 120 q18 -48 40 -22 q20 24 42 -26" fill="none" stroke="#7b5be8" stroke-width="5" stroke-linecap="round" />
  <circle class="scribble d2" cx="334" cy="80" r="10" fill="none" stroke="#ff5f7e" stroke-width="5" />
  <line x1="280" y1="146" x2="260" y2="192" stroke="#2a2340" stroke-width="6" stroke-linecap="round" />
  <line x1="350" y1="146" x2="368" y2="192" stroke="#2a2340" stroke-width="6" stroke-linecap="round" />

  <!-- hero -->
  <g class="hero">
    <path class="cape" d="M150 104 q-42 28 -22 78 q22 -14 46 -8 q-10 -36 8 -66 z" fill="#ff5f7e" stroke="#2a2340" stroke-width="3" />
    <path d="M136 108 q24 -16 48 0 l10 62 q-34 12 -68 0 z" fill="#ffffff" stroke="#2a2340" stroke-width="4" />
    <line x1="160" y1="112" x2="164" y2="168" stroke="#2a2340" stroke-width="2.4" />
    <circle cx="160" cy="80" r="23" fill="#ffc94d" stroke="#2a2340" stroke-width="4" />
    <path d="M141 74 q19 -11 38 0 q-5 11 -19 11 q-14 0 -19 -11 z" fill="#7b5be8" stroke="#2a2340" stroke-width="2" />
    <circle cx="152" cy="76" r="2.4" fill="#fff" /><circle cx="168" cy="76" r="2.4" fill="#fff" />
    <path d="M151 90 q9 8 18 0" fill="none" stroke="#2a2340" stroke-width="2.6" stroke-linecap="round" />
    <g class="arm">
      <path d="M184 110 q40 -8 66 -22" fill="none" stroke="#2a2340" stroke-width="7" stroke-linecap="round" />
      <line x1="250" y1="88" x2="264" y2="82" stroke="#7b5be8" stroke-width="6" stroke-linecap="round" />
      <circle cx="265" cy="81" r="3.6" fill="#ff5f7e" />
    </g>
  </g>

  <!-- speech bubble -->
  <g class="bubble">
    <path d="M402 68 l-16 22 l28 -12 z" fill="#ffffff" stroke="#2a2340" stroke-width="4" />
    <rect x="372" y="20" width="176" height="50" rx="16" fill="#ffffff" stroke="#2a2340" stroke-width="4" />
    <text x="460" y="51" text-anchor="middle" class="say">I'm drawing here!</text>
  </g>
</svg>

<style>
  .scene {
    width: 100%;
    display: block;
  }
  .say {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-weight: 800;
    font-size: 15px;
    fill: #2a2340;
  }

  .hero {
    transform-box: fill-box;
    transform-origin: bottom center;
    animation: bob 2.6s ease-in-out infinite;
  }
  @keyframes bob {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-4px); }
  }

  .arm {
    transform-box: fill-box;
    transform-origin: 8% 60%;
    animation: stroke 0.55s ease-in-out infinite alternate;
  }
  @keyframes stroke {
    from { transform: rotate(-6deg); }
    to { transform: rotate(6deg); }
  }

  .cape {
    transform-box: fill-box;
    transform-origin: top right;
    animation: flap 1.5s ease-in-out infinite alternate;
  }
  @keyframes flap {
    from { transform: skewY(-3deg) rotate(-1deg); }
    to { transform: skewY(4deg) rotate(1.5deg); }
  }

  .bubble {
    transform-box: fill-box;
    transform-origin: bottom left;
    animation: pop 2.2s ease-in-out infinite;
  }
  @keyframes pop {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.05); }
  }

  .scribble {
    stroke-dasharray: 220;
    stroke-dashoffset: 220;
    animation: draw 2.6s ease-in-out infinite;
  }
  .scribble.d2 {
    animation-delay: 0.5s;
  }
  @keyframes draw {
    0% { stroke-dashoffset: 220; }
    45% { stroke-dashoffset: 0; }
    80% { stroke-dashoffset: 0; }
    100% { stroke-dashoffset: 220; }
  }

  .spark {
    transform-box: fill-box;
    transform-origin: center;
    animation: twinkle 1.5s ease-in-out infinite;
  }
  .s2 { animation-delay: 0.5s; }
  .s3 { animation-delay: 1s; }
  @keyframes twinkle {
    0%, 100% { opacity: 0.2; transform: scale(0.7); }
    50% { opacity: 1; transform: scale(1.1); }
  }

  @media (prefers-reduced-motion: reduce) {
    .hero, .arm, .cape, .bubble, .scribble, .spark {
      animation: none;
    }
    .scribble { stroke-dashoffset: 0; }
    .spark { opacity: 0.8; }
  }
</style>
