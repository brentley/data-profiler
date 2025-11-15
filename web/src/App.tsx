// VQ8 Data Profiler Main Application
import { useState, useEffect } from 'react';
import { useToast } from './hooks/useToast';
import { ToastContainer } from './components/Toast';
import { UploadForm } from './components/UploadForm';
import { RunStatus } from './components/RunStatus';
import { RunHistory } from './components/RunHistory';
import { FileSummary } from './components/FileSummary';
import { ErrorRollup } from './components/ErrorRollup';
import { CandidateKeys } from './components/CandidateKeys';
import { ColumnTable } from './components/ColumnTable';
import { Downloads } from './components/Downloads';
import { api } from './utils/api';
import type { Profile } from './types/api';
import './App.css';

type AppState = 'upload' | 'processing' | 'results';

function App() {
  const [appState, setAppState] = useState<AppState>('upload');
  const [currentRunId, setCurrentRunId] = useState<string | null>(null);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(false);
  const { toasts, success, error, warning, info } = useToast();

  // Force dark mode on mount
  useEffect(() => {
    document.documentElement.classList.add('dark');
  }, []);

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

  const handleSelectHistoricRun = async (runId: string) => {
    setCurrentRunId(runId);
    setLoading(true);
    try {
      const profileData = await api.getProfile(runId);
      setProfile(profileData);
      setAppState('results');
      info('Run Loaded', 'Historical run data has been loaded successfully.');
    } catch (err) {
      error(
        'Failed to Load Run',
        err instanceof Error ? err.message : 'Please try again.'
      );
      setAppState('upload');
    } finally {
      setLoading(false);
    }
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
                  className="w-5 h-5 sm:w-6 sm:h-6 text-white flex-shrink-0"
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

            {/* Header Actions */}
            {appState === 'results' && (
              <button
                onClick={handleReset}
                className="px-3 py-1.5 sm:px-4 sm:py-2 text-xs sm:text-sm font-medium text-vq-accent hover:text-orange-600 dark:text-vq-accent dark:hover:text-orange-400 transition-colors rounded-lg hover:bg-orange-50 dark:hover:bg-orange-900/20"
              >
                <span className="hidden sm:inline">New Upload</span>
                <span className="sm:hidden">New</span>
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
        {appState === 'upload' && (
          <div className="space-y-6">
            {/* Run History - constrained width */}
            <div className="max-w-5xl mx-auto">
              <RunHistory
                onSelectRun={handleSelectHistoricRun}
                onError={(msg) => error('Error', msg)}
              />
            </div>

            {/* Upload Form - constrained width */}
            <div className="max-w-5xl mx-auto">
              <div className="card card-lg">
                <h2 className="text-2xl font-bold mb-2 text-gray-900 dark:text-gray-100">Upload New File</h2>
                <p className="text-gray-600 dark:text-gray-400 mb-6">
                  Upload your CSV or TXT file (optionally gzipped) for automatic analysis.
                  File format, delimiter, and encoding will be detected automatically.
                </p>
                <UploadForm
                  onUploadStart={handleUploadStart}
                  onError={(msg) => error('Upload Error', msg)}
                />
              </div>
            </div>

            {/* Features - constrained width, always 3 columns on larger screens */}
            <div className="max-w-5xl mx-auto">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="card text-center p-6">
                  <div className="w-10 h-10 bg-blue-100 dark:bg-blue-900/30 text-vq-primary rounded-lg flex items-center justify-center mx-auto mb-3">
                    <svg className="w-5 h-5 flex-shrink-0" width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                  <h3 className="font-semibold mb-1.5 text-gray-900 dark:text-gray-100">Data Validation</h3>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    Comprehensive validation rules and error detection
                  </p>
                </div>

                <div className="card text-center p-6">
                  <div className="w-10 h-10 bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400 rounded-lg flex items-center justify-center mx-auto mb-3">
                    <svg className="w-5 h-5 flex-shrink-0" width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                    </svg>
                  </div>
                  <h3 className="font-semibold mb-1.5 text-gray-900 dark:text-gray-100">Column Profiling</h3>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    Detailed statistics and type inference for every column
                  </p>
                </div>

                <div className="card text-center p-6">
                  <div className="w-10 h-10 bg-orange-100 dark:bg-orange-900/30 text-vq-accent rounded-lg flex items-center justify-center mx-auto mb-3">
                    <svg className="w-5 h-5 flex-shrink-0" width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
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
            {/* File Summary - constrained width */}
            <div className="max-w-5xl mx-auto">
              <FileSummary fileInfo={profile.file} />
            </div>

            {/* Error Roll-up - constrained width */}
            <div className="max-w-5xl mx-auto">
              <ErrorRollup errors={profile.errors} warnings={profile.warnings} />
            </div>

            {/* Candidate Keys - constrained width */}
            {profile.candidate_keys.length > 0 && (
              <div className="max-w-5xl mx-auto">
                <CandidateKeys
                  runId={currentRunId}
                  candidateKeys={profile.candidate_keys}
                  onKeysConfirmed={handleKeysConfirmed}
                  onError={(msg) => error('Error', msg)}
                />
              </div>
            )}

            {/* Column Profiles - wider for table data */}
            <div className="max-w-6xl mx-auto">
              <h2 className="text-2xl font-bold mb-4 text-gray-900 dark:text-gray-100">
                Column Profiles
              </h2>
              <ColumnTable columns={profile.columns} totalRows={profile.file.rows} />
            </div>

            {/* Downloads - constrained width */}
            <div className="max-w-5xl mx-auto">
              <Downloads runId={currentRunId} />
            </div>
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
