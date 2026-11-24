import { Highlight, themes } from 'prism-react-renderer';
import { cn } from './cn';

export interface CodeSnippetBlockProps {
  code: string;
  language?: string;
  className?: string;
}

/**
 * Light-themed syntax-highlighted Python code block matching Figma UI (NFR-02).
 */
export function CodeSnippetBlock({
  code,
  language = 'python',
  className,
}: CodeSnippetBlockProps) {
  const label = language.toLowerCase() === 'python' ? 'Python' : language;
  return (
    <div
      className={cn(
        'overflow-hidden rounded-xl border border-[#dce6df] bg-[#f4f7f5]',
        className,
      )}
    >
      <div className="flex items-center justify-between border-b border-[#e2ebe5] bg-[#eef3f0] px-4 py-1.5 text-[11px] font-semibold tracking-wide text-slate-500">
        <span>{label}</span>
      </div>
      <Highlight theme={themes.github} code={code.trimEnd()} language={language}>
        {({ className: prismClass, style, tokens, getLineProps, getTokenProps }) => (
          <pre
            className={cn(
              prismClass,
              'overflow-x-auto p-4 font-mono text-xs leading-relaxed text-slate-800',
            )}
            style={{ ...style, backgroundColor: 'transparent' }}
          >
            <code>
              {tokens.map((line, i) => (
                <div key={i} {...getLineProps({ line })}>
                  <span
                    aria-hidden="true"
                    className="mr-4 inline-block w-5 select-none text-right text-slate-400"
                  >
                    {i + 1}
                  </span>
                  {line.map((token, key) => (
                    <span key={key} {...getTokenProps({ token })} />
                  ))}
                </div>
              ))}
            </code>
          </pre>
        )}
      </Highlight>
    </div>
  );
}
