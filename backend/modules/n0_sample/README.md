# N0 Sample Module

N0 is the simplest reference template for new modules. It defines the standard repository communication pattern: `{ "data": ..., "metadata": { ... } }` and illustrates how to use Pydantic contracts for input/output boundary validation.

## Interface

```python
from backend.shared.contracts.n0_contracts import N0SampleInput

run_sample(data: Union[N0SampleInput, dict]) -> dict
```

`run_sample()` strictly enforces programmatic type-safety and structural checking at the module's exit and entrance boundaries using **Pydantic V2**.

## Input Contract

The module accepts raw dictionaries matching the schema below or a pre-instantiated `N0SampleInput` Pydantic model:

```python
class N0SampleInput(BaseModel):
    text: str = Field(default="", description="Sample input text.")
    tags: List[str] = Field(default_factory=list, description="Sample input list of tags.")
```

## Output Contract

Every module should return a dictionary conforming to the standard output envelope:

```python
class N0SampleData(BaseModel):
    text: Optional[str] = ""
    tags: List[str] = Field(default_factory=list)

class N0SampleMetadata(BaseModel):
    module: str = "n0_sample"
    latency_ms: float = 0.0

class N0SampleOutput(BaseModel):
    data: N0SampleData = Field(default_factory=N0SampleData)
    metadata: N0SampleMetadata = Field(default_factory=N0SampleMetadata)
```

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
    "latency_ms": 1.0
  }
}
```
