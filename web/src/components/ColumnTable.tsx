// Compact spreadsheet-like column profile display
import { useState } from 'react';
import type { ColumnProfile } from '../types/api';

interface ColumnTableProps {
  columns: ColumnProfile[];
  totalRows: number;
}

interface ExpandedRow {
  [key: number]: boolean;
}

export function ColumnTable({ columns, totalRows }: ColumnTableProps) {
  const [expandedRows, setExpandedRows] = useState<ExpandedRow>({});

  const toggleRow = (index: number) => {
    setExpandedRows(prev => ({
      ...prev,
      [index]: !prev[index]
    }));
  };

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

  const getNullPercentage = (column: ColumnProfile) => {
    return totalRows > 0 ? (column.null_count / totalRows) * 100 : 0;
  };

  return (
    <div className="card overflow-x-auto column-table-container">
      <table className="w-full text-sm column-table">
        <thead>
          <tr className="border-b-2 border-gray-300 dark:border-slate-600">
            <th className="text-left py-3 px-2 font-semibold text-gray-700 dark:text-gray-300">#</th>
            <th className="text-left py-3 px-3 font-semibold text-gray-700 dark:text-gray-300 min-w-[150px]">Column Name</th>
            <th className="text-left py-3 px-3 font-semibold text-gray-700 dark:text-gray-300">Type</th>
            <th className="text-right py-3 px-3 font-semibold text-gray-700 dark:text-gray-300">Null %</th>
            <th className="text-right py-3 px-3 font-semibold text-gray-700 dark:text-gray-300">Distinct</th>
            <th className="text-right py-3 px-3 font-semibold text-gray-700 dark:text-gray-300">Values</th>
            <th className="text-left py-3 px-3 font-semibold text-gray-700 dark:text-gray-300 min-w-[200px]">Top Values</th>
            <th className="text-center py-3 px-2 font-semibold text-gray-700 dark:text-gray-300 w-[40px]"></th>
          </tr>
        </thead>
        <tbody>
          {columns.map((column, index) => {
            const isExpanded = expandedRows[index];
            const nullPct = getNullPercentage(column);
            const topValuesPreview = column.top_values.slice(0, 3);
            const hasMore = column.top_values.length > 3;

            return (
              <tr
                key={index}
                className="border-b border-gray-200 dark:border-slate-700 hover:bg-gray-50 dark:hover:bg-slate-800/50 transition-colors"
              >
                {/* Column Number */}
                <td className="py-2 px-2 text-gray-600 dark:text-gray-400 font-mono text-xs">
                  {index + 1}
                </td>

                {/* Column Name */}
                <td className="py-2 px-3">
                  <div className="font-mono font-semibold text-gray-900 dark:text-gray-100 truncate" title={column.name}>
                    {column.name}
                  </div>
                </td>

                {/* Type */}
                <td className="py-2 px-3">
                  <span className={`badge text-xs ${getTypeColor(column.type)}`}>
                    {column.type}
                  </span>
                </td>

                {/* Null % */}
                <td className="py-2 px-3 text-right font-mono text-gray-900 dark:text-gray-100">
                  {nullPct.toFixed(1)}%
                </td>

                {/* Distinct Count */}
                <td className="py-2 px-3 text-right font-mono text-gray-900 dark:text-gray-100">
                  {formatNumber(column.distinct_count)}
                </td>

                {/* Values Count */}
                <td className="py-2 px-3 text-right font-mono text-gray-900 dark:text-gray-100">
                  {column.top_values.length}
                </td>

                {/* Top Values Column */}
                <td className="py-2 px-3">
                  <div className="space-y-1">
                    {/* Show first 3 values inline */}
                    {topValuesPreview.map((tv, i) => (
                      <div key={i} className="flex justify-between items-center text-xs">
                        <span className="font-mono text-gray-900 dark:text-gray-100 truncate mr-2 flex-1" title={tv.value || '<empty>'}>
                          {tv.value || '<empty>'}
                        </span>
                        <span className="text-gray-500 dark:text-gray-400 font-mono whitespace-nowrap">
                          ({formatNumber(tv.count)})
                        </span>
                      </div>
                    ))}

                    {/* Show more button */}
                    {hasMore && !isExpanded && (
                      <button
                        onClick={() => toggleRow(index)}
                        className="text-xs text-vq-primary hover:underline"
                      >
                        + {column.top_values.length - 3} more...
                      </button>
                    )}

                    {/* Expanded values */}
                    {isExpanded && column.top_values.slice(3).map((tv, i) => (
                      <div key={i + 3} className="flex justify-between items-center text-xs">
                        <span className="font-mono text-gray-900 dark:text-gray-100 truncate mr-2 flex-1" title={tv.value || '<empty>'}>
                          {tv.value || '<empty>'}
                        </span>
                        <span className="text-gray-500 dark:text-gray-400 font-mono whitespace-nowrap">
                          ({formatNumber(tv.count)})
                        </span>
                      </div>
                    ))}

                    {isExpanded && (
                      <button
                        onClick={() => toggleRow(index)}
                        className="text-xs text-vq-primary hover:underline"
                      >
                        Show less
                      </button>
                    )}
                  </div>
                </td>

                {/* Expand/Details Button */}
                <td className="py-2 px-2 text-center">
                  {(column.numeric_stats || column.date_stats || column.money_rules || column.length) && (
                    <button
                      onClick={() => toggleRow(index)}
                      className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition-colors"
                      aria-label={isExpanded ? 'Hide details' : 'Show details'}
                      title={isExpanded ? 'Hide details' : 'Show details'}
                    >
                      <svg
                        className={`w-5 h-5 flex-shrink-0 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
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
                          d="M19 9l-7 7-7-7"
                        />
                      </svg>
                    </button>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      {/* Expanded Details Rows (shown below each expanded row) */}
      {columns.map((column, index) => {
        const isExpanded = expandedRows[index];
        if (!isExpanded) return null;

        const hasDetails = column.numeric_stats || column.date_stats || column.money_rules || column.length;
        if (!hasDetails) return null;

        return (
          <div
            key={`details-${index}`}
            className="border-t-2 border-vq-primary/20 mt-4 pt-4 pb-2 bg-gray-50 dark:bg-slate-800/50 rounded-lg p-4"
          >
            <div className="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-3">
              Details for Column {index + 1}: {column.name}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {/* Length Stats */}
              {column.length && (
                <div>
                  <h4 className="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-2">
                    Length Statistics
                  </h4>
                  <div className="grid grid-cols-3 gap-2 text-xs">
                    <div className="p-2 bg-white dark:bg-slate-700 rounded text-center">
                      <div className="text-gray-500 dark:text-gray-400">Min</div>
                      <div className="font-semibold font-mono">{column.length.min}</div>
                    </div>
                    <div className="p-2 bg-white dark:bg-slate-700 rounded text-center">
                      <div className="text-gray-500 dark:text-gray-400">Avg</div>
                      <div className="font-semibold font-mono">{formatNumber(column.length.avg)}</div>
                    </div>
                    <div className="p-2 bg-white dark:bg-slate-700 rounded text-center">
                      <div className="text-gray-500 dark:text-gray-400">Max</div>
                      <div className="font-semibold font-mono">{column.length.max}</div>
                    </div>
                  </div>
                </div>
              )}

              {/* Numeric Stats */}
              {column.numeric_stats && (
                <div>
                  <h4 className="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-2">
                    Numeric Statistics
                  </h4>
                  <div className="space-y-1 text-xs">
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
                        <span className="text-gray-600 dark:text-gray-400">Gaussian p</span>
                        <span className="font-mono">{column.numeric_stats.gaussian_pvalue.toFixed(4)}</span>
                      </div>
                    )}
                  </div>

                  {/* Quantiles */}
                  {Object.keys(column.numeric_stats.quantiles).length > 0 && (
                    <div className="mt-2">
                      <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">Quantiles</div>
                      <div className="grid grid-cols-4 gap-1 text-xs">
                        {Object.entries(column.numeric_stats.quantiles).map(([key, value]) => (
                          <div key={key} className="p-1 bg-white dark:bg-slate-700 rounded text-center">
                            <div className="text-gray-500 dark:text-gray-400">{key}</div>
                            <div className="font-mono text-[10px]">{formatNumber(value)}</div>
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
                  <h4 className="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-2">
                    Money Validation
                  </h4>
                  <div className="space-y-1 text-xs">
                    <div className="flex justify-between items-center">
                      <span className="text-gray-600 dark:text-gray-400">Two decimals</span>
                      <span className={column.money_rules.two_decimal_ok ? 'badge badge-pass text-xs' : 'badge badge-fail text-xs'}>
                        {column.money_rules.two_decimal_ok ? 'OK' : 'FAIL'}
                      </span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-gray-600 dark:text-gray-400">No bad symbols</span>
                      <span className={!column.money_rules.disallowed_symbols_found ? 'badge badge-pass text-xs' : 'badge badge-fail text-xs'}>
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
                  <h4 className="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-2">
                    Date Statistics
                  </h4>
                  <div className="space-y-1 text-xs">
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
          </div>
        );
      })}
    </div>
  );
}
