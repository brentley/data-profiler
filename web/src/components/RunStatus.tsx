// Run status component with real-time polling
import { useEffect, useState } from 'react';
import { api } from '../utils/api';
import type { RunStatus as RunStatusType } from '../types/api';

interface RunStatusProps {
  runId: string;
  onComplete: () => void;
  onError: (message: string) => void;
  onWarning: (message: string) => void;
}

export function RunStatus({
  runId,
  onComplete,
  onError,
  onWarning,
}: RunStatusProps) {
  const [status, setStatus] = useState<RunStatusType | null>(null);
  const [loading, setLoading] = useState(true);
  const [errorCount, setErrorCount] = useState(0);
  const [warningCount, setWarningCount] = useState(0);

  useEffect(() => {
    let intervalId: number | null = null;
    let lastErrorCount = 0;
    let lastWarningCount = 0;

    const pollStatus = async () => {
      try {
        const data = await api.getRunStatus(runId);
        setStatus(data);
        setLoading(false);

        // Aggregate error notifications (don't spam)
        const currentErrorCount = data.errors.reduce(
          (sum, err) => sum + err.count,
          0
        );
        if (currentErrorCount > lastErrorCount) {
          const newErrors = currentErrorCount - lastErrorCount;
          onError(
            `${newErrors} new error${newErrors > 1 ? 's' : ''} detected. See error roll-up for details.`
          );
          lastErrorCount = currentErrorCount;
        }

        // Aggregate warning notifications
        const currentWarningCount = data.warnings.reduce(
          (sum, warn) => sum + warn.count,
          0
        );
        if (currentWarningCount > lastWarningCount) {
          const newWarnings = currentWarningCount - lastWarningCount;
          onWarning(
            `${newWarnings} new warning${newWarnings > 1 ? 's' : ''} detected.`
          );
          lastWarningCount = currentWarningCount;
        }

        setErrorCount(currentErrorCount);
        setWarningCount(currentWarningCount);

        // Stop polling when completed or failed
        if (data.state === 'completed' || data.state === 'failed') {
          if (intervalId) clearInterval(intervalId);
          if (data.state === 'completed') {
            onComplete();
          } else {
            onError('Profiling failed. Check error roll-up for details.');
          }
        }
      } catch (err) {
        console.error('Failed to fetch run status:', err);
        setLoading(false);
      }
    };

    // Initial poll
    pollStatus();

    // Poll every 2 seconds while processing
    intervalId = window.setInterval(pollStatus, 2000);

    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [runId, onComplete, onError, onWarning]);

  if (loading) {
    return (
      <div className="card flex items-center justify-center py-12">
        <div className="text-center">
          <div className="spinner w-8 h-8 border-4 mx-auto mb-4"></div>
          <p className="text-gray-600 dark:text-gray-400">
            Loading status...
          </p>
        </div>
      </div>
    );
  }

  if (!status) {
    return (
      <div className="card">
        <p className="text-red-600 dark:text-red-400">
          Failed to load run status
        </p>
      </div>
    );
  }

  const getStateColor = (state: string) => {
    switch (state) {
      case 'queued':
        return 'text-blue-600 dark:text-blue-400';
      case 'processing':
        return 'text-yellow-600 dark:text-yellow-400';
      case 'completed':
        return 'text-green-600 dark:text-green-400';
      case 'failed':
        return 'text-red-600 dark:text-red-400';
      default:
        return 'text-gray-600 dark:text-gray-400';
    }
  };

  const getStateBadge = (state: string) => {
    switch (state) {
      case 'queued':
        return <span className="badge badge-info">Queued</span>;
      case 'processing':
        return <span className="badge badge-warn">Processing</span>;
      case 'completed':
        return <span className="badge badge-pass">Completed</span>;
      case 'failed':
        return <span className="badge badge-fail">Failed</span>;
      default:
        return <span className="badge">{state}</span>;
    }
  };

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold">Profiling Status</h2>
        {getStateBadge(status.state)}
      </div>

      {/* Progress Bar */}
      <div className="mb-6">
        <div className="flex justify-between text-sm mb-2">
          <span className="text-gray-600 dark:text-gray-400">Progress</span>
          <span className={`font-medium ${getStateColor(status.state)}`}>
            {status.progress_pct.toFixed(1)}%
          </span>
        </div>
        <div className="w-full bg-gray-200 dark:bg-slate-700 rounded-full h-3 overflow-hidden">
          <div
            className="progress-bar h-full"
            style={{ width: `${status.progress_pct}%` }}
            role="progressbar"
            aria-valuenow={status.progress_pct}
            aria-valuemin={0}
            aria-valuemax={100}
          />
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-2 gap-4">
        <div className="text-center p-4 bg-gray-50 dark:bg-slate-700/50 rounded-lg">
          <div className="text-2xl font-bold text-red-600 dark:text-red-400">
            {errorCount}
          </div>
          <div className="text-sm text-gray-600 dark:text-gray-400">
            Errors
          </div>
        </div>
        <div className="text-center p-4 bg-gray-50 dark:bg-slate-700/50 rounded-lg">
          <div className="text-2xl font-bold text-yellow-600 dark:text-yellow-400">
            {warningCount}
          </div>
          <div className="text-sm text-gray-600 dark:text-gray-400">
            Warnings
          </div>
        </div>
      </div>

      {/* Processing Animation */}
      {status.state === 'processing' && (
        <div className="mt-6 flex items-center justify-center gap-2 text-gray-600 dark:text-gray-400">
          <span className="spinner"></span>
          <span className="text-sm">Analyzing your data...</span>
        </div>
      )}
    </div>
  );
}
