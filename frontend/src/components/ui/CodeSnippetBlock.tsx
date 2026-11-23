import { Highlight, themes } from 'prism-react-renderer';
import { cn } from './cn';

export interface CodeSnippetBlockProps {
  code: string;
  language?: string;
  className?: string;
}

/**
 * Syntax-highlighted Python code block powered by prism-react-renderer (NFR-02).
 */
export function CodeSnippetBlock({
  code,
  language = 'python',
  className,
}: CodeSnippetBlockProps) {
  return (
    <Highlight theme={themes.nightOwl} code={code.trimEnd()} language={language}>
      {({ className: prismClass, style, tokens, getLineProps, getTokenProps }) => (
        <pre
          className={cn(
            prismClass,
            'overflow-x-auto rounded-lg border border-slate-800 p-3.5 font-mono text-xs leading-relaxed',
            className,
          )}
          style={style}
        >
          <code>
            {tokens.map((line, i) => (
              <div key={i} {...getLineProps({ line })}>
                <span
                  aria-hidden="true"
                  className="mr-3 inline-block w-5 select-none text-right text-slate-500"
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
  );
}
