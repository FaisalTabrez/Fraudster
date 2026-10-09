import { Icon } from "./Icon";

// Shows a submitted URL as inert text. Fraudster never opens links, so this is a plain span:
// no <a href>, no underline, no pointer cursor. The host is emphasised, scheme and path dimmed.
export function InertUrl({ value, badge = true }: { value: string; badge?: boolean }) {
  const parts = /^([a-z][a-z0-9+.-]*:\/\/)?([^/?#\s]*)(.*)$/i.exec(value);
  const scheme = parts?.[1] ?? "";
  const host = parts?.[2] ?? value;
  const rest = parts?.[3] ?? "";
  return (
    <span className="fr-url">
      <span className="fr-url__text">
        <span className="fr-url__dim">{scheme}</span>
        {host}
        <span className="fr-url__dim">{rest}</span>
      </span>
      {badge && (
        <span className="fr-url__badge">
          <Icon name="not-opened" size={14} />
          Not opened
        </span>
      )}
    </span>
  );
}
