<script lang="ts">
  import { ui } from '$lib/ui.svelte';
  import { sendContact } from '$lib/api';

  let message = $state('');
  let email = $state('');
  let hp = $state(''); // honeypot
  let sending = $state(false);
  let sent = $state(false);
  let error = $state<string | null>(null);

  function close() {
    ui.closeContact();
    message = '';
    email = '';
    error = null;
    sent = false;
  }

  async function submit() {
    error = null;
    if (message.trim().length < 3) {
      error = 'Please enter a message.';
      return;
    }
    sending = true;
    try {
      await sendContact({
        message: message.trim(),
        from_email: email.trim() || undefined,
        website: hp
      });
      sent = true;
    } catch (e) {
      error = (e as Error).message;
    } finally {
      sending = false;
    }
  }
</script>

{#if ui.contactOpen}
  <div
    class="overlay"
    role="presentation"
    onclick={(e) => {
      if (e.target === e.currentTarget) close();
    }}
  >
    <div class="dialog" role="dialog" aria-modal="true" aria-label="Contact us">
      {#if sent}
        <h3>Message sent 🎉</h3>
        <p class="note">Thanks for getting in touch — we’ll get back to you if you left an email.</p>
        <div class="dialog-actions">
          <button class="mbtn" onclick={close}>Close</button>
        </div>
      {:else}
        <h3>Contact us</h3>
        <p class="note">Feedback, a bug, or just saying hello? Send the developer a message.</p>
        <label>
          Your email <span class="opt">(optional, so we can reply)</span>
          <input type="email" bind:value={email} placeholder="you@example.com" />
        </label>
        <label>
          Message
          <textarea bind:value={message} rows="5" placeholder="What’s on your mind?"></textarea>
        </label>
        <input
          class="hp"
          tabindex="-1"
          autocomplete="off"
          aria-hidden="true"
          bind:value={hp}
          placeholder="Leave this empty"
        />
        {#if error}<div class="derr">{error}</div>{/if}
        <div class="dialog-actions">
          <button class="mbtn" onclick={submit} disabled={sending}>
            {sending ? 'Sending…' : 'Send'}
          </button>
          <button class="mbtn ghost" onclick={close}>Cancel</button>
        </div>
      {/if}
    </div>
  </div>
{/if}

<style>
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
  .note {
    color: var(--muted);
    font-size: 13px;
    margin-bottom: 16px;
  }
  label {
    display: block;
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--muted);
    margin-bottom: 14px;
  }
  label .opt {
    text-transform: none;
    letter-spacing: 0;
  }
  input,
  textarea {
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
  textarea {
    resize: vertical;
  }
  .hp {
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
