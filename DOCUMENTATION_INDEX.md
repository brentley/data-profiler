# Documentation Index

Complete guide to all documentation for the data profiler project.

## Quick Navigation

### For Users
- **[README.md](README.md)** - Start here! Project overview, features, and quick start
- **[API.md](API.md)** - API endpoint reference with examples
- **[ERROR_CODES.md](ERROR_CODES.md)** - Error code reference and troubleshooting

### For Developers
- **[DEVELOPMENT.md](DEVELOPMENT.md)** - Development setup, testing, and workflow
- **[CODING_STANDARDS.md](CODING_STANDARDS.md)** - Code documentation and style guide
- **[TYPE_INFERENCE.md](TYPE_INFERENCE.md)** - Type detection algorithm and validation rules
- **[DATA_MODEL.md](DATA_MODEL.md)** - Database schema and data structures

---

## Documentation by Topic

### Getting Started

| Document | Purpose |
|----------|---------|
| [README.md](README.md) | Project overview, features, installation |
| [DEVELOPMENT.md](DEVELOPMENT.md) | Development environment setup |

### API Reference

| Document | Purpose |
|----------|---------|
| [API.md](API.md) | Complete API endpoint documentation |
| [API.md - Data Models](API.md#data-models) | Request/response schemas |
| [ERROR_CODES.md](ERROR_CODES.md) | Error codes and resolution |

### Data Handling

| Document | Purpose |
|----------|---------|
| [TYPE_INFERENCE.md](TYPE_INFERENCE.md) | Type detection and validation |
| [TYPE_INFERENCE.md - Examples](TYPE_INFERENCE.md#type-inference-examples) | Type detection examples |
| [DATA_MODEL.md](DATA_MODEL.md) | Database schema |
| [ERROR_CODES.md](ERROR_CODES.md) | Error categorization |

### Code Quality

| Document | Purpose |
|----------|---------|
| [CODING_STANDARDS.md](CODING_STANDARDS.md) | Documentation standards |
| [DEVELOPMENT.md - Testing](DEVELOPMENT.md#testing) | Testing guidelines |
| [DEVELOPMENT.md - Code Quality](DEVELOPMENT.md#code-quality) | Code quality tools |

### Operations

| Document | Purpose |
|----------|---------|
| [README.md - Deployment](README.md#deployment) | Deployment instructions |
| [DATA_MODEL.md - Retention](DATA_MODEL.md#data-retention) | Data cleanup and retention |

---

## Document Descriptions

### README.md

**Purpose**: Project introduction and quick start guide

**Contents**:
- Feature overview
- Architecture overview (backend, frontend, storage)
- Quick start instructions
- Environment configuration
- File format requirements
- Error handling overview
- Performance considerations
- Security information
- Roadmap

**When to Read**: First document to read for anyone new to the project

**Related**: DEVELOPMENT.md, API.md

---

### API.md

**Purpose**: Complete API reference for all endpoints

**Contents**:
- Base URL and authentication
- All endpoints:
  - Health check
  - Create run
  - Upload file
  - Check status
  - Get profile
  - Get metrics
  - Get report
  - Get/confirm keys
- Request/response models
- Error handling
- Rate limiting
- Examples and workflows

**When to Read**: When implementing API calls or understanding endpoint behavior

**Related**: DATA_MODEL.md, ERROR_CODES.md

---

### ERROR_CODES.md

**Purpose**: Reference for all error and warning codes

**Contents**:
- Catastrophic errors (processing stops)
- Non-catastrophic errors (processing continues)
- Error categories:
  - UTF-8 encoding
  - Headers
  - Row structure
  - Quoting/delimiters
  - Type validation
  - Date validation
  - Line endings
  - Keys and uniqueness
  - Resource errors
  - Configuration errors
- Resolution workflows
- Logging specifications

**When to Read**: When debugging errors or implementing error handling

**Related**: README.md, API.md, TYPE_INFERENCE.md

---

### TYPE_INFERENCE.md

**Purpose**: Detailed specification of type detection and validation

**Contents**:
- Type system overview
- Type detection algorithm
- Type-specific patterns and rules:
  - Numeric
  - Money
  - Date
  - String types (alpha, varchar, code)
- NULL handling
- Type validation examples
- Edge cases
- Algorithm pseudocode
- Testing guidelines
- Limitations and future enhancements

**When to Read**: When implementing type detection or understanding validation rules

**Related**: CODING_STANDARDS.md, DEVELOPMENT.md

---

### DATA_MODEL.md

**Purpose**: Complete database schema and data structures

**Contents**:
- Main database schema:
  - runs table
  - columns table
  - errors table
  - candidate_keys table
  - confirmed_keys table
  - logs table
- Temporary database structure
- File artifacts:
  - Profile JSON
  - Metrics CSV
  - Audit log JSON
- Data retention policies
- Performance considerations
- Indexing strategy
- Query optimization

**When to Read**: When implementing database operations or understanding data storage

**Related**: API.md, DEVELOPMENT.md

---

### DEVELOPMENT.md

**Purpose**: Development environment and workflow guide

**Contents**:
- Environment setup
- Running services (Docker, manual)
- Testing guidelines:
  - Unit tests
  - Integration tests
  - Test fixtures
  - TDD workflow
- Code quality (formatting, linting, type checking)
- Project structure
- Common development tasks
- Debugging tips
- Performance optimization
- Troubleshooting FAQ

**When to Read**: When setting up development environment or working on features

**Related**: CODING_STANDARDS.md, README.md

---

### CODING_STANDARDS.md

**Purpose**: Code documentation and style guidelines

**Contents**:
- Python documentation standards:
  - Module docstrings
  - Class docstrings
  - Function docstrings
  - Type hints
  - Inline comments
  - Error documentation
- TypeScript documentation:
  - Component docstrings
  - Function documentation
  - Type definitions
- Comment guidelines
- Error code documentation
- API documentation
- Documentation checklist
- Tools and integration

**When to Read**: Before writing code to understand documentation expectations

**Related**: DEVELOPMENT.md, TYPE_INFERENCE.md

---

### DOCUMENTATION_INDEX.md (This Document)

**Purpose**: Navigation guide for all documentation

**Contents**:
- Quick navigation links
- Documentation by topic
- Document descriptions
- Cross-references

**When to Read**: When looking for specific information or getting oriented

---

## Documentation Organization

### By Audience

**Project Managers / Product Owners**:
1. README.md - Features and scope
2. API.md - Capabilities overview
3. ERROR_CODES.md - Quality considerations

**API Consumers / Users**:
1. README.md - Quick start
2. API.md - Endpoint reference
3. ERROR_CODES.md - Troubleshooting

**Backend Developers**:
1. DEVELOPMENT.md - Setup
2. TYPE_INFERENCE.md - Data handling
3. DATA_MODEL.md - Storage
4. CODING_STANDARDS.md - Code style
5. API.md - API contracts

**Frontend Developers**:
1. DEVELOPMENT.md - Setup
2. API.md - Endpoint reference
3. CODING_STANDARDS.md - Code style
4. README.md - Features overview

**DevOps / Infrastructure**:
1. README.md - Deployment
2. DATA_MODEL.md - Storage requirements
3. DEVELOPMENT.md - Docker setup

---

## Cross-References

### Type Handling
- See TYPE_INFERENCE.md for how types are detected
- See ERROR_CODES.md for type validation errors
- See DATA_MODEL.md for how types are stored
- See API.md for type information in responses
- See DEVELOPMENT.md for testing type inference

### Error Handling
- See ERROR_CODES.md for complete error reference
- See API.md for HTTP status codes
- See CODING_STANDARDS.md for error documentation style
- See README.md for error handling overview

### API Development
- See API.md for endpoint specification
- See DATA_MODEL.md for request/response models
- See CODING_STANDARDS.md for API documentation
- See DEVELOPMENT.md for testing APIs

### Data Processing
- See TYPE_INFERENCE.md for validation rules
- See DATA_MODEL.md for storage
- See ERROR_CODES.md for error handling
- See README.md for file format requirements

---

## Documentation Maintenance

### Keeping Documentation Updated

1. **After API Changes**:
   - Update API.md with new endpoints
   - Update CODING_STANDARDS.md with examples if needed

2. **After Adding Error Codes**:
   - Add to ERROR_CODES.md
   - Reference in TYPE_INFERENCE.md if type-related

3. **After Database Changes**:
   - Update DATA_MODEL.md schema
   - Update related query examples in DEVELOPMENT.md

4. **After Development Process Changes**:
   - Update DEVELOPMENT.md
   - Update CODING_STANDARDS.md if standards changed

### Documentation Review Checklist

- [ ] All public APIs documented in API.md
- [ ] All error codes in ERROR_CODES.md
- [ ] Database schema in DATA_MODEL.md matches code
- [ ] Examples in documentation are current and working
- [ ] Cross-references are accurate
- [ ] Links are not broken
- [ ] Documentation is formatted consistently

---

## Search Quick Reference

### Need Help With...

| Question | Document | Section |
|----------|----------|---------|
| How do I upload a file? | API.md | Upload File |
| What error is E_NUMERIC_FORMAT? | ERROR_CODES.md | Type Validation Errors |
| How are dates validated? | TYPE_INFERENCE.md | Date Type |
| What's the database schema? | DATA_MODEL.md | Database Schema |
| How do I run tests? | DEVELOPMENT.md | Testing |
| How do I write code? | CODING_STANDARDS.md | Python Code Documentation |
| What's the project structure? | DEVELOPMENT.md | Project Structure |
| How do I set up development? | DEVELOPMENT.md | Development Environment Setup |
| What are the API limits? | API.md | Limits |
| How do I debug issues? | DEVELOPMENT.md | Debugging Issues |

---

## Contributing to Documentation

### Guidelines

1. **Keep Documentation Current**: Update docs when code changes
2. **Use Consistent Style**: Follow existing documentation format
3. **Include Examples**: Provide working examples for complex topics
4. **Add Cross-References**: Link related documentation
5. **Test Examples**: Verify examples work before committing

### Adding New Documentation

If adding a new document:

1. Add entry to DOCUMENTATION_INDEX.md
2. Follow existing style and format
3. Include cross-references to related docs
4. Add table of contents for long documents
5. Include "See Also" section

### Updating Existing Documentation

Before updating:

1. Check for related documents that might need updates
2. Update cross-references if structure changes
3. Verify all code examples still work
4. Update this index if scope changes

---

## Version Information

- **Project Version**: 1.0.0
- **Documentation Version**: 1.0.0
- **Last Updated**: 2024-01-15
- **API Version**: 1.0.0

---

## Document Matrix

| Document | Backend | Frontend | DevOps | Product | Users |
|----------|---------|----------|--------|---------|-------|
| README.md | ✓ | ✓ | ✓ | ✓ | ✓ |
| API.md | ✓ | ✓ | ✓ | ✓ | ✓ |
| ERROR_CODES.md | ✓ | ✓ | ✓ | ✓ | ✓ |
| TYPE_INFERENCE.md | ✓ | | | | |
| DATA_MODEL.md | ✓ | | ✓ | | |
| DEVELOPMENT.md | ✓ | ✓ | ✓ | | |
| CODING_STANDARDS.md | ✓ | ✓ | | | |
| DOCUMENTATION_INDEX.md | ✓ | ✓ | ✓ | ✓ | ✓ |

✓ = Recommended reading for this role

---

## Additional Resources

### Documentation
- [README.md](README.md) - Project overview
- [opening-spec.txt](opening-spec.txt) - Original specification

### Code
- `/api/` - Backend source code
- `/web/` - Frontend source code
- `/api/tests/` - Test files with examples

### External Resources
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLite Documentation](https://www.sqlite.org/docs.html)
- [React Documentation](https://react.dev/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)

---

## Getting Help

1. Check DOCUMENTATION_INDEX.md (this document) for navigation
2. Search for your question in the relevant document
3. Check "See Also" sections for related information
4. Review DEVELOPMENT.md troubleshooting section
5. Check code examples in relevant documentation

---

## Feedback

Documentation feedback and suggestions:
1. Check existing issues in project repository
2. Open new issue with "documentation" label
3. Include specific document and section
4. Suggest improvements with examples
