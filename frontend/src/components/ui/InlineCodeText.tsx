import { Fragment } from 'react';

export interface InlineCodeTextProps {
  text: string;
}

/**
 * Safely renders inline backtick-delimited tokens (`like_this`) as styled <code> elements
 * without dangerouslySetInnerHTML (NFR-02 Readability & Security).
 */
export function InlineCodeText({ text }: InlineCodeTextProps) {
  if (!text || !text.includes('`')) {
    return <>{text}</>;
  }

  const segments = text.split(/(`[^`]+`)/g);
  return (
    <>
      {segments.map((part, idx) => {
        if (part.length >= 2 && part.startsWith('`') && part.endsWith('`')) {
          return (
            <code
              key={idx}
              className="rounded bg-[#edf5f0] px-1.5 py-0.5 font-mono text-[0.9em] font-semibold text-[#14532d]"
            >
              {part.slice(1, -1)}
            </code>
          );
        }
        return <Fragment key={idx}>{part}</Fragment>;
      })}
    </>
  );
}
