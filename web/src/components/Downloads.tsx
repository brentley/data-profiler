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
      fileType: 'JSON',
      icon: (
        <svg className="flex-shrink-0 w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" width="24" height="24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"
          />
        </svg>
      ),
      color: 'text-[#116df8]',
      bgColor: 'bg-[#116df8]/10 dark:bg-[#116df8]/20',
      badgeColor: 'bg-[#116df8] text-white',
      borderHover: 'hover:border-[#116df8] hover:shadow-[#116df8]/20',
    },
    {
      name: 'Metrics CSV',
      description: 'Per-column metrics in CSV format',
      url: api.getMetricsCsvUrl(runId),
      fileType: 'CSV',
      icon: (
        <svg className="flex-shrink-0 w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" width="24" height="24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M3 10h18M3 14h18m-9-4v8m-7 0h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"
          />
        </svg>
      ),
      color: 'text-emerald-600 dark:text-emerald-400',
      bgColor: 'bg-emerald-50 dark:bg-emerald-900/20',
      badgeColor: 'bg-emerald-600 dark:bg-emerald-500 text-white',
      borderHover: 'hover:border-emerald-500 hover:shadow-emerald-500/20',
    },
    {
      name: 'HTML Report',
      description: 'Interactive HTML report',
      url: api.getReportHtmlUrl(runId),
      fileType: 'HTML',
      icon: (
        <svg className="flex-shrink-0 w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" width="24" height="24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
          />
        </svg>
      ),
      color: 'text-[#ff5100]',
      bgColor: 'bg-[#ff5100]/10 dark:bg-[#ff5100]/20',
      badgeColor: 'bg-[#ff5100] text-white',
      borderHover: 'hover:border-[#ff5100] hover:shadow-[#ff5100]/20',
    },
  ];

  return (
    <div className="card">
      <h3 className="text-lg font-semibold mb-4">Download Reports</h3>

      <div className="space-y-2.5">
        {downloads.map((download) => (
          <a
            key={download.name}
            href={download.url}
            download
            className={`download-card flex items-center gap-3 p-3.5 rounded-lg border-2 border-gray-200 dark:border-slate-700 ${download.borderHover} transition-all duration-200 group hover:shadow-lg`}
          >
            <div className={`${download.bgColor} ${download.color} p-2.5 rounded-lg transition-transform group-hover:scale-110 duration-200`}>
              {download.icon}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-0.5">
                <h4 className="font-semibold text-gray-900 dark:text-gray-100 group-hover:text-gray-700 dark:group-hover:text-white transition-colors">
                  {download.name}
                </h4>
                <span className={`text-xs font-semibold px-2 py-0.5 rounded ${download.badgeColor}`}>
                  {download.fileType}
                </span>
              </div>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                {download.description}
              </p>
            </div>
            <svg
              className={`flex-shrink-0 w-5 h-5 text-gray-400 ${download.color} transition-all group-hover:translate-y-0.5`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              width="20"
              height="20"
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

      <div className="mt-4 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-100 dark:border-blue-800/30">
        <p className="text-sm text-blue-800 dark:text-blue-300">
          <strong>Tip:</strong> The JSON profile contains the complete profiling data,
          while the CSV is optimized for spreadsheet analysis.
        </p>
      </div>
    </div>
  );
}
