import { useId } from 'react';
import { cn } from './cn';

export interface ProgressBarProps {
  label: string;
  value: number;
  max?: number;
  className?: string;
}

export function ProgressBar({ label, value, max = 100, className }: ProgressBarProps) {
  const id = useId();
  const safeMax = max > 0 ? max : 100;
  const clamped = Math.min(Math.max(value, 0), safeMax);
  const percent = Math.round((clamped / safeMax) * 100);

  return (
    <div className={cn('w-full', className)}>
      <div className="mb-1.5 flex items-center justify-between text-xs font-medium text-slate-700">
        <label htmlFor={id}>{label}</label>
        <span>{percent}%</span>
      </div>
      <progress
        id={id}
        value={clamped}
        max={safeMax}
        className="h-2.5 w-full overflow-hidden rounded-full [&::-moz-progress-bar]:bg-[#14532d] [&::-webkit-progress-bar]:rounded-full [&::-webkit-progress-bar]:bg-[#dce8e1] [&::-webkit-progress-value]:rounded-full [&::-webkit-progress-value]:bg-[#14532d]"
      >
        {percent}%
      </progress>
    </div>
  );
}
