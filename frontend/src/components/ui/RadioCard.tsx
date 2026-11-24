import { useId } from 'react';
import { Check } from 'lucide-react';
import { cn } from './cn';

export interface RadioCardOption<T extends string> {
  value: T;
  label: string;
  description?: string;
}

export interface RadioCardGroupProps<T extends string> {
  legend: string;
  name: string;
  options: RadioCardOption<T>[];
  value: T;
  onChange: (next: T) => void;
  error?: string;
}

export function RadioCardGroup<T extends string>({
  legend,
  name,
  options,
  value,
  onChange,
  error,
}: RadioCardGroupProps<T>) {
  const groupId = useId();
  const errorId = `${groupId}-error`;

  return (
    <fieldset
      aria-describedby={error ? errorId : undefined}
      className="border-0 p-0"
    >
      <legend className="text-sm font-semibold text-slate-900">{legend}</legend>
      <div className="mt-3 grid gap-3 sm:grid-cols-3">
        {options.map((opt) => {
          const inputId = `${groupId}-${opt.value}`;
          const selected = value === opt.value;
          return (
            <div key={opt.value} className="relative">
              <input
                type="radio"
                id={inputId}
                name={name}
                value={opt.value}
                checked={selected}
                aria-invalid={error ? 'true' : undefined}
                onChange={() => onChange(opt.value)}
                className="visually-hidden peer"
              />
              <label
                htmlFor={inputId}
                className={cn(
                  'flex min-h-16 cursor-pointer flex-col justify-between rounded-xl border p-4 transition-colors',
                  'peer-focus-visible:outline peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-[#14532d]',
                  selected
                    ? 'border-[#14532d] bg-[#edf6f0] text-slate-900 shadow-xs'
                    : 'border-slate-200 bg-white text-slate-800 hover:border-[#14532d]/40 hover:bg-[#f8fbf9]',
                )}
              >
                <span className="flex items-center justify-between gap-2">
                  <span className="text-sm font-semibold">{opt.label}</span>
                  <span
                    aria-hidden="true"
                    className={cn(
                      'flex h-5 w-5 shrink-0 items-center justify-center rounded-full border',
                      selected
                        ? 'border-[#14532d] bg-[#14532d] text-white'
                        : 'border-slate-300 bg-white',
                    )}
                  >
                    {selected ? <Check className="h-3 w-3" /> : null}
                  </span>
                </span>
                {opt.description ? (
                  <span className="mt-1.5 text-xs text-slate-600">{opt.description}</span>
                ) : null}
              </label>
            </div>
          );
        })}
      </div>
      {error ? (
        <p id={errorId} className="mt-2 text-sm font-medium text-red-600">
          {error}
        </p>
      ) : null}
    </fieldset>
  );
}
