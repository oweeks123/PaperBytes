// Tiny shared UI state (Svelte 5 runes) — lets any page open the global auth /
// contact modals (both are hosted in the root layout).
class UI {
  authOpen = $state(false);
  contactOpen = $state(false);
  openAuth(): void {
    this.authOpen = true;
  }
  closeAuth(): void {
    this.authOpen = false;
  }
  openContact(): void {
    this.contactOpen = true;
  }
  closeContact(): void {
    this.contactOpen = false;
  }
}

export const ui = new UI();
