// File upload form component with chunked upload support
// Supports .txt, .csv, .gz files with auto-detected delimiter, quoting, and line endings
import { useState, useRef, type DragEvent } from 'react';
import { api, ApiError } from '../utils/api';
import type { CreateRunRequest, ChunkedUploadStatus } from '../types/api';

interface UploadFormProps {
  onUploadStart: (runId: string) => void;
  onError: (message: string) => void;
}

const CHUNK_SIZE = 5 * 1024 * 1024; // 5MB
const MAX_FILE_SIZE = 10 * 1024 * 1024 * 1024; // 10GB
const MAX_RETRIES = 3;

interface UploadProgress {
  bytesUploaded: number;
  totalBytes: number;
  currentChunk: number;
  totalChunks: number;
  uploadSpeed: number; // MB/s
  eta: number; // seconds
}

interface UploadSession {
  runId: string;
  file: File;
  uploadSpeed: number;
  lastUpdateTime: number;
  lastUpdateBytes: number;
  uploadedChunks: Set<number>;
}

export function UploadForm({ onUploadStart, onError }: UploadFormProps) {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [progress, setProgress] = useState<UploadProgress | null>(null);
  const [uploadFailed, setUploadFailed] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const uploadSessionRef = useRef<UploadSession | null>(null);

  const validateFile = (file: File): string | null => {
    const validExtensions = ['.txt', '.csv', '.gz'];
    const fileName = file.name.toLowerCase();
    const isValid = validExtensions.some((ext) => fileName.endsWith(ext));

    if (!isValid) {
      return 'Please upload a .txt, .csv, or .gz file';
    }

    // Check for .gz containing .txt or .csv
    if (fileName.endsWith('.gz')) {
      const withoutGz = fileName.slice(0, -3);
      if (!withoutGz.endsWith('.txt') && !withoutGz.endsWith('.csv')) {
        return 'Gzipped files must be .txt.gz or .csv.gz';
      }
    }

    // Check file size (10GB max)
    if (file.size > MAX_FILE_SIZE) {
      return 'File size exceeds 10GB limit';
    }

    if (file.size === 0) {
      return 'File is empty';
    }

    return null;
  };

  const handleFileChange = (selectedFile: File | null) => {
    if (!selectedFile) {
      setFile(null);
      return;
    }

    const error = validateFile(selectedFile);
    if (error) {
      onError(error);
      setFile(null);
      return;
    }

    setFile(selectedFile);
  };

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragOver(false);
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragOver(false);

    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      handleFileChange(droppedFile);
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
  };

  const calculateProgress = (
    bytesUploaded: number,
    totalBytes: number,
    uploadSpeed: number,
  ): UploadProgress => {
    const totalChunks = Math.ceil(totalBytes / CHUNK_SIZE);
    const currentChunk = Math.floor(bytesUploaded / CHUNK_SIZE);
    const progressPct = (bytesUploaded / totalBytes) * 100;

    // Calculate ETA based on upload speed
    let eta = 0;
    if (uploadSpeed > 0) {
      const remainingBytes = totalBytes - bytesUploaded;
      eta = Math.ceil(remainingBytes / (uploadSpeed * 1024 * 1024)); // Convert speed to bytes/s
    }

    return {
      bytesUploaded,
      totalBytes,
      currentChunk: Math.min(currentChunk, totalChunks),
      totalChunks,
      uploadSpeed,
      eta,
    };
  };

  const updateUploadSpeed = (session: UploadSession, bytesUploaded: number): number => {
    const now = Date.now();
    const timeDiff = (now - session.lastUpdateTime) / 1000; // seconds
    const bytesDiff = bytesUploaded - session.lastUpdateBytes;

    if (timeDiff < 1) {
      // Update less frequently for stable speed calculation
      return session.uploadSpeed;
    }

    const newSpeed = bytesDiff / timeDiff / (1024 * 1024); // MB/s
    // Apply exponential moving average to smooth out speed fluctuations
    const smoothedSpeed = session.uploadSpeed * 0.7 + newSpeed * 0.3;

    session.uploadSpeed = smoothedSpeed;
    session.lastUpdateTime = now;
    session.lastUpdateBytes = bytesUploaded;

    return smoothedSpeed;
  };

  const uploadChunkWithRetry = async (
    session: UploadSession,
    chunkIndex: number,
    chunk: Blob,
    retryCount: number = 0,
  ): Promise<void> => {
    if (abortControllerRef.current?.signal.aborted) {
      throw new Error('Upload cancelled');
    }

    try {
      await api.uploadChunk(session.runId, chunkIndex, chunk);
      session.uploadedChunks.add(chunkIndex);
    } catch (error) {
      if (retryCount < MAX_RETRIES) {
        const backoffDelay = Math.pow(2, retryCount) * 1000; // 1s, 2s, 4s
        await new Promise((resolve) => setTimeout(resolve, backoffDelay));
        return uploadChunkWithRetry(session, chunkIndex, chunk, retryCount + 1);
      }
      throw error;
    }
  };

  const resumeUpload = async () => {
    if (!uploadSessionRef.current) {
      onError('No upload session found');
      return;
    }

    setErrorMessage('');
    setUploadFailed(false);

    try {
      const status = await api.getUploadStatus(uploadSessionRef.current.runId);
      const session = uploadSessionRef.current;

      // Mark already uploaded chunks
      for (let i = 0; i < status.chunks_received; i++) {
        session.uploadedChunks.add(i);
      }

      // Continue uploading from where we left off
      await performChunkedUpload(session, status.chunks_received);
    } catch (error) {
      const message =
        error instanceof Error ? error.message : 'Failed to resume upload. Please try again.';
      setErrorMessage(message);
      onError(message);
    }
  };

  const performChunkedUpload = async (
    session: UploadSession,
    startFromChunk: number = 0,
  ): Promise<void> => {
    const { file, runId } = session;
    const totalChunks = Math.ceil(file.size / CHUNK_SIZE);

    for (let chunkIndex = startFromChunk; chunkIndex < totalChunks; chunkIndex++) {
      if (abortControllerRef.current?.signal.aborted) {
        throw new Error('Upload cancelled');
      }

      // Skip already uploaded chunks
      if (session.uploadedChunks.has(chunkIndex)) {
        const bytesUploaded = (chunkIndex + 1) * CHUNK_SIZE;
        const speed = updateUploadSpeed(session, bytesUploaded);
        setProgress(
          calculateProgress(Math.min(bytesUploaded, file.size), file.size, speed),
        );
        continue;
      }

      const start = chunkIndex * CHUNK_SIZE;
      const end = Math.min(start + CHUNK_SIZE, file.size);
      const chunk = file.slice(start, end);

      try {
        await uploadChunkWithRetry(session, chunkIndex, chunk);

        // Update progress
        const speed = updateUploadSpeed(session, end);
        setProgress(calculateProgress(end, file.size, speed));
      } catch (error) {
        setUploadFailed(true);
        const message =
          error instanceof Error ? error.message : `Failed to upload chunk ${chunkIndex + 1}`;
        setErrorMessage(message);
        throw error;
      }
    }

    // All chunks uploaded successfully, complete the upload
    const completeResponse = await api.completeChunkedUpload(runId);

    // Notify parent component
    onUploadStart(runId);
    setUploading(false);
    setProgress(null);
    setFile(null);
    setUploadFailed(false);
    uploadSessionRef.current = null;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!file) {
      onError('Please select a file');
      return;
    }

    setUploading(true);
    setUploadFailed(false);
    setErrorMessage('');
    abortControllerRef.current = new AbortController();

    try {
      // Step 1: Create run with auto-detection for all settings
      const request: CreateRunRequest = {
        delimiter: null, // Always auto-detect
        quoted: true, // Default assumption
        expect_crlf: true, // Default assumption
      };
      const { run_id } = await api.createRun(request);

      // Step 2: Initialize chunked upload
      const totalChunks = Math.ceil(file.size / CHUNK_SIZE);
      await api.initChunkedUpload(run_id, {
        filename: file.name,
        total_size: file.size,
        chunk_size: CHUNK_SIZE,
      });

      // Step 3: Create upload session
      const session: UploadSession = {
        runId: run_id,
        file,
        uploadSpeed: 0,
        lastUpdateTime: Date.now(),
        lastUpdateBytes: 0,
        uploadedChunks: new Set(),
      };
      uploadSessionRef.current = session;

      // Initialize progress
      setProgress(
        calculateProgress(0, file.size, 0),
      );

      // Step 4: Upload all chunks
      await performChunkedUpload(session);
    } catch (err) {
      if (err instanceof Error && err.message === 'Upload cancelled') {
        // User cancelled, don't show error
        setUploading(false);
        setProgress(null);
        return;
      }

      const message =
        err instanceof Error ? err.message : 'Upload failed. Please try again.';
      setErrorMessage(message);
      onError(message);
      setUploading(false);
    }
  };

  const handleCancel = () => {
    abortControllerRef.current?.abort();
    setUploading(false);
    setProgress(null);
    setUploadFailed(false);
    setErrorMessage('');
    uploadSessionRef.current = null;
  };

  // Display progress state
  if (uploading && progress) {
    const progressPct = (progress.bytesUploaded / progress.totalBytes) * 100;
    const progressClamped = Math.min(progressPct, 100);

    return (
      <form className="space-y-5">
        <div className="text-sm text-gray-600 dark:text-gray-400">
          {uploadFailed ? 'Upload interrupted. Resume or start over.' : 'Uploading your file...'}
        </div>

        {/* Progress Bar Container */}
        <div className="space-y-3">
          {/* Visual Progress Bar */}
          <div className="w-full bg-gray-200 dark:bg-slate-700 rounded-full h-2 overflow-hidden">
            <div
              className="progress-bar h-full transition-all duration-300"
              style={{ width: `${progressClamped}%` }}
            />
          </div>

          {/* Progress Details */}
          <div className="space-y-1 text-xs text-gray-600 dark:text-gray-400">
            <div className="flex justify-between items-center">
              <span>
                {progressPct.toFixed(1)}%
              </span>
              <span>
                {formatFileSize(progress.bytesUploaded)} / {formatFileSize(progress.totalBytes)}
              </span>
            </div>

            <div className="flex justify-between items-center">
              <span>
                {progress.uploadSpeed.toFixed(1)} MB/s
              </span>
              <span>
                {progress.eta > 0 ? `~${progress.eta}s remaining` : 'calculating...'}
              </span>
            </div>

            <div className="text-center">
              <span>
                Chunk {progress.currentChunk} of {progress.totalChunks}
              </span>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-3 pt-2">
          {uploadFailed ? (
            <>
              <button
                type="button"
                onClick={resumeUpload}
                className="btn-accent flex-1"
              >
                Resume Upload
              </button>
              <button
                type="button"
                onClick={() => {
                  handleCancel();
                  setFile(null);
                }}
                className="btn-secondary flex-1"
              >
                Start Over
              </button>
            </>
          ) : (
            <button
              type="button"
              onClick={handleCancel}
              className="btn-secondary flex-1"
            >
              Cancel
            </button>
          )}
        </div>
      </form>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {/* Instructions */}
      <div className="text-sm text-gray-600 dark:text-gray-400">
        Upload your CSV file for automatic profiling. The delimiter, quoting, and line endings
        will be detected automatically.
      </div>

      {/* File Upload Dropzone */}
      <div style={{ width: '100%' }}>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Select File
        </label>
        <div
          className={`dropzone ${dragOver ? 'drag-over' : ''}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".txt,.csv,.gz"
            onChange={(e) => handleFileChange(e.target.files?.[0] || null)}
            className="hidden"
            aria-label="File upload"
          />
          {file ? (
            <div className="flex items-center gap-2">
              <svg
                className="w-6 h-6 text-green-500 flex-shrink-0"
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
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
              <div className="flex-1 min-w-0 text-left">
                <p className="text-xs font-medium text-gray-900 dark:text-gray-100 truncate">
                  {file.name} ({formatFileSize(file.size)})
                </p>
              </div>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  setFile(null);
                }}
                className="text-xs text-red-600 hover:text-red-700 dark:text-red-400 px-2 flex-shrink-0"
              >
                Remove
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <svg
                className="w-6 h-6 text-gray-400 flex-shrink-0"
                width="24"
                height="24"
                stroke="currentColor"
                fill="none"
                viewBox="0 0 48 48"
              >
                <path
                  d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
                  strokeWidth={2}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
              <div className="flex-1 text-left">
                <p className="text-xs text-gray-600 dark:text-gray-400">
                  <span className="font-semibold">Click to upload</span> or drag and drop (.txt,
                  .csv, or .gz)
                </p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Submit Button */}
      <div className="pt-2">
        <button
          type="submit"
          disabled={!file}
          className="btn-accent flex items-center justify-center gap-2 min-w-[160px]"
        >
          <>
            <svg
              className="w-4 h-4 flex-shrink-0"
              width="16"
              height="16"
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
            <span>Start Profiling</span>
          </>
        </button>
      </div>
    </form>
  );
}
