<script lang="ts">
  import { session } from '$lib/session.svelte';

  let { open = false, onclose }: { open?: boolean; onclose: () => void } = $props();

  let email = $state('');
  let reg = $state('');
  let busy = $state(false);
  let error = $state<string | null>(null);

  async function submit() {
    error = null;
    if (!email.includes('@')) {
      error = 'Enter a valid email address.';
      return;
    }
    if (reg.trim().length < 2) {
      error = 'Enter your professional registration (e.g. GMC/GDC/NMC number).';
      return;
    }
    busy = true;
    try {
      await session.signIn(email.trim(), reg.trim());
      email = '';
      reg = '';
      onclose();
    } catch (e) {
      error = (e as Error).message;
    } finally {
      busy = false;
    }
  }
</script>

{#if open}
  <div
    class="overlay"
    role="presentation"
    onclick={(e) => {
      if (e.target === e.currentTarget) onclose();
    }}
  >
    <div class="dialog" role="dialog" aria-modal="true" aria-label="Sign in or register">
      <h3>Sign in / register</h3>
      <p class="note">
        Registration is free for practitioners. Enter your email and professional
        registration — no password needed.
      </p>
      <label>
        Email
        <input type="email" bind:value={email} placeholder="you@nhs.net" autocomplete="email" />
      </label>
      <label>
        Professional registration
        <input type="text" bind:value={reg} placeholder="e.g. GMC 1234567" />
      </label>
      {#if error}<div class="derr">{error}</div>{/if}
      <div class="actions">
        <button class="mbtn" onclick={submit} disabled={busy}>
          {busy ? 'Signing in…' : 'Continue'}
        </button>
        <button class="mbtn ghost" onclick={onclose}>Cancel</button>
      </div>
    </div>
  </div>
{/if}

<style>
  .overlay {
    position: fixed;
    inset: 0;
    background: rgba(42, 35, 64, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 20px;
    z-index: 60;
  }
  .dialog {
    background: var(--face);
    border: 3px solid var(--ink);
    border-radius: 20px;
    box-shadow: 0 10px 0 var(--ink);
    padding: 22px;
    width: min(440px, 100%);
  }
  h3 {
    font-size: 22px;
    font-weight: 800;
    margin-bottom: 6px;
  }
  .note {
    font-size: 13px;
    color: var(--muted);
    margin-bottom: 14px;
  }
  label {
    display: block;
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--soft-ink);
    margin-bottom: 12px;
  }
  input {
    display: block;
    width: 100%;
    margin-top: 6px;
    padding: 11px 12px;
    border: 2px solid var(--ink);
    border-radius: 12px;
    font-size: 15px;
    font-family: 'Plus Jakarta Sans', sans-serif;
    background: #fff;
  }
  .derr {
    color: var(--bad);
    font-size: 13px;
    margin-bottom: 10px;
  }
  .actions {
    display: flex;
    gap: 10px;
    margin-top: 4px;
  }
  .mbtn {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    font-weight: 700;
    padding: 12px 16px;
    border: 2px solid var(--ink);
    border-radius: 12px;
    background: var(--grape);
    color: #fff;
    cursor: pointer;
  }
  .mbtn.ghost {
    background: #fff;
    color: var(--ink);
  }
  .mbtn:disabled {
    opacity: 0.6;
    cursor: default;
  }
</style>
