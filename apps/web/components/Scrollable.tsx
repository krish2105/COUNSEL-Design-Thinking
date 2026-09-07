/* A horizontally scrolling region a keyboard can actually reach.
 *
 * A table wide enough to scroll on a phone is unreachable to anyone not using a
 * pointer unless the container is focusable and named — axe calls this
 * scrollable-region-focusable, and it is a real failure rather than a lint:
 * without it, half the capability table simply does not exist for a keyboard
 * user on a narrow screen.
 */

export function Scrollable({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="scrollable" role="region" aria-label={label} tabIndex={0}>
      {children}
    </div>
  );
}
