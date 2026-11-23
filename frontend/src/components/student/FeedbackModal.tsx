import { useEffect, useId, useState, type FormEvent } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Star } from 'lucide-react';
import { extractApiErrorMessage } from '../../api/admin';
import { studentApi } from '../../api/student';
import { Button, Modal, cn } from '../ui';

export interface FeedbackTarget {
  resource_id: string;
  title: string;
  initialRating?: number | null;
  initialComment?: string | null;
}

export interface FeedbackModalProps {
  target: FeedbackTarget | null;
  onClose: () => void;
}

const RATING_LABELS: Record<number, string> = {
  1: '1 star — Not helpful',
  2: '2 stars — Needs improvement',
  3: '3 stars — Helpful basics',
  4: '4 stars — Clear & relevant',
  5: '5 stars — Excellent resource',
};

export function FeedbackModal({ target, onClose }: FeedbackModalProps) {
  const queryClient = useQueryClient();
  const groupId = useId();

  const [rating, setRating] = useState<number>(5);
  const [comment, setComment] = useState<string>('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    if (target) {
      setRating(target.initialRating ?? 5);
      setComment(target.initialComment ?? '');
      setErrorMsg(null);
    }
  }, [target]);

  const saveMutation = useMutation({
    mutationFn: async () => {
      if (!target) throw new Error('No resource selected.');
      return studentApi.upsertFeedback({
        resource_id: target.resource_id,
        rating,
        comment: comment.trim() || null,
      });
    },
    onSuccess: async () => {
      onClose();
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['recommendations'] }),
        queryClient.invalidateQueries({ queryKey: ['bookmarks'] }),
        queryClient.invalidateQueries({ queryKey: ['resource-history'] }),
      ]);
    },
    onError: (err: unknown) => {
      setErrorMsg(extractApiErrorMessage(err, 'Could not save resource rating.'));
    },
  });

  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setErrorMsg(null);
    saveMutation.mutate();
  };

  return (
    <Modal
      open={Boolean(target)}
      onClose={onClose}
      title="Rate & Review Learning Resource"
      description={
        target
          ? `Share how helpful "${target.title}" was for your Python learning path (FR09).`
          : undefined
      }
    >
      <form method="post" action="/api/v1/feedback" onSubmit={handleSubmit} className="space-y-4">
        {errorMsg ? (
          <div
            role="alert"
            className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800"
          >
            {errorMsg}
          </div>
        ) : null}

        <fieldset className="border-0 p-0">
          <legend className="text-sm font-semibold text-slate-900">
            Your rating (1 to 5 stars) <span aria-hidden="true">*</span>
          </legend>
          <div className="mt-2.5 flex items-center gap-2">
            {[1, 2, 3, 4, 5].map((value) => {
              const inputId = `${groupId}-star-${value}`;
              const filled = value <= rating;
              const isSelected = value === rating;
              return (
                <div key={value} className="relative">
                  <input
                    type="radio"
                    id={inputId}
                    name="rating"
                    value={value}
                    checked={isSelected}
                    onChange={() => setRating(value)}
                    className="visually-hidden peer"
                  />
                  <label
                    htmlFor={inputId}
                    className={cn(
                      'inline-flex min-h-11 min-w-11 cursor-pointer items-center justify-center rounded-xl border p-2 transition-colors',
                      'peer-focus-visible:outline peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-blue-600',
                      filled
                        ? 'border-amber-400 bg-amber-50 text-amber-600'
                        : 'border-slate-300 bg-white text-slate-400 hover:border-slate-400',
                    )}
                  >
                    <Star
                      aria-hidden="true"
                      className={cn('h-6 w-6', filled ? 'fill-amber-400 text-amber-500' : '')}
                    />
                    <span className="visually-hidden">{RATING_LABELS[value]}</span>
                  </label>
                </div>
              );
            })}
          </div>
          <p className="mt-2 text-xs font-medium text-slate-600">{RATING_LABELS[rating]}</p>
        </fieldset>

        <div className="flex flex-col gap-1">
          <label htmlFor={`${groupId}-comment`} className="text-sm font-semibold text-slate-900">
            Optional review note
          </label>
          <textarea
            id={`${groupId}-comment`}
            name="comment"
            rows={3}
            maxLength={2000}
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="What stood out about the examples, pacing, or clarity?"
            className="rounded-lg border border-slate-400 px-3 py-2 text-sm text-slate-900"
          />
        </div>

        <div className="flex justify-end gap-3 border-t border-slate-100 pt-4">
          <Button variant="outline" onClick={onClose} disabled={saveMutation.isPending}>
            Cancel
          </Button>
          <Button type="submit" isLoading={saveMutation.isPending}>
            Save Rating
          </Button>
        </div>
      </form>
    </Modal>
  );
}
