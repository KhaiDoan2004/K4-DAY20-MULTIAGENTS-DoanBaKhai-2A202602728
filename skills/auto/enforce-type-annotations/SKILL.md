---
name: enforce-type-annotations
description: Use this skill to ensure all public functions have proper type annotations.
---
- Review all public functions (names not starting with '_') for type annotations on parameters and return values.
- Use static type checkers (e.g., mypy) to identify missing type annotations.
- Document the expected types in the function docstrings for clarity.
- Ensure that any new functions added during development follow the type annotation rules.
- Regularly audit the codebase to maintain compliance with type annotation standards.
