import json
import os
import sys

# Add project root to path for imports
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.modules.n17_feedback_processing import process_feedback

# Sample cases
test_cases = [
    {
        "name": "Change intensity (Beach -> Quiet)",
        "user_input": "Tôi muốn đi du lịch biển sôi động",
        "user_tags": ["beach", "party", "nightlife"],
        "img_desc": "Hình ảnh một bãi biển đông đúc với âm nhạc",
        "feedback": "Thực ra tôi thấy hơi mệt, tôi muốn tìm một nơi nào đó cực kỳ yên tĩnh, không dùng cái ảnh này nữa"
    },
    {
        "name": "Add specific preference",
        "user_input": "Du lịch Đà Lạt",
        "user_tags": ["nature", "cool climate"],
        "img_desc": "",
        "feedback": "Tôi muốn thêm các hoạt động trải nghiệm cà phê và săn mây"
    }
]

def run_test():
    print("--- N17 Feedback Chatbot Test ---")
    
    results = []
    
    for case in test_cases:
        print(f"\nRunning case: {case['name']}")
        print(f"Feedback: \"{case['feedback']}\"")
        
        # 1. Process feedback
        result = process_feedback(
            user_input=case["user_input"],
            user_tags=case["user_tags"],
            img_desc=case["img_desc"],
            feedback_text=case["feedback"]
        )
        
        # 2. Print results
        print(f"Refined Text: {result.get('refined_text')}")
        print(f"Refined Tags: {result.get('refined_tags')}")
        print(f"Refined Img Desc: {result.get('refined_img_desc')}")
        print(f"Explanation: {result.get('explanation')}")
        
        meta = result.get("metadata", {})
        usage = meta.get("usage") or {}
        total_tokens = (usage.get("prompt_tokens") or 0) + (usage.get("completion_tokens") or 0)
        print(f"Model: {meta.get('model')} | Tokens: {total_tokens}")
        
        results.append({
            "case": case["name"],
            "input": case,
            "output": result
        })

    # 3. Save to JSON
    output_file = os.path.join(os.path.dirname(__file__), "test_results.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\nAll tests completed. Results saved to: {output_file}")

if __name__ == "__main__":
    run_test()
