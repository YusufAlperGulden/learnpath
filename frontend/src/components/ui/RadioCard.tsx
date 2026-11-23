import { useId } from 'react';
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
                  'flex min-h-14 cursor-pointer flex-col justify-between rounded-xl border p-4 transition-colors',
                  'peer-focus-visible:outline peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-blue-600',
                  selected
                    ? 'border-blue-600 bg-blue-50/70 text-slate-900'
                    : 'border-slate-300 bg-white text-slate-800 hover:border-slate-400',
                )}
              >
                <span className="flex items-center justify-between gap-2">
                  <span className="text-sm font-semibold">{opt.label}</span>
                  <span
                    aria-hidden="true"
                    className={cn(
                      'h-4 w-4 rounded-full border-2',
                      selected ? 'border-blue-600 bg-blue-600' : 'border-slate-400 bg-white',
                    )}
                  />
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
