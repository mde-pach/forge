---
paths:
  - "src/**/*.py"
  - "tests/**/*.py"
---

# Python conventions

<!-- Loaded only when a Python file is read. Keep it about the things a
     type checker and a linter cannot express. -->

- Public functions are fully annotated; `Any` needs a comment saying why.
- Errors carry context: raise with a message that names the offending value.
- Tests assert behaviour, not implementation. One reason to fail per test.
