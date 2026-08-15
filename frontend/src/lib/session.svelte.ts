// Client session/auth state (Svelte 5 runes). Holds the signed-in user and
// bearer token, persisted to localStorage. Lightweight/passwordless by design —
// register with email + professional registration returns a token.
import {
  downgradeTier,
  getMe,
  register,
  setAuthToken,
  upgradeTier,
  type User
} from './api';

const KEY = 'ph_token';

class Session {
  user = $state<User | null>(null);
  ready = $state(false); // true once init() has resolved (token validated or none)

  get tier(): 'anon' | 'free_registered' | 'paid' {
    return (this.user?.tier as 'free_registered' | 'paid') ?? 'anon';
  }
  get isSignedIn(): boolean {
    return this.user !== null;
  }
  get isPaid(): boolean {
    return this.user?.tier === 'paid';
  }

  /** Restore a persisted token (if any) and validate it against /auth/me. */
  async init(): Promise<void> {
    const t = typeof localStorage !== 'undefined' ? localStorage.getItem(KEY) : null;
    if (t) {
      setAuthToken(t);
      try {
        this.user = await getMe();
      } catch {
        this.clear(); // stale/invalid token
      }
    }
    this.ready = true;
  }

  async signIn(email: string, professionalRegistration: string): Promise<User> {
    const u = await register(email, professionalRegistration);
    this.apply(u);
    return u;
  }
  async upgrade(): Promise<void> {
    this.apply(await upgradeTier());
  }
  async downgrade(): Promise<void> {
    this.apply(await downgradeTier());
  }
  signOut(): void {
    this.clear();
  }

  private apply(u: User): void {
    this.user = u;
    setAuthToken(u.token);
    if (typeof localStorage !== 'undefined') localStorage.setItem(KEY, u.token);
  }
  private clear(): void {
    this.user = null;
    setAuthToken(null);
    if (typeof localStorage !== 'undefined') localStorage.removeItem(KEY);
  }
}

export const session = new Session();
