<script lang="ts">
  import { base } from '$app/paths';
  import ContentPage from '$lib/components/ContentPage.svelte';
</script>

<svelte:head>
  <title>Privacy Policy · Paper Heroes</title>
  <meta name="description" content="How Paper Heroes collects, uses, and protects your data." />
</svelte:head>

<ContentPage title="Privacy Policy" updated="17 August 2026">
  <p>
    This Privacy Policy explains what information <strong>Paper Heroes</strong> ("we", "us")
    collects when you use paperheroes.io, how we use it, and the choices you have. By using the
    site you agree to the practices described here.
  </p>

  <h2>Information we collect</h2>
  <ul>
    <li>
      <strong>Account details.</strong> If you register, we store the <strong>email address</strong>
      and <strong>professional registration</strong> you provide, along with your account tier and a
      session token used to keep you signed in. We do not collect a password — sign-in is
      passwordless.
    </li>
    <li>
      <strong>Your content.</strong> If you save cards into decks or write reflections, we store
      those decks, card memberships, and reflection text against your account.
    </li>
    <li>
      <strong>Contact messages.</strong> If you use the contact form, we store the message and, if
      you provide one, the email address you enter so we can reply.
    </li>
    <li>
      <strong>Approximate location.</strong> To show region-appropriate advertising, your IP
      address is used to look up your <strong>country</strong> (via the ip-api.com service). We
      store the country result for that request, not a history of your IP address.
    </li>
    <li>
      <strong>Technical data.</strong> Like most websites, our hosting and content-delivery
      providers process standard request data (such as IP address and browser user-agent) to serve
      and secure the site.
    </li>
  </ul>

  <h2>Cookies and advertising</h2>
  <p>
    Paper Heroes uses a session token stored in your browser's local storage to keep you signed in.
    We display advertising through <strong>Google AdSense</strong>. Google and its partners may use
    cookies and similar technologies to serve ads based on your prior visits to this and other
    websites.
  </p>
  <ul>
    <li>
      Third-party vendors, including Google, use cookies to serve ads based on your visits to this
      site and others.
    </li>
    <li>
      Google's use of advertising cookies enables it and its partners to serve ads to you based on
      your visits. You can opt out of personalised advertising by visiting
      <a href="https://www.google.com/settings/ads" target="_blank" rel="noreferrer"
        >Google Ads Settings</a
      >.
    </li>
    <li>
      More information about how Google uses data is available at
      <a href="https://policies.google.com/technologies/partner-sites" target="_blank" rel="noreferrer"
        >How Google uses information from sites that use its services</a
      >.
    </li>
  </ul>

  <h2>How we use your information</h2>
  <ul>
    <li>To operate the site and provide the features of your tier.</li>
    <li>To save and display your decks and reflections.</li>
    <li>To respond to messages you send us.</li>
    <li>To show region-appropriate advertising and keep the service secure.</li>
  </ul>

  <h2>Third-party services</h2>
  <p>To provide the app, we share limited data with the following processors:</p>
  <ul>
    <li><strong>PubMed / NCBI</strong> — article retrieval (no personal data sent).</li>
    <li>
      <strong>Anthropic</strong> and <strong>OpenAI</strong> — generating paper summaries,
      appraisals, and illustrations. These are generated from public article text, not your personal
      data.
    </li>
    <li><strong>Google AdSense</strong> — advertising, as described above.</li>
    <li><strong>ip-api.com</strong> — country lookup from IP address.</li>
    <li>
      <strong>Render</strong> (hosting) and <strong>Cloudflare</strong> (DNS/CDN) — serving and
      protecting the site.
    </li>
  </ul>

  <h2>Data retention</h2>
  <p>
    We keep your account data, decks, reflections, and contact messages for as long as your account
    is active or as needed to provide the service. You can ask us to delete your account and its
    associated data at any time using the <a href="{base}/#contact">contact form</a>.
  </p>

  <h2>Your rights</h2>
  <p>
    Depending on where you live, you may have the right to access, correct, or delete the personal
    data we hold about you, or to object to certain processing. To exercise any of these rights,
    contact us via the <a href="{base}/#contact">contact form</a>.
  </p>

  <h2>Children</h2>
  <p>Paper Heroes is intended for healthcare professionals and adults; it is not directed at children.</p>

  <h2>Changes</h2>
  <p>
    We may update this policy from time to time. Material changes will be reflected by the "last
    updated" date above.
  </p>

  <h2>Contact</h2>
  <p>
    Questions about this policy? Reach us through the <a href="{base}/#contact">contact form</a>. See
    also our <a href="{base}/terms">Terms of Service</a>.
  </p>
</ContentPage>
