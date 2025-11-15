# GitHub Issues: Data Profiler UI/UX Improvements

This document contains structured issue descriptions for the data-profiler UI/UX improvements. Each issue can be created directly on GitHub using these specifications.

---

## Issue 1: Fix RunMetadata Schema to Support Auto-Detection Information

**Title:** Add auto-detection metadata to RunMetadata schema for delimiter/quoting/line-ending detection

**Type:** Enhancement

**Priority:** High

**Description:**

The current `FileMetadata` schema in `api/models/run.py` includes basic fields for file information but lacks structured metadata about auto-detection confidence levels for CSV parsing parameters (delimiter, quoting, line endings).

### Problem

When users don't manually specify delimiter, quoting, or line-ending preferences, the API auto-detects these values but doesn't expose detection confidence metrics to the frontend. This makes it difficult for users to understand:
- Whether auto-detection succeeded with high confidence
- Whether they should manually verify settings
- What parameters were actually used for parsing

### Solution

Extend the `FileMetadata` model to include optional fields for auto-detection results:

1. **Add fields to `FileMetadata` model** (`api/models/run.py`):
   - `delimiter_detected: Optional[bool]` - Whether delimiter was auto-detected
   - `delimiter_confidence: Optional[float]` - Confidence score (0.0-1.0)
   - `quoting_detected: Optional[bool]` - Whether quoting was auto-detected
   - `quoting_confidence: Optional[float]` - Confidence score (0.0-1.0)
   - `line_ending_detected: Optional[bool]` - Whether line ending was auto-detected
   - `line_ending_confidence: Optional[float]` - Confidence score (0.0-1.0)

2. **Update backend logic** (`api/services/ingest.py`):
   - Capture detection method for each parameter
   - Calculate confidence scores during parsing
   - Return detection metadata in profile responses

3. **Update frontend display** (`web/src/components/FileSummary.tsx`):
   - Show detection confidence badges
   - Indicate high/medium/low confidence levels
   - Suggest manual verification if confidence < 0.8

### Files Modified

- `api/models/run.py` - FileMetadata schema
- `api/services/ingest.py` - Detection logic
- `web/src/components/FileSummary.tsx` - Display detection info
- `web/src/types/api.ts` - Type definitions

### Testing Notes

- Verify detection metadata flows through API responses
- Test with files using ambiguous delimiters (tab vs comma)
- Validate confidence scores are between 0.0 and 1.0
- Test backward compatibility (confidence fields are optional)
- Ensure frontend gracefully handles missing confidence data

### Acceptance Criteria

- [ ] FileMetadata includes detection metadata fields
- [ ] Backend populates detection confidence values
- [ ] Frontend displays detection information in FileSummary
- [ ] Backward compatibility maintained (fields optional)
- [ ] Tests pass for detection metadata scenarios
- [ ] API documentation updated

---

## Issue 2: Fix Tailwind CSS Compilation for max-width Utilities

**Title:** Configure Tailwind CSS to properly compile max-width utilities

**Type:** Bug

**Priority:** High

**Description:**

The current Tailwind CSS configuration is missing custom max-width utilities needed for the layout constraint system. The application uses `max-w-5xl` and `max-w-6xl` classes throughout the components, but these may not be properly compiled or may be using default Tailwind values instead of optimized values for the data profiler layout.

### Problem

1. Content sections use `max-w-5xl` (48rem) and `max-w-6xl` (64rem) for constraint
2. These classes may not be compiling to correct values
3. No custom max-width scale defined in `tailwind.config.js`
4. Results in inconsistent or overflowing content on different screen sizes

### Solution

1. **Update `web/tailwind.config.js`** to define custom max-width scale:
   ```javascript
   theme: {
     extend: {
       maxWidth: {
         '5xl': '64rem',      // 1024px - for main content
         '6xl': '80rem',      // 1280px - for wide content
         '7xl': '96rem',      // 1536px - for extra wide content
       }
     }
   }
   ```

2. **Verify utility compilation** in `web/src/index.css`
3. **Test responsive behavior** across all breakpoints
4. **Validate page width constraints** in all views

### Files Modified

- `web/tailwind.config.js` - Extend theme configuration
- `web/src/index.css` - Ensure proper CSS import
- `web/build/tailwind.css` - Generated CSS (auto-generated)

### Testing Notes

- Inspect compiled CSS to verify max-width values
- Test on desktop, tablet, and mobile viewports
- Verify no content overflow at any breakpoint
- Test print preview for layout consistency
- Check browser DevTools computed styles

### Acceptance Criteria

- [ ] Tailwind config includes custom max-width utilities
- [ ] max-w-5xl and max-w-6xl compile to correct values
- [ ] No content overflow on desktop (1920px+)
- [ ] No content overflow on tablet (768px-1024px)
- [ ] Responsive behavior works as designed
- [ ] Build completes without warnings

---

## Issue 3: Fix Oversized Icon Rendering Across Components

**Title:** Reduce icon sizes across components for professional appearance

**Type:** Bug

**Priority:** Critical

**Description:**

Multiple components throughout the application use oversized SVG icons that make the UI appear bulky and unprofessional. This is particularly noticeable in:
- File upload area (current: w-12 h-12 = 48px)
- Feature cards (current: w-10 h-10 = 40px)
- Button icons (current: w-6 h-6 = 24px)
- Header logo area (current: w-10 h-10 = 40px)

### Problem

1. Upload form dropzone icon is 48x48px (too large for data tool)
2. Feature card icons are 40x40px (should be 32px)
3. Inconsistent icon sizing across components
4. Makes the interface feel like a mobile app rather than professional tool

### Solution

Standardize icon sizes:
1. **Feature card icons**: Reduce from 40px to 32px (w-8 h-8)
2. **Upload area icon**: Reduce from 48px to 40px (w-10 h-10)
3. **Button icons**: Keep at 20px (w-5 h-5)
4. **Header logo**: Keep at 40px (w-10 h-10)
5. **Create CSS size variables** for consistency

Update files:

**web/src/components/UploadForm.tsx**
```jsx
// Before: className="mx-auto h-12 w-12"
// After: className="mx-auto h-10 w-10"
<svg className="mx-auto h-10 w-10 text-gray-400" />
```

**web/src/App.tsx**
```jsx
// Before: className="w-10 h-10 ... mx-auto mb-3"
// After: className="w-8 h-8 ... mx-auto mb-3"
<div className="w-8 h-8 bg-blue-100 dark:bg-blue-900/30 ...">
```

**web/src/index.css** (add icon size variables):
```css
:root {
  --icon-xs: 1rem;     /* 16px */
  --icon-sm: 1.25rem;  /* 20px */
  --icon-md: 1.5rem;   /* 24px */
  --icon-lg: 2rem;     /* 32px */
  --icon-xl: 2.5rem;   /* 40px */
}
```

### Files Modified

- `web/src/components/UploadForm.tsx` - Dropzone icon size
- `web/src/App.tsx` - Feature card icons and header logo
- `web/src/components/FileSummary.tsx` - Summary icons
- `web/src/components/ErrorRollup.tsx` - Error icons
- `web/src/components/ColumnTable.tsx` - Type indicator icons
- `web/src/index.css` - Icon size variables

### Testing Notes

- Visual inspection at 1920x1080 resolution
- Compare before/after screenshots
- Verify proportions look correct with text
- Check dark mode appearance
- Test on mobile/tablet breakpoints
- Ensure accessibility (sufficient touch targets if used as buttons)

### Acceptance Criteria

- [ ] Feature card icons are 32px (w-8 h-8)
- [ ] Upload area icon is 40px (w-10 h-10)
- [ ] All other icons sized appropriately
- [ ] CSS variables defined for reusability
- [ ] No visual clipping or distortion
- [ ] Professional appearance verified

---

## Issue 4: Apply VisiQuate Branding (Colors and Styling)

**Title:** Apply VisiQuate brand colors and styling standards throughout UI

**Type:** Enhancement

**Priority:** Medium

**Description:**

While the application has basic color support, VisiQuate branding is not consistently applied. The design needs to implement the complete VisiQuate design system including:
- Brand color palette (primary blue, accent orange)
- Data type colors (numeric, text, date, code, money)
- Semantic colors (success, warning, error, info)
- Typography hierarchy
- Component styling standards

### Problem

1. Limited use of VisiQuate primary color (#116df8)
2. No defined data type color system
3. Inconsistent semantic color usage for status/errors
4. Typography lacks hierarchy
5. Components don't follow VisiQuate design guidelines

### Solution

1. **Expand color palette** in `web/tailwind.config.js`:
   ```javascript
   theme: {
     extend: {
       colors: {
         'vq-primary': '#116df8',
         'vq-accent': '#ff5100',
         'vq-type-numeric': '#3b82f6',
         'vq-type-text': '#06b6d4',
         'vq-type-date': '#8b5cf6',
         'vq-type-code': '#10b981',
         'vq-type-money': '#06b6d4',
         'vq-type-mixed': '#f97316',
         'vq-type-unknown': '#6b7280',
       }
     }
   }
   ```

2. **Update component styling**:
   - Use brand colors consistently
   - Apply data type colors to type badges
   - Implement semantic colors for status indicators
   - Update card styling with VisiQuate design

3. **Update typography** with proper hierarchy:
   - Headers: bold, larger sizes
   - Body text: readable, consistent
   - Labels: smaller, uppercase
   - Data values: monospace for numbers

### Files Modified

- `web/tailwind.config.js` - Color palette
- `web/src/index.css` - Typography hierarchy
- `web/src/App.css` - Component styling
- `web/src/components/FileSummary.tsx` - Status badges
- `web/src/components/ColumnTable.tsx` - Type colors
- `web/src/components/ErrorRollup.tsx` - Error colors

### Testing Notes

- Verify all brand colors render correctly
- Test dark mode color contrast (WCAG AA minimum)
- Check data type colors are distinguishable
- Validate status color meanings (green=success, red=error)
- Compare against VisiQuate design guide
- Screenshot comparison before/after

### Acceptance Criteria

- [ ] Brand colors applied throughout UI
- [ ] Data type colors consistently used
- [ ] Semantic colors for status/errors
- [ ] Typography hierarchy implemented
- [ ] Dark mode colors verified for contrast
- [ ] WCAG AA accessibility maintained

---

## Issue 5: Redesign Page Layout with Proper Width Constraints

**Title:** Implement constrained-width layout for improved content readability

**Type:** Enhancement

**Priority:** High

**Description:**

The current layout extends full-width on large displays, making long text lines and tables difficult to read. Professional data tools typically constrain content width to improve readability and focus user attention. The layout needs max-width constraints at various breakpoints.

### Problem

1. Content extends to 100% of viewport width on large screens
2. Column tables and text become hard to read at 4K+ resolutions
3. No visual hierarchy between different content sections
4. Inconsistent spacing on desktop displays

### Solution

Implement a layered max-width constraint system:

1. **Outer container** (main content):
   - `max-w-7xl` (80rem/1280px) for header/footer
   - `max-w-6xl` (64rem/1024px) for table content
   - `max-w-5xl` (56rem/896px) for form content

2. **Update `web/src/App.tsx`**:
   - Wrap main content sections in max-width containers
   - Apply consistent spacing (mx-auto for centering)
   - Maintain responsive behavior on mobile/tablet

3. **Responsive breakpoints**:
   - Mobile (< 640px): No max-width constraint, use full width
   - Tablet (640px-1024px): max-w-md or max-w-2xl
   - Desktop (1024px+): Apply full constraint (max-w-5xl/6xl)
   - Large desktop (1920px+): Still constrained, centered

### Layout Structure

```
┌─ Full width ────────────────────────────────────────────┐
│ ┌─ Header max-w-7xl, centered ────────────────────────┐ │
│ │                                                      │ │
│ └──────────────────────────────────────────────────────┘ │
│ ┌─ Main max-w-6xl, centered ──────────────────────────┐ │
│ │ ┌─ Upload section max-w-5xl ────────────────────┐  │ │
│ │ │                                                │  │ │
│ │ └────────────────────────────────────────────────┘  │ │
│ │ ┌─ Results section max-w-6xl ───────────────────┐  │ │
│ │ │ (Table can use wider constraint)               │  │ │
│ │ └────────────────────────────────────────────────┘  │ │
│ └──────────────────────────────────────────────────────┘ │
│ ┌─ Footer max-w-7xl, centered ────────────────────────┐ │
│ │                                                      │ │
│ └──────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

### Files Modified

- `web/src/App.tsx` - Wrap sections with max-width containers
- `web/tailwind.config.js` - Configure custom max-width values
- `web/src/index.css` - CSS variables for max-widths

### Testing Notes

- Test at 1920x1080 (Full HD)
- Test at 2560x1440 (2K)
- Test at 3840x2160 (4K)
- Verify mobile layout (375px, 768px, 1024px)
- Check that content remains centered
- Validate table readability at all sizes

### Acceptance Criteria

- [ ] Main content constrained to max-w-6xl
- [ ] Forms/uploads constrained to max-w-5xl
- [ ] Content centered on large displays
- [ ] Mobile layout unaffected (full width)
- [ ] Responsive breakpoints working correctly
- [ ] Table remains readable at all sizes

---

## Issue 6: Force Dark Mode Permanently

**Title:** Remove light mode option and enforce dark mode UI

**Type:** Enhancement

**Priority:** Medium

**Description:**

The application supports both light and dark modes, but design specifications call for dark mode to be the default and permanent for the professional data profiler aesthetic. This issue consolidates dark mode as the only UI theme.

### Problem

1. Light mode CSS is unnecessary and adds bloat
2. User preference switching adds complexity
3. Design system optimized for dark mode
4. Inconsistent appearance if users switch modes

### Solution

1. **Remove theme toggle** from UI (if present)
2. **Simplify CSS** by removing light mode styles
3. **Force dark mode on app initialization** (already done in App.tsx useEffect)
4. **Remove localStorage theme preference** logic
5. **Simplify color variables** to dark mode only

### Code Changes

**web/src/App.tsx** (already has this):
```jsx
// Force dark mode on mount
useEffect(() => {
  document.documentElement.classList.add('dark');
}, []);
```

**web/src/index.css** - Remove light mode variants:
- Remove `light` color definitions
- Keep only `dark` mode colors
- Remove theme toggle styles

**web/src/App.css** - Simplify:
- Remove `.light` selectors
- Keep only `.dark` selectors
- Reduce CSS file size

### Files Modified

- `web/src/App.tsx` - Verify dark mode is forced
- `web/src/index.css` - Remove light mode styles
- `web/src/App.css` - Remove light mode selectors
- `web/src/components/*.tsx` - Remove light mode variants

### Testing Notes

- Inspect computed styles in DevTools (all dark)
- Verify no light mode colors appear
- Test theme toggle is removed/disabled
- Check localStorage doesn't set theme preference
- Take before/after screenshots
- Test on different browsers

### Acceptance Criteria

- [ ] Dark mode forced on app initialization
- [ ] Light mode styles removed from CSS
- [ ] No theme toggle in UI
- [ ] Computed styles confirm dark mode
- [ ] CSS file size reduced
- [ ] All components render in dark mode

---

## Issue 7: Enhance HTML Report with Complete CSV Data

**Title:** Include full CSV data in downloadable HTML report

**Type:** Enhancement

**Priority:** Medium

**Description:**

Currently, the HTML report includes summarized column profile data but doesn't include the complete raw CSV data. Users should be able to download a single HTML file that contains:
- Profile summary
- Column statistics
- Error/warning details
- Complete raw CSV data (embedded or as downloadable table)

### Problem

1. HTML report lacks complete data context
2. Users must download separate CSV file to see raw data
3. Single-file distribution difficult
4. No way to review source data alongside analysis

### Solution

1. **Create enhanced HTML report template** (`api/services/report.py`):
   - Include profile summary (current)
   - Include column statistics (current)
   - Add "Raw Data" section with CSV table
   - Add collapsible sections for large tables
   - Add download button for data

2. **Implement data embedding**:
   - For files < 5MB: Embed complete data as HTML table
   - For files >= 5MB: Embed first 1000 rows + download link
   - Add summary: "Showing 1,000 of 1,000,000 rows"

3. **Add interactive features**:
   - Searchable data table
   - Column sorting
   - Export to CSV functionality
   - Print-friendly layout

### Files Modified

- `api/services/report.py` - HTML generation
- `web/src/components/Downloads.tsx` - Report info
- API documentation - Updated report format

### Implementation Details

```python
# In api/services/report.py
def generate_html_report(profile, csv_data, max_rows=1000):
    """
    Generate enhanced HTML report with embedded data.

    Args:
        profile: Profile response data
        csv_data: List of row dictionaries
        max_rows: Maximum rows to embed (1000)

    Returns:
        HTML string with complete report
    """
    # 1. Profile summary section
    # 2. Column statistics
    # 3. Error/warning details
    # 4. Raw data table (first N rows)
    # 5. JavaScript for interactivity
```

### Testing Notes

- Generate reports for various file sizes (1MB, 100MB, 1GB)
- Verify HTML file size is reasonable
- Test table sorting and searching
- Verify data accuracy matches source
- Test print preview
- Validate HTML structure and CSS

### Acceptance Criteria

- [ ] HTML report includes raw data table
- [ ] Reports under 5MB embed complete data
- [ ] Reports over 5MB embed 1000 rows + link
- [ ] Data table is sortable and searchable
- [ ] Export to CSV functionality works
- [ ] Print layout is clean and readable
- [ ] No data corruption or truncation

---

## Issue 8: Add Comprehensive Auto-Detection Tests

**Title:** Create comprehensive test suite for CSV auto-detection functionality

**Type:** Test/Enhancement

**Priority:** High

**Description:**

The auto-detection system for delimiter, quoting, and line-ending detection needs comprehensive test coverage to ensure reliability. Current tests may not cover all edge cases and ambiguous scenarios.

### Problem

1. Limited test coverage for auto-detection logic
2. No tests for ambiguous cases (tab vs comma delimiter)
3. No tests for mixed or malformed inputs
4. No confidence score calculation tests
5. No tests for format combination scenarios

### Solution

Create comprehensive test file `api/tests/test_auto_detection.py` covering:

1. **Delimiter detection** (test_auto_detect_delimiter):
   - Comma-delimited files
   - Pipe-delimited files
   - Tab-delimited files
   - Semicolon-delimited files
   - Mixed/ambiguous delimiters
   - Delimiters inside quoted fields (should not match)

2. **Quoting detection** (test_auto_detect_quoting):
   - Double-quote escaping
   - Embedded quotes in data
   - Mixed quote styles
   - No quoting in file
   - Partial quoting (some fields quoted)

3. **Line-ending detection** (test_auto_detect_line_endings):
   - LF (Unix)
   - CRLF (Windows)
   - CR (old Mac)
   - Mixed line endings

4. **Confidence scoring** (test_confidence_scores):
   - Confidence calculation algorithm
   - Edge cases (small files, few rows)
   - Very large files
   - Consistency checks

5. **Combined scenarios** (test_auto_detection_combinations):
   - All valid combinations work
   - Ambiguous combinations handled correctly
   - Fallback to defaults when uncertain

6. **Edge cases** (test_auto_detection_edge_cases):
   - Empty files
   - Single-row files
   - Single-column files
   - Very large files (gigabytes)
   - Files with BOM
   - Unicode in headers

### Test File Structure

```python
# api/tests/test_auto_detection.py

import pytest
from api.services.ingest import AutoDetector

class TestDelimiterDetection:
    def test_comma_delimiter(self):
        """Test detection of comma-delimited CSV"""
        pass

    def test_pipe_delimiter(self):
        """Test detection of pipe-delimited format"""
        pass

    def test_ambiguous_delimiter(self):
        """Test handling of ambiguous delimiters"""
        pass

    # ... more tests

class TestQuotingDetection:
    # ... tests for quoting

class TestLineEndingDetection:
    # ... tests for line endings

class TestConfidenceScoring:
    # ... tests for confidence calculation

class TestEdgeCases:
    # ... tests for edge cases
```

### Golden Files

Create test data files in `api/tests/golden_files/auto_detection/`:
- `comma_simple.csv` - Basic comma-delimited
- `comma_quoted.csv` - Comma with quoted fields
- `pipe_simple.txt` - Pipe-delimited format
- `tab_delimited.txt` - Tab-delimited
- `ambiguous.csv` - Ambiguous delimiter
- `mixed_line_endings.csv` - Mixed LF/CRLF
- `unicode_headers.csv` - Unicode column names
- `large_file_sample.csv` - Sample of large file

### Files Modified/Created

- `api/tests/test_auto_detection.py` - New test file
- `api/tests/golden_files/auto_detection/` - Test data files
- `api/services/ingest.py` - Ensure auto-detection logic is testable
- `api/tests/conftest.py` - Test fixtures

### Testing Notes

- Run tests with pytest: `pytest api/tests/test_auto_detection.py -v`
- Generate coverage report: `pytest --cov=api.services.ingest api/tests/test_auto_detection.py`
- Target minimum 95% coverage for auto-detection logic
- Verify confidence scores are reasonable
- Test performance (auto-detection should be < 100ms for typical files)

### Acceptance Criteria

- [ ] test_auto_detection.py created with comprehensive tests
- [ ] All delimiter types tested
- [ ] Quoting scenarios covered
- [ ] Line endings tested
- [ ] Confidence scoring verified
- [ ] Edge cases handled
- [ ] 95%+ coverage for auto-detection code
- [ ] All tests passing (pytest -v)
- [ ] Golden files committed to repo
- [ ] Documentation updated

---

## Summary of Issues

| # | Issue | Type | Priority | Impact |
|---|-------|------|----------|--------|
| 1 | Add auto-detection metadata schema | Enhancement | High | Backend structure, UI clarity |
| 2 | Fix Tailwind CSS max-width utilities | Bug | High | Layout consistency, appearance |
| 3 | Fix oversized icons | Bug | Critical | Visual/UX polish |
| 4 | Apply VisiQuate branding | Enhancement | Medium | Professional appearance |
| 5 | Redesign page layout with constraints | Enhancement | High | Readability, accessibility |
| 6 | Force dark mode permanently | Enhancement | Medium | Simplification, consistency |
| 7 | Enhance HTML report with CSV data | Enhancement | Medium | User experience, data access |
| 8 | Comprehensive auto-detection tests | Test | High | Reliability, confidence |

## Creation Instructions

Each issue should be created on GitHub with:
1. **Title** - As specified above
2. **Description** - Copy the "Description" and "Problem" sections
3. **Solution** - Copy the "Solution" section
4. **Files Modified** - List from section
5. **Testing** - Copy from "Testing Notes"
6. **Acceptance Criteria** - Copy checklist items
7. **Labels** - bug/enhancement/test, priority level
8. **Project** - data-profiler
9. **Milestone** - UI/UX Improvements (v1.1.0)

## Linking to Pull Requests

When creating a PR to implement these issues:
1. Reference issue number in PR description: `Closes #N`
2. Use issue number in branch name: `issue-N-short-description`
3. Add issue number to commits: `fix: description (fixes #N)`
4. Link PR to issue in GitHub (PR sidebar)

Example:
```
git checkout -b issue-3-fix-oversized-icons
# ... make changes ...
git commit -m "fix: reduce icon sizes across components (fixes #3)"
git push origin issue-3-fix-oversized-icons
# Create PR with "Closes #3" in description
```

---

**Generated:** 2025-11-14
**For:** VQ8 Data Profiler Repository
**Scope:** UI/UX Improvements Phase
