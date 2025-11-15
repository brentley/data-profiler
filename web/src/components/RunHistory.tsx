import { useState, useEffect } from 'react';
import { api } from '../utils/api';
import { formatRelativeTime } from '../utils/date';
import type { RunStatus } from '../types/api';

interface RunHistoryProps {
  onSelectRun: (runId: string) => void;
  onError: (message: string) => void;
}

export function RunHistory({ onSelectRun, onError }: RunHistoryProps) {
  const [runs, setRuns] = useState<RunStatus[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadRuns();
  }, []);

  const loadRuns = async () => {
    setLoading(true);
    try {
      const runsData = await api.listRuns(20); // Get last 20 runs
      setRuns(runsData);
    } catch (err) {
      onError(err instanceof Error ? err.message : 'Failed to load run history');
    } finally {
      setLoading(false);
    }
  };

  const getStateIcon = (state: string) => {
    switch (state) {
      case 'completed':
        return (
          <svg className="w-4 h-4 text-green-500" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
          </svg>
        );
      case 'failed':
        return (
          <svg className="w-4 h-4 text-red-500" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
          </svg>
        );
      case 'processing':
        return (
          <svg className="w-4 h-4 text-blue-500 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
        );
      default:
        return (
          <svg className="w-4 h-4 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
          </svg>
        );
    }
  };

  const getStateLabel = (state: string) => {
    switch (state) {
      case 'completed':
        return <span className="text-xs px-2 py-0.5 rounded-full bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400">Completed</span>;
      case 'failed':
        return <span className="text-xs px-2 py-0.5 rounded-full bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400">Failed</span>;
      case 'processing':
        return <span className="text-xs px-2 py-0.5 rounded-full bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400">Processing</span>;
      default:
        return <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-400">Queued</span>;
    }
  };

  if (loading) {
    return (
      <div className="card">
        <h2 className="text-xl font-bold mb-4 text-gray-900 dark:text-gray-100">Previous Runs</h2>
        <div className="flex items-center justify-center py-8">
          <div className="spinner w-8 h-8 border-4"></div>
        </div>
      </div>
    );
  }

  if (runs.length === 0) {
    return (
      <div className="card">
        <h2 className="text-xl font-bold mb-4 text-gray-900 dark:text-gray-100">Previous Runs</h2>
        <p className="text-gray-600 dark:text-gray-400 text-center py-8">
          No previous runs found. Upload a file to get started.
        </p>
      </div>
    );
  }

  return (
    <div className="card">
      <h2 className="text-xl font-bold mb-4 text-gray-900 dark:text-gray-100">Previous Runs</h2>

      <div className="space-y-2 max-h-96 overflow-y-auto">
        {runs.map((run) => (
          <div
            key={run.run_id}
            className={`p-4 rounded-lg border cursor-pointer transition-all hover:shadow-md ${
              run.state === 'completed'
                ? 'border-gray-200 dark:border-slate-700 hover:border-blue-300 dark:hover:border-blue-600'
                : 'border-gray-200 dark:border-slate-700 opacity-75'
            }`}
            onClick={() => {
              if (run.state === 'completed') {
                onSelectRun(run.run_id);
              }
            }}
          >
            <div className="flex items-start justify-between">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  {getStateIcon(run.state)}
                  <span className="font-medium text-gray-900 dark:text-gray-100 truncate">
                    {run.source_filename || 'Unnamed file'}
                  </span>
                  {getStateLabel(run.state)}
                </div>

                <div className="flex flex-wrap gap-4 text-sm text-gray-600 dark:text-gray-400">
                  <span className="flex items-center gap-1">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    {formatRelativeTime(run.created_at)}
                  </span>

                  {run.row_count !== undefined && run.row_count > 0 && (
                    <span>
                      {run.row_count.toLocaleString()} rows × {run.column_count} columns
                    </span>
                  )}

                  {run.errors.length > 0 && (
                    <span className="text-red-600 dark:text-red-400">
                      {run.errors.length} error{run.errors.length !== 1 ? 's' : ''}
                    </span>
                  )}

                  {run.warnings.length > 0 && (
                    <span className="text-yellow-600 dark:text-yellow-400">
                      {run.warnings.length} warning{run.warnings.length !== 1 ? 's' : ''}
                    </span>
                  )}
                </div>
              </div>

              {run.state === 'completed' && (
                <svg className="w-5 h-5 text-gray-400 flex-shrink-0 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              )}
            </div>

            {run.state === 'processing' && run.progress_pct > 0 && (
              <div className="mt-2">
                <div className="w-full bg-gray-200 rounded-full h-1.5 dark:bg-gray-700">
                  <div
                    className="bg-blue-600 h-1.5 rounded-full transition-all"
                    style={{ width: `${run.progress_pct}%` }}
                  ></div>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="mt-4 text-xs text-gray-500 dark:text-gray-400 text-center">
        Showing last 20 runs. Click on a completed run to view its results.
      </div>
    </div>
  );
}