// Error roll-up table component
// Shows aggregated error codes with counts and color coding
import type { ErrorItem } from '../types/api';

interface ErrorRollupProps {
  errors: ErrorItem[];
  warnings: ErrorItem[];
}

export function ErrorRollup({ errors, warnings }: ErrorRollupProps) {
  if (errors.length === 0 && warnings.length === 0) {
    return (
      <div className="card">
        <div className="flex items-center gap-3">
          <span className="badge badge-pass text-lg">✓</span>
          <div>
            <h3 className="font-semibold text-green-600 dark:text-green-400">
              No Issues Detected
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              All validation checks passed successfully
            </p>
          </div>
        </div>
      </div>
    );
  }

  const getCriticality = (code: string): 'catastrophic' | 'error' | 'warning' => {
    if (code.startsWith('E_UTF8') || code.startsWith('E_HEADER') || code.startsWith('E_JAGGED')) {
      return 'catastrophic';
    }
    if (code.startsWith('E_')) {
      return 'error';
    }
    return 'warning';
  };

  const getCriticalityBadge = (code: string) => {
    const level = getCriticality(code);
    switch (level) {
      case 'catastrophic':
        return <span className="badge badge-fail">Catastrophic</span>;
      case 'error':
        return <span className="badge badge-fail">Error</span>;
      case 'warning':
        return <span className="badge badge-warn">Warning</span>;
    }
  };

  const allIssues = [
    ...errors.map((e) => ({ ...e, type: 'error' as const })),
    ...warnings.map((w) => ({ ...w, type: 'warning' as const })),
  ].sort((a, b) => b.count - a.count); // Sort by count descending

  const totalErrors = errors.reduce((sum, err) => sum + err.count, 0);
  const totalWarnings = warnings.reduce((sum, warn) => sum + warn.count, 0);

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold">Issue Roll-up</h3>
        <div className="flex gap-3">
          {totalErrors > 0 && (
            <span className="badge badge-fail">{totalErrors} Error{totalErrors !== 1 ? 's' : ''}</span>
          )}
          {totalWarnings > 0 && (
            <span className="badge badge-warn">{totalWarnings} Warning{totalWarnings !== 1 ? 's' : ''}</span>
          )}
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50 dark:bg-slate-700/50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Severity
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Code
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Message
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Count
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-slate-700">
            {allIssues.map((issue, index) => (
              <tr
                key={`${issue.code}-${index}`}
                className="hover:bg-gray-50 dark:hover:bg-slate-700/50 transition-colors"
              >
                <td className="px-4 py-3 whitespace-nowrap">
                  {getCriticalityBadge(issue.code)}
                </td>
                <td className="px-4 py-3 whitespace-nowrap">
                  <code className="text-sm font-mono bg-gray-100 dark:bg-slate-900 px-2 py-1 rounded">
                    {issue.code}
                  </code>
                </td>
                <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">
                  {issue.message}
                </td>
                <td className="px-4 py-3 text-right whitespace-nowrap">
                  <span className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                    {issue.count.toLocaleString()}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Legend */}
      <div className="mt-4 pt-4 border-t border-gray-200 dark:border-slate-700">
        <p className="text-xs text-gray-500 dark:text-gray-400">
          <strong>Catastrophic errors</strong> stop processing immediately.{' '}
          <strong>Non-catastrophic errors</strong> are counted and reported but don't halt the profiling process.
        </p>
      </div>
    </div>
  );
}
