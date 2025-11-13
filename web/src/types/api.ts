// API Types for VQ8 Data Profiler
// Based on OpenAPI spec from opening-spec.txt

export type RunState = 'queued' | 'processing' | 'completed' | 'failed';

export type ColumnType =
  | 'alpha'
  | 'varchar'
  | 'code'
  | 'numeric'
  | 'money'
  | 'date'
  | 'mixed'
  | 'unknown';

export interface ErrorItem {
  code: string;
  message: string;
  count: number;
}

export interface CreateRunRequest {
  delimiter: '|' | ',';
  quoted?: boolean;
  expect_crlf?: boolean;
}

export interface CreateRunResponse {
  run_id: string;
}

export interface RunStatus {
  state: RunState;
  progress_pct: number;
  warnings: ErrorItem[];
  errors: ErrorItem[];
}

export interface TopValue {
  value: string;
  count: number;
}

export interface LengthStats {
  min: number;
  max: number;
  avg: number;
}

export interface NumericStats {
  min: number;
  max: number;
  mean: number;
  median: number;
  stddev: number;
  quantiles: {
    p1?: number;
    p5?: number;
    p25?: number;
    p50?: number;
    p75?: number;
    p95?: number;
    p99?: number;
  };
  gaussian_pvalue?: number;
}

export interface MoneyRules {
  two_decimal_ok: boolean;
  disallowed_symbols_found: boolean;
  violations_count: number;
}

export interface DateStats {
  detected_format: string;
  min: string;
  max: string;
  out_of_range_count: number;
}

export interface ColumnProfile {
  name: string;
  type: ColumnType;
  null_pct: number;
  distinct_count: number;
  top_values: TopValue[];
  length?: LengthStats;
  numeric_stats?: NumericStats;
  money_rules?: MoneyRules;
  date_stats?: DateStats;
}

export interface FileInfo {
  rows: number;
  columns: number;
  delimiter: string;
  crlf_detected: boolean;
  header: string[];
}

export interface CandidateKey {
  columns: string[];
  score?: number;
  distinct_ratio?: number;
  null_ratio_sum?: number;
}

export interface Profile {
  run_id: string;
  file: FileInfo;
  errors: ErrorItem[];
  warnings: ErrorItem[];
  columns: ColumnProfile[];
  candidate_keys: CandidateKey[];
}

export interface CandidateKeysResponse {
  suggestions: CandidateKey[];
}

export interface ConfirmKeysRequest {
  keys: string[][];
}
