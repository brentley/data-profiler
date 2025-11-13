# VQ8 Data Profiler - Quick Start Guide

## Prerequisites

- Node.js 20+ and npm installed
- Backend API running (or mock data for development)

## Installation & Setup

```bash
# Navigate to the web directory
cd /Users/brent/git/data-profiler/web

# Install dependencies (already done)
npm install

# Create environment file
cp .env.example .env

# Edit .env if needed (defaults to http://localhost:8000)
# VITE_API_URL=http://localhost:8000
```

## Development

```bash
# Start development server
npm run dev

# The app will be available at:
# http://localhost:5173
```

Open your browser to http://localhost:5173 and you should see the VQ8 Data Profiler UI.

## Production Build

```bash
# Build for production
npm run build

# Preview production build
npm run preview
```

## Testing the UI (Without Backend)

If the backend is not yet available, you can still test the UI:

1. The upload form will work
2. It will fail gracefully with an error toast
3. You can inspect all components and styling
4. Dark mode toggle works
5. Responsive design can be tested

## Expected Workflow

1. **Upload Page**
   - Select or drag-drop a .txt, .csv, or .gz file
   - Choose delimiter (| or ,)
   - Set options for quoted fields and CRLF
   - Click "Start Profiling"

2. **Processing Page**
   - Shows real-time progress bar
   - Displays error/warning counts
   - Updates every 2 seconds
   - Shows status badge (Queued → Processing → Completed)

3. **Results Page**
   - File summary with row/column counts
   - Error roll-up table with severity levels
   - Candidate key suggestions
   - Per-column profiling cards (expandable)
   - Download links (JSON, CSV, HTML)

## Troubleshooting

### Port Already in Use
If port 5173 is taken:
```bash
# Vite will automatically try the next available port
npm run dev
```

### API Connection Issues
Check `.env` file:
```env
VITE_API_URL=http://localhost:8000
```

Ensure backend is running on the correct port.

### Build Errors
Clear node_modules and reinstall:
```bash
rm -rf node_modules package-lock.json
npm install
npm run build
```

### Dark Mode Not Working
The app defaults to dark mode. Check browser console for errors.
Theme preference is stored in localStorage under key `vq8-theme`.

## Features to Test

- [ ] File upload (drag-drop and click)
- [ ] File validation (.txt, .csv, .gz only)
- [ ] Delimiter selection
- [ ] Dark/light mode toggle
- [ ] Responsive design (resize browser)
- [ ] Toast notifications
- [ ] Progress tracking
- [ ] Error rollup table
- [ ] Candidate key selection
- [ ] Column card expansion
- [ ] Download links

## Next Steps

Once the backend API is ready:

1. Update `VITE_API_URL` in `.env`
2. Test full upload workflow
3. Verify real-time status polling
4. Test profile display
5. Confirm key selection and duplicate check
6. Test all download formats

## Support

For issues or questions, refer to:
- Main README: `/Users/brent/git/data-profiler/web/README.md`
- Full documentation: `/Users/brent/git/data-profiler/WEB_UI_SUMMARY.md`
- BuildSpec: `/Users/brent/git/data-profiler/opening-spec.txt`
