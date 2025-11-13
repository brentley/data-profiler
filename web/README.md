# VQ8 Data Profiler - Web UI

Modern React frontend for the VQ8 Data Profiler, built with Vite, TypeScript, and Tailwind CSS.

## Features

- **File Upload**: Support for .txt, .csv, and .gz files
- **Real-time Processing**: Live status updates with progress tracking
- **Comprehensive Profiling**: Detailed statistics for every column
- **Error Rollup**: Aggregated error reporting with severity levels
- **Candidate Keys**: Automatic uniqueness key detection
- **Dark Mode**: Default dark theme with light mode toggle
- **Responsive Design**: Mobile-first, works on all devices
- **Accessibility**: WCAG 2.1 AA compliant

## Tech Stack

- **React 19** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **Tailwind CSS 4** - Styling
- **VisiQuate UI Standards** - Design system

## Getting Started

### Prerequisites

- Node.js 20+ and npm
- Backend API running on port 8000 (or configure `VITE_API_URL`)

### Installation

```bash
npm install
```

### Development

```bash
npm run dev
```

Open http://localhost:5173 in your browser.

### Build

```bash
npm run build
```

Output will be in the `dist/` directory.

### Preview Production Build

```bash
npm run preview
```

## Configuration

Create a `.env` file based on `.env.example`:

```env
VITE_API_URL=http://localhost:8000
```

## Project Structure

```
src/
├── components/          # React components
│   ├── UploadForm.tsx       # File upload with options
│   ├── RunStatus.tsx        # Processing status with polling
│   ├── FileSummary.tsx      # File-level metrics
│   ├── ErrorRollup.tsx      # Aggregated error table
│   ├── CandidateKeys.tsx    # Key suggestions
│   ├── ColumnCard.tsx       # Per-column profiling
│   ├── Downloads.tsx        # Report downloads
│   └── Toast.tsx            # Notifications
├── hooks/               # Custom React hooks
│   └── useToast.ts          # Toast notification management
├── types/               # TypeScript types
│   └── api.ts               # API response types
├── utils/               # Utilities
│   ├── api.ts               # API client
│   └── theme.ts             # Dark mode management
├── App.tsx              # Main application
├── App.css              # Custom styles
└── index.css            # Global styles + Tailwind
```

## API Integration

The frontend communicates with the backend via REST API:

- `POST /runs` - Create profiling run
- `POST /runs/{id}/upload` - Upload file
- `GET /runs/{id}/status` - Poll status
- `GET /runs/{id}/profile` - Get full profile
- `GET /runs/{id}/candidate-keys` - Get key suggestions
- `POST /runs/{id}/confirm-keys` - Confirm keys for duplicate check
- `GET /runs/{id}/metrics.csv` - Download CSV metrics
- `GET /runs/{id}/report.html` - Download HTML report

See `src/types/api.ts` for complete type definitions.

## Design System

Following VisiQuate UI Standards:

- **Colors**: `--vq-primary: #116df8`, `--vq-accent: #ff5100`
- **Dark Mode**: Default theme with system preference support
- **Mobile-First**: Responsive breakpoints at 768px and 1024px
- **Touch-Friendly**: 44x44px minimum touch targets
- **Safari-First**: Compatible with Safari restrictions

## Components

### UploadForm
File upload with drag-and-drop, delimiter selection, and validation.

### RunStatus
Real-time progress tracking with polling. Shows aggregated errors/warnings.

### ErrorRollup
Table view of all errors and warnings with counts and severity badges.

### CandidateKeys
Interactive key selection for duplicate detection.

### ColumnCard
Expandable card showing column statistics, top values, and type-specific metrics.

### FileSummary
Overview of file structure (rows, columns, delimiter, line endings).

### Downloads
Links to download JSON, CSV, and HTML reports.

### Toast
Non-spammy notification system with auto-dismiss.

## Performance

- Lazy loading for heavy components
- Efficient polling with cleanup
- Optimized re-renders with React hooks
- CSS transitions for smooth UX

## Accessibility

- Semantic HTML
- ARIA labels and roles
- Keyboard navigation
- Focus indicators
- Color contrast compliance

## Browser Support

- Chrome/Edge (latest)
- Safari (latest)
- Firefox (latest)
- Mobile Safari
- Chrome Mobile

Safari is the primary test target per VisiQuate standards.

## License

Copyright VisiQuate. All rights reserved.
