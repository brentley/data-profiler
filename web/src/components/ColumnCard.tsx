// Column profile card with drill-down details
import { useState } from 'react';
import type { ColumnProfile, QualityData } from '../types/api';

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

  const getPatternLabel = (key: string): string => {
    const labels: Record<string, string> = {
      email: 'Email',
      phone_us: 'Phone',
      ssn_tin: 'SSN/TIN',
      zip_code_5: 'ZIP-5',
      zip_plus_4: 'ZIP+4',
      us_state_code: 'State',
      npi: 'NPI',
      npi_valid_checksum: 'NPI (Valid)',
      icd10_diagnosis: 'ICD-10 Dx',
      icd10_procedure: 'ICD-10 PCS',
      cpt_code: 'CPT',
    };
    return labels[key] || key;
  };

  const getPatternColor = (key: string): string => {
    if (['ssn_tin'].includes(key)) return 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400';
    if (['npi', 'npi_valid_checksum', 'icd10_diagnosis', 'icd10_procedure', 'cpt_code'].includes(key))
      return 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400';
    if (['zip_code_5', 'zip_plus_4', 'us_state_code'].includes(key))
      return 'bg-teal-100 text-teal-800 dark:bg-teal-900/30 dark:text-teal-400';
    return 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400';
  };

  const getQualityColorClass = (value: number): string => {
    if (value >= 95) return 'bg-green-500';
    if (value >= 80) return 'bg-yellow-500';
    return 'bg-red-500';
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

          {/* Data Quality */}
          {column.quality && (
            <div>
              <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Data Quality
              </h4>
              <div className="space-y-3 text-sm">
                {/* Completeness & Uniqueness Bars */}
                <div className="space-y-2">
                  <div>
                    <div className="flex justify-between mb-1">
                      <span className="text-gray-600 dark:text-gray-400">Completeness</span>
                      <span className="font-mono">{column.quality.completeness_pct.toFixed(1)}%</span>
                    </div>
                    <div className="bg-gray-200 dark:bg-slate-700 rounded-full h-2">
                      <div
                        className={`${getQualityColorClass(column.quality.completeness_pct)} rounded-full h-full transition-all`}
                        style={{ width: `${column.quality.completeness_pct}%` }}
                      />
                    </div>
                  </div>
                  <div>
                    <div className="flex justify-between mb-1">
                      <span className="text-gray-600 dark:text-gray-400">Uniqueness</span>
                      <span className="font-mono">{column.quality.uniqueness_pct.toFixed(1)}%</span>
                    </div>
                    <div className="bg-gray-200 dark:bg-slate-700 rounded-full h-2">
                      <div
                        className={`${getQualityColorClass(column.quality.uniqueness_pct)} rounded-full h-full transition-all`}
                        style={{ width: `${column.quality.uniqueness_pct}%` }}
                      />
                    </div>
                  </div>
                </div>

                {/* PHI Risk Flags */}
                {column.quality.phi_risk_flags.length > 0 && (
                  <div className="p-2 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded">
                    <div className="flex gap-2 items-start">
                      <svg className="w-4 h-4 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                      </svg>
                      <div>
                        <div className="text-red-800 dark:text-red-300 font-semibold">PHI Risk Flags:</div>
                        <div className="text-red-700 dark:text-red-400 mt-1 text-xs">
                          {column.quality.phi_risk_flags.join(', ')}
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Detected Patterns */}
                {Object.keys(column.quality.detected_patterns).length > 0 && (
                  <div>
                    <div className="text-gray-600 dark:text-gray-400 mb-1">Patterns Detected:</div>
                    <div className="flex flex-wrap gap-1">
                      {Object.entries(column.quality.detected_patterns).map(([pattern, count]) => (
                        <span
                          key={pattern}
                          className={`badge text-xs ${getPatternColor(pattern)}`}
                        >
                          {getPatternLabel(pattern)} ({formatNumber(count)})
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Whitespace Issues */}
                {(column.quality.leading_whitespace_count > 0 || column.quality.trailing_whitespace_count > 0) && (
                  <div className="p-2 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded">
                    <div className="flex gap-2 items-start">
                      <svg className="w-4 h-4 text-yellow-600 dark:text-yellow-400 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                      </svg>
                      <div>
                        <div className="text-yellow-800 dark:text-yellow-300">Whitespace Issues:</div>
                        <div className="text-yellow-700 dark:text-yellow-400 mt-1 text-xs space-y-1">
                          {column.quality.leading_whitespace_count > 0 && (
                            <div>Leading: {formatNumber(column.quality.leading_whitespace_count)}</div>
                          )}
                          {column.quality.trailing_whitespace_count > 0 && (
                            <div>Trailing: {formatNumber(column.quality.trailing_whitespace_count)}</div>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Outliers */}
                {column.quality.outlier_count > 0 && (
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">Outliers</span>
                    <span className="font-mono text-orange-600 dark:text-orange-400 font-semibold">
                      {formatNumber(column.quality.outlier_count)} ({column.quality.outlier_pct.toFixed(1)}%)
                    </span>
                  </div>
                )}

                {/* Empty Strings */}
                {column.quality.empty_string_count > 0 && (
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">Empty Strings</span>
                    <span className="font-mono">{formatNumber(column.quality.empty_string_count)}</span>
                  </div>
                )}

                {/* Entropy */}
                {column.quality.entropy !== null && (
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">
                      Entropy
                      <span className="ml-1 text-gray-400 dark:text-gray-500" title="Shannon entropy measures data diversity">?</span>
                    </span>
                    <span className="font-mono">{column.quality.entropy.toFixed(3)}</span>
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
