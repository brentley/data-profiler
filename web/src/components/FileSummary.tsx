// File summary component
// Shows high-level file metrics
import type { FileInfo } from '../types/api';

interface FileSummaryProps {
  fileInfo: FileInfo;
}

export function FileSummary({ fileInfo }: FileSummaryProps) {
  return (
    <div className="card">
      <h3 className="text-lg font-semibold mb-4">File Summary</h3>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
        <div className="text-center p-4 bg-gray-50 dark:bg-slate-700/50 rounded-lg">
          <div className="text-2xl font-bold text-vq-primary">
            {fileInfo.rows.toLocaleString()}
          </div>
          <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            Rows
          </div>
        </div>

        <div className="text-center p-4 bg-gray-50 dark:bg-slate-700/50 rounded-lg">
          <div className="text-2xl font-bold text-vq-primary">
            {fileInfo.columns.toLocaleString()}
          </div>
          <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            Columns
          </div>
        </div>

        <div className="text-center p-4 bg-gray-50 dark:bg-slate-700/50 rounded-lg">
          <div className="text-2xl font-bold font-mono">
            {fileInfo.delimiter === '|' ? '|' : ','}
          </div>
          <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            Delimiter
          </div>
        </div>

        <div className="text-center p-4 bg-gray-50 dark:bg-slate-700/50 rounded-lg">
          <div className="text-2xl font-bold">
            {fileInfo.crlf_detected ? (
              <span className="badge badge-pass">CRLF</span>
            ) : (
              <span className="badge badge-info">LF</span>
            )}
          </div>
          <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            Line Ending
          </div>
        </div>
      </div>

      {/* Header Row */}
      <div>
        <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Header ({fileInfo.header.length} columns)
        </h4>
        <div className="max-h-32 overflow-y-auto border border-gray-200 dark:border-slate-700 rounded-lg p-3 bg-gray-50 dark:bg-slate-700/50">
          <div className="flex flex-wrap gap-2">
            {fileInfo.header.map((col, index) => (
              <span
                key={index}
                className="inline-flex items-center px-2 py-1 rounded bg-white dark:bg-slate-800 text-xs font-mono border border-gray-200 dark:border-slate-600"
                title={col}
              >
                {col}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
