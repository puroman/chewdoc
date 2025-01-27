# Code Documentation Converter Tool Specification

## Overview
A CLI tool to generate LLM-optimized documentation from Python packages (local or PyPI) with optional additional documentation sources.

## Input Sources

### 1. Package Sources
- PyPI package name and version
- Local package directory
- Git repository URL
- Optional additional documentation files

### 2. Additional Sources
- Markdown documentation files
- RST documentation files
- External API documentation
- GitHub wiki pages
- Project README files

## Command Line Interface

## ChewDoc Package Documentation Generator

### CLI Usage Examples

```bash
# Request package documentation
chewdoc package requests --version 2.31.0 --output docs/output.myst

# Local package documentation
chewdoc package ./my-package \
    --output docs/local-package.myst

# PyPI package documentation
chewdoc package numpy \
    --output docs/numpy-docs.myst
```

### Features

- Generate MyST markdown documentation
- Support for local and PyPI packages
- Detailed docstring and type information extraction

## Package Analysis Features

### 1. Package Metadata Extraction
```yaml
---
package_info:
  name: string
  version: string
  author: string
  license: string
  dependencies: list[string]
  python_requires: string
---
```

### 2. Module Analysis
- Module hierarchy
- Import relationships
- Public API surface
- Usage patterns
- Type hints
- Tests and examples

### 3. Documentation Sources Priority
1. Inline docstrings
2. Package documentation
3. Additional provided documentation
4. External references (if specified)
5. Generated examples from tests

## Document Structure

### 1. Package Overview
```markdown
# Package: {name}

:::{package-info}
version: 1.0.0
repository: https://github.com/org/repo
documentation: https://docs.org/pkg
:::

## Installation
[Generated installation instructions]

## Quick Start
[Generated from examples/tests]
```

### 2. Module Documentation
```markdown
:::{module} package.submodule
description: Module purpose and overview
relationships:
  - imports: other.module
  - used_by: another.module
examples:
  - source: tests/test_module.py
  - source: examples/usage.py
:::
```

### 3. API Reference
```markdown
:::{class} ClassName
module: package.module
description: Class purpose
bases: 
  - BaseClass
  - Interface

Methods:
  :::{method} method_name
  signature: (param: type) -> return_type
  description: Method purpose
  examples:
    ```python
    # Generated from tests/examples
    instance.method_name(param)
    ```
  :::
:::
```

## LLM-Optimized Features

### 1. Context Preservation
```markdown
:::{context}
Component: UserManager
Package: auth_system
Layer: Business Logic
Purpose: Handle user operations
Related Concepts:
  - Authentication
  - User lifecycle
:::
```

### 2. Relationship Mapping
```markdown
:::{dependencies}
Direct:
  - requests>=2.31.0
  - urllib3<2
Indirect:
  - charset-normalizer
  - idna
:::
```

### 3. Usage Patterns
```markdown
:::{usage-patterns}
Common:
  - Web request handling
  - Authentication
  - Response parsing
Anti-patterns:
  - Direct socket usage
  - Sync in async context
:::
```

## Implementation Requirements

### 1. Package Management
- PyPI integration
- Virtual environment handling
- Dependency resolution
- Version management

### 2. Code Analysis
- AST parsing for source code
- Import graph generation
- Type hint extraction
- Test analysis for examples
- Usage pattern detection

### 3. Documentation Aggregation
- Multiple source merging
- Conflict resolution
- Priority handling
- Cross-reference generation

### 4. Output Generation
- Consistent formatting
- Cross-reference validation
- Example validation
- Context enrichment

## Success Metrics

1. Documentation Coverage
- Public API coverage
- Example coverage
- Type hint coverage
- Documentation completeness

2. LLM Effectiveness
- Query success rate
- Context preservation
- Relationship accuracy
- Example relevance

3. User Experience
- Installation success
- Generation speed
- Memory usage
- Error handling

## Development Phases

### Phase 1: Core Package Analysis
- PyPI integration
- Basic code parsing
- Documentation extraction
- Simple output generation

### Phase 2: Enhanced Analysis
- Dependency analysis
- Test/example extraction
- Type hint processing
- Usage pattern detection

### Phase 3: Documentation Enhancement
- Multiple source handling
- Cross-referencing
- Context generation
- Example validation

### Phase 4: LLM Optimization
- Semantic structure
- Query optimization
- Context enrichment
- Relationship mapping

### Phase 5: Advanced Features
- Interactive mode
- Custom templates
- Plugin system
- Documentation testing
