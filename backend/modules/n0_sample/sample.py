from typing import Any, Union
import time
from backend.shared.contracts.n0_contracts import N0SampleInput, N0SampleOutput

def run_sample(data: Union[N0SampleInput, dict[str, Any]]) -> dict[str, Any]:
    """Normalize input and return the standard data/metadata envelope."""
    t0 = time.time()
    
    # 1. Enforce Input validation boundary
    validated_input = N0SampleInput.model_validate(data) if isinstance(data, dict) else data
    
    # 2. Extract & simple cleaning
    text = str(validated_input.text).strip()
    tags = [str(t).strip() for t in validated_input.tags if str(t).strip()]
    
    # 3. Build & Enforce Output validation boundary
    raw_response = {
        "data": {
            "text": text,
            "tags": tags,
        },
        "metadata": {
            "module": "n0_sample",
            "latency_ms": float(int((time.time() - t0) * 1000))
        }
    }
    
    validated_output = N0SampleOutput.model_validate(raw_response)
    return validated_output.model_dump()
