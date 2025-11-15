// Column profile card with drill-down details
import { useState } from 'react';
import type { ColumnProfile } from '../types/api';

interface ColumnCardProps {
  column: ColumnProfile;
  index: number;
  totalRows: number;
}

export function ColumnCard({ column, index, totalRows }: ColumnCardProps) {
  const [expanded, setExpanded] = useState(false);

  // Calculate null percentage from null count and total rows
  const nullPct = totalRows > 0 ? (column.null_count / totalRows) * 100 : 0;

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'numeric':
      case 'money':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400';
      case 'date':
        return 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400';
      case 'code':
        return 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400';
      case 'mixed':
        return 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400';
      case 'unknown':
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400';
      default:
        return 'bg-teal-100 text-teal-800 dark:bg-teal-900/30 dark:text-teal-400';
    }
  };

  const formatNumber = (num: number) => {
    return num.toLocaleString(undefined, { maximumFractionDigits: 2 });
  };

  return (
    <div className="card">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xs font-medium text-gray-500 dark:text-gray-400">
              Column {index + 1}
            </span>
            <span className={`badge ${getTypeColor(column.type)}`}>
              {column.type}
            </span>
          </div>
          <h3 className="text-lg font-semibold font-mono truncate" title={column.name}>
            {column.name}
          </h3>
        </div>
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex-shrink-0 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition-colors"
          aria-label={expanded ? 'Collapse' : 'Expand'}
        >
          <svg
            className={`w-6 h-6 flex-shrink-0 transition-transform ${expanded ? 'rotate-180' : ''}`}
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
              d="M19 9l-7 7-7-7"
            />
          </svg>
        </button>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-3 gap-3 mb-4">
        <div className="text-center p-3 bg-gray-50 dark:bg-slate-700/50 rounded">
          <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">
            Null %
          </div>
          <div className="text-lg font-semibold">
            {nullPct.toFixed(1)}%
          </div>
        </div>
        <div className="text-center p-3 bg-gray-50 dark:bg-slate-700/50 rounded">
          <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">
            Distinct
          </div>
          <div className="text-lg font-semibold">
            {formatNumber(column.distinct_count)}
          </div>
        </div>
        <div className="text-center p-3 bg-gray-50 dark:bg-slate-700/50 rounded">
          <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">
            {column.length ? 'Avg Len' : 'Values'}
          </div>
          <div className="text-lg font-semibold">
            {column.length ? formatNumber(column.length.avg) : column.top_values.length}
          </div>
        </div>
      </div>

      {/* Top Values */}
      {column.top_values.length > 0 && (
        <div className="mb-4">
          <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Top {column.top_values.length} Values
          </h4>
          <div className="space-y-2">
            {column.top_values.slice(0, expanded ? undefined : 3).map((tv, i) => {
              const percentage =
                (tv.count / column.top_values.reduce((sum, v) => sum + v.count, 0)) * 100;
              return (
                <div key={i} className="flex items-center gap-2">
                  <div className="flex-1 min-w-0">
                    <div className="flex justify-between text-sm mb-1">
                      <span className="font-mono text-gray-900 dark:text-gray-100 truncate">
                        {tv.value || '<empty>'}
                      </span>
                      <span className="text-gray-500 dark:text-gray-400 ml-2">
                        {formatNumber(tv.count)}
                      </span>
                    </div>
                    <div className="h-2 bg-gray-200 dark:bg-slate-700 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-vq-primary rounded-full transition-all"
                        style={{ width: `${percentage}%` }}
                      />
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
          {!expanded && column.top_values.length > 3 && (
            <button
              onClick={() => setExpanded(true)}
              className="text-sm text-vq-primary hover:underline mt-2"
            >
              Show {column.top_values.length - 3} more...
            </button>
          )}
        </div>
      )}

      {/* Expanded Details */}
      {expanded && (
        <div className="space-y-4 pt-4 border-t border-gray-200 dark:border-slate-700">
          {/* Length Stats */}
          {column.length && (
            <div>
              <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Length Statistics
              </h4>
              <div className="grid grid-cols-3 gap-3">
                <div className="p-2 bg-gray-50 dark:bg-slate-700/50 rounded text-center">
                  <div className="text-xs text-gray-500 dark:text-gray-400">Min</div>
                  <div className="font-semibold">{column.length.min}</div>
                </div>
                <div className="p-2 bg-gray-50 dark:bg-slate-700/50 rounded text-center">
                  <div className="text-xs text-gray-500 dark:text-gray-400">Avg</div>
                  <div className="font-semibold">{formatNumber(column.length.avg)}</div>
                </div>
                <div className="p-2 bg-gray-50 dark:bg-slate-700/50 rounded text-center">
                  <div className="text-xs text-gray-500 dark:text-gray-400">Max</div>
                  <div className="font-semibold">{column.length.max}</div>
                </div>
              </div>
            </div>
          )}

          {/* Numeric Stats */}
          {column.numeric_stats && (
            <div>
              <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Numeric Statistics
              </h4>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600 dark:text-gray-400">Range</span>
                  <span className="font-mono">
                    {formatNumber(column.numeric_stats.min)} – {formatNumber(column.numeric_stats.max)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600 dark:text-gray-400">Mean</span>
                  <span className="font-mono">{formatNumber(column.numeric_stats.mean)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600 dark:text-gray-400">Median</span>
                  <span className="font-mono">{formatNumber(column.numeric_stats.median)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600 dark:text-gray-400">Std Dev</span>
                  <span className="font-mono">{formatNumber(column.numeric_stats.stddev)}</span>
                </div>
                {column.numeric_stats.gaussian_pvalue !== undefined && (
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">Gaussian p-value</span>
                    <span className="font-mono">{column.numeric_stats.gaussian_pvalue.toFixed(4)}</span>
                  </div>
                )}
              </div>

              {/* Quantiles */}
              {Object.keys(column.numeric_stats.quantiles).length > 0 && (
                <div className="mt-3">
                  <div className="text-xs text-gray-500 dark:text-gray-400 mb-2">Quantiles</div>
                  <div className="grid grid-cols-4 gap-2 text-xs">
                    {Object.entries(column.numeric_stats.quantiles).map(([key, value]) => (
                      <div key={key} className="p-2 bg-gray-50 dark:bg-slate-700/50 rounded text-center">
                        <div className="text-gray-500 dark:text-gray-400">{key}</div>
                        <div className="font-mono">{formatNumber(value)}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Money Rules */}
          {column.money_rules && (
            <div>
              <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Money Validation
              </h4>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between items-center">
                  <span className="text-gray-600 dark:text-gray-400">Two decimals</span>
                  <span className={column.money_rules.two_decimal_ok ? 'badge badge-pass' : 'badge badge-fail'}>
                    {column.money_rules.two_decimal_ok ? 'OK' : 'FAIL'}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-600 dark:text-gray-400">No disallowed symbols</span>
                  <span className={!column.money_rules.disallowed_symbols_found ? 'badge badge-pass' : 'badge badge-fail'}>
                    {!column.money_rules.disallowed_symbols_found ? 'OK' : 'FAIL'}
                  </span>
                </div>
                {column.money_rules.violations_count > 0 && (
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">Violations</span>
                    <span className="text-red-600 dark:text-red-400 font-semibold">
                      {formatNumber(column.money_rules.violations_count)}
                    </span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Date Stats */}
          {column.date_stats && (
            <div>
              <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Date Statistics
              </h4>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600 dark:text-gray-400">Format</span>
                  <span className="font-mono">{column.date_stats.detected_format}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600 dark:text-gray-400">Range</span>
                  <span className="font-mono">
                    {column.date_stats.min} – {column.date_stats.max}
                  </span>
                </div>
                {column.date_stats.out_of_range_count > 0 && (
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">Out of range</span>
                    <span className="text-yellow-600 dark:text-yellow-400 font-semibold">
                      {formatNumber(column.date_stats.out_of_range_count)}
                    </span>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
