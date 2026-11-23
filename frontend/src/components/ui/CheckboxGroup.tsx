import { useId } from 'react';
import { Check } from 'lucide-react';
import { cn } from './cn';

export interface CheckboxOption<T extends string> {
  value: T;
  label: string;
  description?: string;
}

export interface CheckboxGroupProps<T extends string> {
  legend: string;
  name: string;
  options: CheckboxOption<T>[];
  selectedValues: T[];
  onChange: (next: T[]) => void;
  error?: string;
  hint?: string;
}

export function CheckboxGroup<T extends string>({
  legend,
  name,
  options,
  selectedValues,
  onChange,
  error,
  hint,
}: CheckboxGroupProps<T>) {
  const groupId = useId();
  const hintId = `${groupId}-hint`;
  const errorId = `${groupId}-error`;
  const describedBy = [hint ? hintId : null, error ? errorId : null]
    .filter(Boolean)
    .join(' ');

  const toggle = (value: T) => {
    if (selectedValues.includes(value)) {
      onChange(selectedValues.filter((v) => v !== value));
    } else {
      onChange([...selectedValues, value]);
    }
  };

  return (
    <fieldset
      aria-describedby={describedBy || undefined}
      className="border-0 p-0"
    >
      <legend className="text-sm font-semibold text-slate-900">{legend}</legend>
      {hint ? (
        <p id={hintId} className="mt-1 text-xs text-slate-600">
          {hint}
        </p>
      ) : null}
      <div className="mt-3 grid gap-3 sm:grid-cols-3">
        {options.map((opt) => {
          const inputId = `${groupId}-${opt.value}`;
          const checked = selectedValues.includes(opt.value);
          return (
            <div key={opt.value} className="relative">
              <input
                type="checkbox"
                id={inputId}
                name={name}
                value={opt.value}
                checked={checked}
                aria-invalid={error ? 'true' : undefined}
                onChange={() => toggle(opt.value)}
                className="visually-hidden peer"
              />
              <label
                htmlFor={inputId}
                className={cn(
                  'flex min-h-14 cursor-pointer items-start gap-3 rounded-xl border p-4 transition-colors',
                  'peer-focus-visible:outline peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-blue-600',
                  checked
                    ? 'border-blue-600 bg-blue-50/70 text-slate-900'
                    : 'border-slate-300 bg-white text-slate-800 hover:border-slate-400',
                )}
              >
                <span
                  aria-hidden="true"
                  className={cn(
                    'mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded border',
                    checked
                      ? 'border-blue-600 bg-blue-600 text-white'
                      : 'border-slate-400 bg-white',
                  )}
                >
                  {checked ? <Check className="h-3.5 w-3.5" /> : null}
                </span>
                <span>
                  <span className="block text-sm font-semibold">{opt.label}</span>
                  {opt.description ? (
                    <span className="mt-0.5 block text-xs text-slate-600">
                      {opt.description}
                    </span>
                  ) : null}
                </span>
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
