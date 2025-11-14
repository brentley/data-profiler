// File upload form component
// Supports .txt, .csv, .gz files with delimiter selection
import { useState, useRef, type DragEvent } from 'react';
import { api } from '../utils/api';
import type { CreateRunRequest } from '../types/api';

interface UploadFormProps {
  onUploadStart: (runId: string) => void;
  onError: (message: string) => void;
}

export function UploadForm({ onUploadStart, onError }: UploadFormProps) {
  const [file, setFile] = useState<File | null>(null);
  const [delimiter, setDelimiter] = useState<'|' | ','>('|');
  const [quoted, setQuoted] = useState(true);
  const [expectCrlf, setExpectCrlf] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!file) {
      onError('Please select a file');
      return;
    }

    setUploading(true);

    try {
      // Step 1: Create run
      const request: CreateRunRequest = {
        delimiter,
        quoted,
        expect_crlf: expectCrlf,
      };
      const { run_id } = await api.createRun(request);

      // Step 2: Upload file
      await api.uploadFile(run_id, file);

      // Notify parent component
      onUploadStart(run_id);
    } catch (err) {
      onError(
        err instanceof Error ? err.message : 'Upload failed. Please try again.'
      );
      setUploading(false);
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
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
                width="24"
                height="24"
                className="h-6 w-6 text-green-500 flex-shrink-0"
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
                width="24"
                height="24"
                className="h-6 w-6 text-gray-400 flex-shrink-0"
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
                  <span className="font-semibold">Click to upload</span> or drag and drop (.txt, .csv, or .gz)
                </p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Delimiter Selection */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Delimiter
        </label>
        <div className="flex gap-4">
          <label className="flex items-center gap-2 cursor-pointer hover:text-vq-primary transition-colors">
            <input
              type="radio"
              value="|"
              checked={delimiter === '|'}
              onChange={(e) => setDelimiter(e.target.value as '|')}
              className="w-4 h-4 text-vq-primary focus:ring-vq-primary focus:ring-2"
            />
            <span className="text-sm">Pipe (|)</span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer hover:text-vq-primary transition-colors">
            <input
              type="radio"
              value=","
              checked={delimiter === ','}
              onChange={(e) => setDelimiter(e.target.value as ',')}
              className="w-4 h-4 text-vq-primary focus:ring-vq-primary focus:ring-2"
            />
            <span className="text-sm">Comma (,)</span>
          </label>
        </div>
      </div>

      {/* Options */}
      <div className="space-y-2.5">
        <label className="flex items-center gap-2 cursor-pointer hover:text-vq-primary transition-colors">
          <input
            type="checkbox"
            checked={quoted}
            onChange={(e) => setQuoted(e.target.checked)}
            className="w-4 h-4 text-vq-primary focus:ring-vq-primary focus:ring-2 rounded"
          />
          <span className="text-sm">
            Fields may be quoted (double quotes)
          </span>
        </label>
        <label className="flex items-center gap-2 cursor-pointer hover:text-vq-primary transition-colors">
          <input
            type="checkbox"
            checked={expectCrlf}
            onChange={(e) => setExpectCrlf(e.target.checked)}
            className="w-4 h-4 text-vq-primary focus:ring-vq-primary focus:ring-2 rounded"
          />
          <span className="text-sm">
            Expect CRLF line endings (Windows)
          </span>
        </label>
      </div>

      {/* Submit Button */}
      <div className="pt-2">
        <button
          type="submit"
          disabled={!file || uploading}
          className="btn-primary flex items-center justify-center gap-2 min-w-[160px]"
        >
          {uploading ? (
            <>
              <span className="spinner"></span>
              <span>Uploading...</span>
            </>
          ) : (
            <>
              <svg
                className="w-4 h-4"
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
          )}
        </button>
      </div>
    </form>
  );
}
