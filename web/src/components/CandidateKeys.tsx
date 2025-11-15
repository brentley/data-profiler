// Candidate key suggestions component
// Shows suggested uniqueness keys with confirmation UI
import { useState } from 'react';
import { api } from '../utils/api';
import type { CandidateKey } from '../types/api';

interface CandidateKeysProps {
  runId: string;
  candidateKeys: CandidateKey[];
  onKeysConfirmed: () => void;
  onError: (message: string) => void;
}

export function CandidateKeys({
  runId,
  candidateKeys,
  onKeysConfirmed,
  onError,
}: CandidateKeysProps) {
  const [selectedKeys, setSelectedKeys] = useState<Set<number>>(new Set());
  const [confirming, setConfirming] = useState(false);

  if (candidateKeys.length === 0) {
    return (
      <div className="card">
        <div className="flex items-center gap-3">
          <svg
            className="w-6 h-6 text-gray-400 flex-shrink-0"
            width="24"
            height="24"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z"
            />
          </svg>
          <div>
            <h3 className="font-semibold text-gray-600 dark:text-gray-400">
              No Candidate Keys Found
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-500">
              No suitable uniqueness keys were identified in this dataset
            </p>
          </div>
        </div>
      </div>
    );
  }

  const toggleKey = (index: number) => {
    const newSelected = new Set(selectedKeys);
    if (newSelected.has(index)) {
      newSelected.delete(index);
    } else {
      newSelected.add(index);
    }
    setSelectedKeys(newSelected);
  };

  const handleConfirm = async () => {
    if (selectedKeys.size === 0) {
      onError('Please select at least one candidate key to confirm');
      return;
    }

    setConfirming(true);

    try {
      const keysToConfirm = Array.from(selectedKeys).map(
        (index) => candidateKeys[index].columns
      );

      await api.confirmKeys(runId, { keys: keysToConfirm });
      onKeysConfirmed();
    } catch (err) {
      onError(
        err instanceof Error
          ? err.message
          : 'Failed to confirm keys. Please try again.'
      );
      setConfirming(false);
    }
  };

  return (
    <div className="card">
      <div className="mb-4">
        <h3 className="text-lg font-semibold mb-2">Candidate Uniqueness Keys</h3>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Select one or more key combinations to check for duplicates. Keys are
          ranked by distinctness and null ratios.
        </p>
      </div>

      <div className="space-y-3 mb-4">
        {candidateKeys.map((candidate, index) => {
          const isSelected = selectedKeys.has(index);
          const isSingleColumn = candidate.columns.length === 1;

          return (
            <label
              key={index}
              className={`block p-4 border-2 rounded-lg cursor-pointer transition-all ${
                isSelected
                  ? 'border-vq-primary bg-blue-50 dark:bg-blue-900/20'
                  : 'border-gray-200 dark:border-slate-700 hover:border-gray-300 dark:hover:border-slate-600'
              }`}
            >
              <div className="flex items-start gap-3">
                <input
                  type="checkbox"
                  checked={isSelected}
                  onChange={() => toggleKey(index)}
                  className="mt-1 w-4 h-4 text-vq-primary focus:ring-vq-primary rounded"
                />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-2">
                    {isSingleColumn ? (
                      <span className="badge badge-info">Single Column</span>
                    ) : (
                      <span className="badge badge-info">
                        Compound ({candidate.columns.length} columns)
                      </span>
                    )}
                    {candidate.score !== undefined && (
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        Score: {(candidate.score * 100).toFixed(1)}%
                      </span>
                    )}
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {candidate.columns.map((col, colIndex) => (
                      <span
                        key={colIndex}
                        className="inline-flex items-center px-3 py-1 rounded-md bg-gray-100 dark:bg-slate-700 text-sm font-mono"
                      >
                        {col}
                      </span>
                    ))}
                  </div>
                  {candidate.distinct_ratio !== undefined &&
                    candidate.null_ratio_sum !== undefined && (
                      <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                        Distinct ratio: {(candidate.distinct_ratio * 100).toFixed(1)}% |
                        Null ratio: {(candidate.null_ratio_sum * 100).toFixed(1)}%
                      </div>
                    )}
                </div>
              </div>
            </label>
          );
        })}
      </div>

      <button
        onClick={handleConfirm}
        disabled={selectedKeys.size === 0 || confirming}
        className="w-full btn-primary disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
      >
        {confirming ? (
          <>
            <span className="spinner"></span>
            <span>Checking for duplicates...</span>
          </>
        ) : (
          <>
            <svg
              className="w-5 h-5 flex-shrink-0"
              width="20"
              height="20"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <span>
              Confirm Selection ({selectedKeys.size} key{selectedKeys.size !== 1 ? 's' : ''})
            </span>
          </>
        )}
      </button>
    </div>
  );
}
