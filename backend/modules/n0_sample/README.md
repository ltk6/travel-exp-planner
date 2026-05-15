# N0 Sample Module

N0 is the simplest reference template for new modules. It defines the standard repository communication pattern: `{ "data": ..., "metadata": { ... } }`.

## Interface
```python
run_sample(data: dict) -> dict
```

## Standard Pattern
Every module should return a dictionary with two top-level keys:
1. **`data`**: The actual functional result (locations, activities, refined text, etc.).
2. **`metadata`**: Execution context, performance metrics (`latency_ms`), and internal signals.

## Example
**Input:**
```json
{
  "text": " hello ",
  "tags": ["beach", ""]
}
```

**Output:**
```json
{
  "data": {
    "text": "hello",
    "tags": ["beach"]
  },
  "metadata": {
    "module": "n0_sample",
    "latency_ms": 1
  }
}
```
