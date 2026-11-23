import { useId, type CSSProperties, type ReactNode } from 'react';
import { cn } from './cn';

export interface ResponsiveTableProps {
  caption: string;
  hideCaptionVisually?: boolean;
  headers: string[];
  children: ReactNode;
  className?: string;
}

/**
 * Semantic, keyboard-scrollable, @container-responsive data table.
 * Injects --label-2..N custom properties so narrow containers render stacked cards cleanly.
 */
export function ResponsiveTable({
  caption,
  hideCaptionVisually = true,
  headers,
  children,
  className,
}: ResponsiveTableProps) {
  const captionId = useId();

  const labelVars: Record<string, string> = {};
  headers.forEach((header, idx) => {
    labelVars[`--label-${idx + 1}`] = `"${header.replace(/"/g, '')}"`;
  });

  return (
    <div
      tabIndex={0}
      role="region"
      aria-labelledby={captionId}
      className={cn(
        'lp-table-wrapper rounded-xl border border-slate-200 bg-white shadow-sm',
        className,
      )}
    >
      <table className="lp-table text-left text-sm" style={labelVars as CSSProperties}>
        <caption
          id={captionId}
          className={cn(
            hideCaptionVisually
              ? 'visually-hidden'
              : 'border-b border-slate-200 px-4 py-3 text-left text-sm font-semibold text-slate-900',
          )}
        >
          {caption}
        </caption>
        <thead>
          <tr>
            {headers.map((header) => (
              <th
                key={header}
                scope="col"
                className="border-b border-slate-200 px-4 py-3 text-xs font-semibold uppercase tracking-wide text-slate-600"
              >
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">{children}</tbody>
      </table>
    </div>
  );
}
