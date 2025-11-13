// Downloads section component
// Provides links to JSON, CSV, and HTML reports
import { api } from '../utils/api';

interface DownloadsProps {
  runId: string;
}

export function Downloads({ runId }: DownloadsProps) {
  const downloads = [
    {
      name: 'JSON Profile',
      description: 'Full profiling data in JSON format',
      url: api.getProfileJsonUrl(runId),
      icon: (
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"
          />
        </svg>
      ),
      color: 'text-blue-600 dark:text-blue-400',
      bgColor: 'bg-blue-50 dark:bg-blue-900/20',
    },
    {
      name: 'Metrics CSV',
      description: 'Per-column metrics in CSV format',
      url: api.getMetricsCsvUrl(runId),
      icon: (
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
          />
        </svg>
      ),
      color: 'text-green-600 dark:text-green-400',
      bgColor: 'bg-green-50 dark:bg-green-900/20',
    },
    {
      name: 'HTML Report',
      description: 'Interactive HTML report',
      url: api.getReportHtmlUrl(runId),
      icon: (
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
          />
        </svg>
      ),
      color: 'text-orange-600 dark:text-orange-400',
      bgColor: 'bg-orange-50 dark:bg-orange-900/20',
    },
  ];

  return (
    <div className="card">
      <h3 className="text-lg font-semibold mb-4">Download Reports</h3>

      <div className="space-y-3">
        {downloads.map((download) => (
          <a
            key={download.name}
            href={download.url}
            download
            className={`flex items-center gap-4 p-4 rounded-lg border-2 border-gray-200 dark:border-slate-700 hover:border-vq-primary dark:hover:border-vq-primary transition-all group`}
          >
            <div className={`${download.bgColor} ${download.color} p-3 rounded-lg`}>
              {download.icon}
            </div>
            <div className="flex-1 min-w-0">
              <h4 className="font-semibold text-gray-900 dark:text-gray-100 group-hover:text-vq-primary transition-colors">
                {download.name}
              </h4>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                {download.description}
              </p>
            </div>
            <svg
              className="w-5 h-5 text-gray-400 group-hover:text-vq-primary transition-colors"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
              />
            </svg>
          </a>
        ))}
      </div>

      <div className="mt-4 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
        <p className="text-sm text-blue-800 dark:text-blue-300">
          <strong>Tip:</strong> The JSON profile contains the complete profiling data,
          while the CSV is optimized for spreadsheet analysis.
        </p>
      </div>
    </div>
  );
}
