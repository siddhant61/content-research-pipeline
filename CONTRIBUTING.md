# Contributing to Content Research Pipeline

Thank you for your interest in contributing to the Content Research Pipeline! This document provides guidelines and information for contributors.

## Code of Conduct

By participating in this project, you agree to abide by our Code of Conduct. Please be respectful and professional in all interactions.

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in the [Issues](https://github.com/siddhant61/content-research-pipeline/issues)
2. If not, create a new issue using the bug report template
3. Provide as much detail as possible, including:
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details
   - Error messages and logs

### Suggesting Features

1. Check if the feature has already been suggested
2. Create a new issue using the feature request template
3. Describe the use case and expected behavior
4. Provide implementation ideas if you have them

### Code Contributions

1. **Fork the repository**
2. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes**
4. **Add tests** for your changes
5. **Run the test suite**:
   ```bash
   pytest tests/
   ```
6. **Run code quality checks**:
   ```bash
   black src/
   flake8 src/
   mypy src/
   ```
7. **Commit your changes**:
   ```bash
   git commit -m "Add: brief description of changes"
   ```
8. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```
9. **Create a Pull Request**

## Development Setup

### Prerequisites

- Python 3.8+
- Git
- OpenAI API key
- Google Search API key and CSE ID

### Setup

1. **Clone your fork**:
   ```bash
   git clone https://github.com/your-username/content-research-pipeline.git
   cd content-research-pipeline
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   pip install -e ".[dev]"
   python -m spacy download en_core_web_sm
   ```

4. **Set up environment variables**:
   ```bash
   cp env.example .env
   # Edit .env with your API keys
   ```

5. **Run tests**:
   ```bash
   pytest tests/
   ```

## Code Style

We use several tools to maintain code quality:

- **Black** for code formatting
- **flake8** for linting
- **mypy** for type checking
- **pytest** for testing

### Running Code Quality Checks

```bash
# Format code
black src/

# Lint code
flake8 src/

# Type check
mypy src/

# Run tests
pytest tests/ --cov=src
```

## Project Structure

```
content_research_pipeline/
├── src/content_research_pipeline/
│   ├── config/          # Configuration management
│   ├── core/            # Core business logic
│   ├── data/            # Data models
│   ├── services/        # External service integrations
│   ├── utils/           # Utility functions
│   └── visualization/   # Report generation
├── tests/               # Test files
├── docs/                # Documentation
└── .github/             # GitHub workflows and templates
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test file
pytest tests/test_search.py

# Run with verbose output
pytest -v
```

### Writing Tests

- Write tests for all new functionality
- Use descriptive test names
- Include both positive and negative test cases
- Mock external APIs in tests
- Follow the existing test patterns

Example test structure:
```python
def test_search_service_should_return_results():
    # Given
    service = SearchService()
    query = "test query"
    
    # When
    results = await service.search_web(query)
    
    # Then
    assert len(results) > 0
    assert all(isinstance(r, SearchResult) for r in results)
```

## Documentation

- Update documentation for any new features
- Use clear, concise language
- Include code examples where appropriate
- Update the README if needed

## Commit Messages

Use clear, descriptive commit messages:

```
Add: new feature description
Fix: bug description
Update: update description
Remove: removal description
Docs: documentation changes
Test: test-related changes
```

## Review Process

1. All submissions require review before merging
2. Address any feedback from reviewers
3. Ensure all CI checks pass
4. Keep PRs focused and reasonably sized

## Release Process

1. Features are merged into `develop` branch
2. Releases are created from `main` branch
3. Semantic versioning is used (MAJOR.MINOR.PATCH)
4. Release notes are generated automatically

## Getting Help

- Check the [README](README.md) for basic usage
- Look at existing issues for common problems
- Create a new issue if you need help

## Recognition

Contributors will be recognized in the project's README and release notes.

Thank you for contributing to the Content Research Pipeline! 