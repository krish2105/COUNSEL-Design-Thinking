/* The session the tabs share.
 *
 * A decision is one thread of work across several screens — the Room argues it,
 * Decide scores it, the Ledger settles it months later — so the tabs need a
 * common handle. It lives in localStorage rather than a URL because the user
 * moves between tabs by clicking the masthead, and losing the session on the
 * way to the memo would be the single most annoying thing this app could do. */

const KEY = "counsel-session";

export function currentSession(): string | null {
  try {
    return window.localStorage.getItem(KEY);
  } catch {
    return null;
  }
}

export function setCurrentSession(id: string): void {
  try {
    window.localStorage.setItem(KEY, id);
  } catch {
    /* A private window with site data blocked. The tab still works; it just
       cannot hand the session to the next one. */
  }
}
