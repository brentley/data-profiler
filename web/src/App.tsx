// VQ8 Data Profiler Main Application
import { useState, useEffect } from 'react';
import { initializeTheme, setStoredTheme, applyTheme, type Theme } from './utils/theme';
import { useToast } from './hooks/useToast';
import { ToastContainer } from './components/Toast';
import { UploadForm } from './components/UploadForm';
import { RunStatus } from './components/RunStatus';
import { FileSummary } from './components/FileSummary';
import { ErrorRollup } from './components/ErrorRollup';
import { CandidateKeys } from './components/CandidateKeys';
import { ColumnCard } from './components/ColumnCard';
import { Downloads } from './components/Downloads';
import { api } from './utils/api';
import type { Profile } from './types/api';
import './App.css';

type AppState = 'upload' | 'processing' | 'results';

function App() {
  const [appState, setAppState] = useState<AppState>('upload');
  const [currentRunId, setCurrentRunId] = useState<string | null>(null);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [theme, setTheme] = useState<Theme>('dark');
  const [loading, setLoading] = useState(false);
  const { toasts, success, error, warning, info } = useToast();

  // Initialize theme on mount
  useEffect(() => {
    const currentTheme = initializeTheme();
    setTheme(currentTheme);
  }, []);

  const handleThemeChange = (newTheme: Theme) => {
    setTheme(newTheme);
    setStoredTheme(newTheme);
    applyTheme(newTheme);
  };

  const handleUploadStart = (runId: string) => {
    setCurrentRunId(runId);
    setAppState('processing');
    info('Upload Started', 'Your file is being processed...');
  };

  const handleProcessingComplete = async () => {
    if (!currentRunId) return;

    setLoading(true);
    try {
      const profileData = await api.getProfile(currentRunId);
      setProfile(profileData);
      setAppState('results');
      success('Profiling Complete', 'Your data has been analyzed successfully.');
    } catch (err) {
      error(
        'Failed to Load Profile',
        err instanceof Error ? err.message : 'Please try again.'
      );
    } finally {
      setLoading(false);
    }
  };

  const handleKeysConfirmed = () => {
    success(
      'Keys Confirmed',
      'Duplicate check is running. Refresh the page to see updated results.'
    );
  };

  const handleReset = () => {
    setAppState('upload');
    setCurrentRunId(null);
    setProfile(null);
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-900 transition-colors">
      {/* Header */}
      <header className="bg-white dark:bg-slate-800 shadow-sm border-b border-gray-200 dark:border-slate-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3 sm:py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 sm:gap-3">
              <div className="w-9 h-9 sm:w-10 sm:h-10 bg-vq-primary rounded-lg flex items-center justify-center flex-shrink-0">
                <svg
                  className="w-5 h-5 sm:w-6 sm:h-6 text-white"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                  />
                </svg>
              </div>
              <div className="min-w-0">
                <h1 className="text-lg sm:text-xl font-bold text-gray-900 dark:text-gray-100 truncate">
                  VQ8 Data Profiler
                </h1>
                <p className="text-xs sm:text-sm text-gray-600 dark:text-gray-400 hidden sm:block">
                  CSV/TXT File Analysis Tool
                </p>
              </div>
            </div>

            {/* Theme Toggle */}
            <div className="flex items-center gap-1.5 sm:gap-2">
              {appState === 'results' && (
                <button
                  onClick={handleReset}
                  className="px-3 py-1.5 sm:px-4 sm:py-2 text-xs sm:text-sm font-medium text-gray-700 dark:text-gray-300 hover:text-vq-primary dark:hover:text-vq-primary transition-colors rounded-lg hover:bg-gray-100 dark:hover:bg-slate-700"
                >
                  <span className="hidden sm:inline">New Upload</span>
                  <span className="sm:hidden">New</span>
                </button>
              )}
              <button
                onClick={() => handleThemeChange(theme === 'dark' ? 'light' : 'dark')}
                className="p-2 rounded-lg bg-gray-100 dark:bg-slate-700 hover:bg-gray-200 dark:hover:bg-slate-600 transition-colors"
                aria-label="Toggle theme"
              >
                {theme === 'dark' ? (
                  <svg className="w-5 h-5 text-yellow-500" fill="currentColor" viewBox="0 0 20 20">
                    <path
                      fillRule="evenodd"
                      d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4 8a4 4 0 11-8 0 4 4 0 018 0zm-.464 4.95l.707.707a1 1 0 001.414-1.414l-.707-.707a1 1 0 00-1.414 1.414zm2.12-10.607a1 1 0 010 1.414l-.706.707a1 1 0 11-1.414-1.414l.707-.707a1 1 0 011.414 0zM17 11a1 1 0 100-2h-1a1 1 0 100 2h1zm-7 4a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1zM5.05 6.464A1 1 0 106.465 5.05l-.708-.707a1 1 0 00-1.414 1.414l.707.707zm1.414 8.486l-.707.707a1 1 0 01-1.414-1.414l.707-.707a1 1 0 011.414 1.414zM4 11a1 1 0 100-2H3a1 1 0 000 2h1z"
                      clipRule="evenodd"
                    />
                  </svg>
                ) : (
                  <svg className="w-5 h-5 text-slate-700" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M17.293 13.293A8 8 0 016.707 2.707a8.001 8.001 0 1010.586 10.586z" />
                  </svg>
                )}
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
        {appState === 'upload' && (
          <div className="max-w-2xl mx-auto">
            <div className="card card-lg">
              <h2 className="text-2xl font-bold mb-2 text-gray-900 dark:text-gray-100">Upload Your Data File</h2>
              <p className="text-gray-600 dark:text-gray-400 mb-6">
                Upload a CSV or TXT file (optionally gzipped) to analyze its structure,
                validate data quality, and generate detailed profiling reports.
              </p>
              <UploadForm
                onUploadStart={handleUploadStart}
                onError={(msg) => error('Upload Error', msg)}
              />
            </div>

            {/* Features */}
            <div className="mt-6 grid md:grid-cols-3 gap-4">
              <div className="card text-center p-6">
                <div className="w-12 h-12 bg-blue-100 dark:bg-blue-900/30 text-vq-primary rounded-lg flex items-center justify-center mx-auto mb-3">
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <h3 className="font-semibold mb-1.5 text-gray-900 dark:text-gray-100">Data Validation</h3>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Comprehensive validation rules and error detection
                </p>
              </div>

              <div className="card text-center p-6">
                <div className="w-12 h-12 bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400 rounded-lg flex items-center justify-center mx-auto mb-3">
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                </div>
                <h3 className="font-semibold mb-1.5 text-gray-900 dark:text-gray-100">Column Profiling</h3>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Detailed statistics and type inference for every column
                </p>
              </div>

              <div className="card text-center p-6">
                <div className="w-12 h-12 bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400 rounded-lg flex items-center justify-center mx-auto mb-3">
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
                  </svg>
                </div>
                <h3 className="font-semibold mb-1.5 text-gray-900 dark:text-gray-100">Key Detection</h3>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Automatic candidate key suggestions and duplicate detection
                </p>
              </div>
            </div>
          </div>
        )}

        {appState === 'processing' && currentRunId && (
          <div className="max-w-2xl mx-auto">
            <RunStatus
              runId={currentRunId}
              onComplete={handleProcessingComplete}
              onError={(msg) => error('Processing Error', msg)}
              onWarning={(msg) => warning('Warning', msg)}
            />
          </div>
        )}

        {appState === 'results' && profile && currentRunId && (
          <div className="space-y-6">
            {/* File Summary */}
            <FileSummary fileInfo={profile.file} />

            {/* Error Roll-up */}
            <ErrorRollup errors={profile.errors} warnings={profile.warnings} />

            {/* Candidate Keys */}
            {profile.candidate_keys.length > 0 && (
              <CandidateKeys
                runId={currentRunId}
                candidateKeys={profile.candidate_keys}
                onKeysConfirmed={handleKeysConfirmed}
                onError={(msg) => error('Error', msg)}
              />
            )}

            {/* Column Profiles */}
            <div>
              <h2 className="text-2xl font-bold mb-4 text-gray-900 dark:text-gray-100">
                Column Profiles
              </h2>
              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                {profile.columns.map((column, index) => (
                  <ColumnCard key={index} column={column} index={index} />
                ))}
              </div>
            </div>

            {/* Downloads */}
            <Downloads runId={currentRunId} />
          </div>
        )}

        {loading && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="card">
              <div className="flex items-center gap-3">
                <div className="spinner w-6 h-6 border-4"></div>
                <span className="text-lg font-medium">Loading profile...</span>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="mt-8 sm:mt-12 py-4 sm:py-6 border-t border-gray-200 dark:border-slate-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <p className="text-center text-xs sm:text-sm text-gray-500 dark:text-gray-400">
            VQ8 Data Profiler v1.0.0 | Built with VisiQuate UI Standards
          </p>
        </div>
      </footer>

      {/* Toast Notifications */}
      <ToastContainer toasts={toasts} />
    </div>
  );
}

export default App;
