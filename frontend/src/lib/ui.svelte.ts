// Tiny shared UI state (Svelte 5 runes) — lets any page open the global auth modal.
class UI {
  authOpen = $state(false);
  openAuth(): void {
    this.authOpen = true;
  }
  closeAuth(): void {
    this.authOpen = false;
  }
}

export const ui = new UI();
