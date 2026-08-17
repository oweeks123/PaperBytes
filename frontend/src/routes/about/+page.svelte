<script lang="ts">
  import { base } from '$app/paths';
  import ContentPage from '$lib/components/ContentPage.svelte';
</script>

<svelte:head>
  <title>About · Paper Heroes</title>
  <meta
    name="description"
    content="Paper Heroes deals one recently-published medical paper at random, summarised and critically appraised by AI and shown as a comic-book trading card."
  />
</svelte:head>

<ContentPage title="About Paper Heroes">
  <p>
    <strong>Paper Heroes</strong> deals you <strong>one recently-published medical paper at random</strong>,
    drawn from a curated set of peer-reviewed journals over the last 30 days. Every visit is a fresh
    draw — a quick, serendipitous way to keep a finger on the pulse of the evidence.
  </p>
  <p>
    Each paper is summarised and critically appraised by AI, then shown as a comic-book
    <strong>trading card</strong> — complete with an AI-generated <strong>hero</strong> (for
    beneficial findings) or <strong>villain</strong> (for harms) illustrating the topic. The card
    reports the headline statistics (odds/risk ratios, confidence intervals, p-values) with a
    plain-language read on what they mean, the study's level of evidence, and an appraisal of its
    strengths and limitations.
  </p>

  <h2>Who it's for</h2>
  <p>
    Clinicians, students, researchers, and anyone who wants a bite-sized, critically-framed window
    into new medical research. It is a tool for discovery and reflection — not a substitute for
    reading the full paper.
  </p>

  <h2>How it works</h2>
  <ul>
    <li>
      Papers are retrieved from <strong>PubMed</strong> (NCBI E-utilities), filtered to a curated
      list of journals and to human-subject research from the last 30 days.
    </li>
    <li>
      A large language model produces the summary and critical appraisal; a separate image model
      draws the hero or villain. Both are generated once per paper and cached, so every reader sees
      the same appraisal.
    </li>
    <li>
      <strong>Registered</strong> members can add a reflection to the downloadable PDF.
      <strong>Premium</strong> members can save cards into named <strong>Card Decks</strong> and keep
      a reflection on the back of each card.
    </li>
  </ul>

  <div class="callout warn">
    <p>
      ⚠ <strong>Not medical advice.</strong> AI-generated summaries, appraisals, and illustrations
      can be incomplete or wrong. Paper Heroes is for education and interest only — always read and
      verify the original article before making any clinical decision.
    </p>
  </div>

  <h2>Get in touch</h2>
  <p>
    Questions, feedback, or a bug to report? Use the <a href="{base}/#contact">contact form</a> —
    we'd love to hear from you. See also our
    <a href="{base}/privacy">Privacy Policy</a> and <a href="{base}/terms">Terms of Service</a>.
  </p>
</ContentPage>
