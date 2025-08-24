# test_parser.py
import json
import logging
from typing import Any, Dict, NamedTuple

# --- Cấu hình logging cơ bản để xem cảnh báo ---
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# --- Mockup đối tượng Rule để test cho dễ ---
class MockRule(NamedTuple):
    name: str
    parameters: Dict[str, Any]

# --- HÀM CẦN KIỂM TRA ---

def _parse_output_values(output: str) -> Dict[str, Any]:
    """
    Phân tích output từ command thành một dictionary để dễ dàng so sánh.
    Hàm này sẽ thử các định dạng sau theo thứ tự:
    1. JSON
    2. Key-Value (phân tách bằng '=' hoặc ':')
    3. Các giá trị phân tách bằng dấu cách
    4. Một giá trị duy nhất
    """
    parsed_data = {"raw_output": output.strip()}
    
    clean_output = output.strip()
    if not clean_output:
        return parsed_data

    try:
        # 1. Thử phân tích dưới dạng JSON
        if (clean_output.startswith('{') and clean_output.endswith('}')) or \
           (clean_output.startswith('[') and clean_output.endswith(']')):
            # Đây là trường hợp JSON, nhưng ta sẽ coi nó là một dict đơn giản
            data = json.loads(clean_output)
            if isinstance(data, dict):
                parsed_data.update(data)
            else: # Nếu là list hoặc giá trị khác
                parsed_data['json_data'] = data
            return parsed_data

        # 2. Thử phân tích dưới dạng Key-Value
        lines = [line.strip() for line in clean_output.splitlines() if line.strip()]
        is_key_value = False
        if lines:
            delimiters = ['=', ':']
            delimiter_found = None

            # Ưu tiên dấu '='
            if any('=' in line for line in lines):
                delimiter_found = '='
            elif any(':' in line for line in lines):
                delimiter_found = ':'

            if delimiter_found:
                temp_dict = {}
                malformed_lines = False
                for line in lines:
                    if delimiter_found not in line:
                        malformed_lines = True
                        break
                    parts = line.split(delimiter_found, 1)
                    if len(parts) == 2:
                        key = parts[0].strip()
                        value = parts[1].strip()
                        temp_dict[key] = value
                
                if temp_dict and not malformed_lines:
                    parsed_data.update(temp_dict)
                    is_key_value = True
        
        if is_key_value:
            return parsed_data

        # 3. Thử phân tích dưới dạng các giá trị phân tách bằng dấu cách
        values = clean_output.split()
        if len(values) > 1:
            parsed_data["all_values"] = " ".join(values)
            for i, val in enumerate(values):
                parsed_data[f"value_{i}"] = val
            return parsed_data
            
        # 4. Nếu không phải các dạng trên, coi đó là một giá trị duy nhất
        parsed_data["single_value"] = clean_output
        return parsed_data

    except Exception as e:
        logging.warning(f"Could not parse command output. Error: {e}. Output: '{clean_output[:100]}'")
        parsed_data["parse_error"] = str(e)
        return parsed_data

def _compare_with_parameters(rule: MockRule, parsed_output: Dict[str, Any]) -> bool:
    """
    So sánh các tham số (parameters) của rule với output đã được phân tích.
    Trả về True nếu tất cả các tham số đều khớp, ngược lại trả về False.
    """
    if not rule.parameters or not isinstance(rule.parameters, dict):
        # Nếu rule không có tham số, coi như thành công nếu command không lỗi
        return "parse_error" not in parsed_output and parsed_output.get("raw_output") is not None

    all_checks_passed = True
    params_to_check = {k: v for k, v in rule.parameters.items() if k not in ["docs", "note", "description"]}

    if not params_to_check:
        # Nếu chỉ có các key tài liệu, cũng coi như thành công
        return "parse_error" not in parsed_output

    for param_key, expected_value in params_to_check.items():
        actual_value = parsed_output.get(param_key)
        
        # So sánh dạng chuỗi để nhất quán
        if str(actual_value) != str(expected_value):
            logging.info(
                f"-> Check FAILED for rule '{rule.name}' on key '{param_key}': "
                f"Expected '{expected_value}' (type: {type(expected_value)}), "
                f"Got '{actual_value}' (type: {type(actual_value)})"
            )
            all_checks_passed = False
            break # Dừng ngay khi có một tham số không khớp
            
    return all_checks_passed


# --- DỮ LIỆU TEST ---

def run_tests():
    """Hàm chính để chạy tất cả các kịch bản test."""
    
    # === Test 1: Kiểm tra hàm _parse_output_values ===
    print("="*20)
    print("PART 1: TESTING _parse_output_values")
    print("="*20)

    outputs_to_test = {
        "Key-Value with '=' (multi-line)": "ucredit=-1\nlcredit=-1\ndcredit=-1\nocredit=-1",
        "Key-Value with ':'": "kernel.pid_max: 4194304",
        "Space-separated values": "4096 87380 56623104",
        "Single numeric value": "1",
        "Single string value": "enabled",
        "JSON object string": '{"setting": "enabled", "value": 1, "mode": "enforcing"}',
        "Empty string": "",
        "Whitespace string": "   \n   ",
        "Malformed Key-Value": "ucredit=-1\njust a random line",
    }

    for name, output in outputs_to_test.items():
        print(f"\n--- Testing output type: [{name}] ---")
        print(f"Input string:\n---\n{output}\n---")
        parsed = _parse_output_values(output)
        print(f"Parsed result: {json.dumps(parsed, indent=2)}")

    # === Test 2: Kiểm tra hàm _compare_with_parameters ===
    print("\n\n" + "="*20)
    print("PART 2: TESTING _compare_with_parameters")
    print("="*20)

    # Output mẫu để so sánh
    pam_auth_output = _parse_output_values("ucredit=-1\nlcredit=-1\ndcredit=-1\nocredit=-1")
    shm_output = _parse_output_values("4096 87380 56623104")
    single_val_output = _parse_output_values("1")
    empty_output = _parse_output_values("")

    # Rule mẫu
    test_scenarios = [
        {
            "description": "PASS: All key-values match",
            "rule": MockRule("check_pam_auth", {"ucredit": -1, "lcredit": -1, "dcredit": -1}),
            "output": pam_auth_output,
            "expected": True
        },
        {
            "description": "FAIL: One key-value is incorrect",
            "rule": MockRule("check_pam_auth_fail", {"ucredit": -1, "lcredit": -2}),
            "output": pam_auth_output,
            "expected": False
        },
        {
            "description": "FAIL: A required key is missing in output",
            "rule": MockRule("check_pam_auth_missing", {"ucredit": -1, "non_existent_key": "abc"}),
            "output": pam_auth_output,
            "expected": False
        },
        {
            "description": "PASS: Space-separated values match individual keys",
            "rule": MockRule("check_shm", {"value_0": 4096, "value_2": 56623104}),
            "output": shm_output,
            "expected": True
        },
        {
            "description": "PASS: Space-separated values match full string",
            "rule": MockRule("check_shm_full", {"all_values": "4096 87380 56623104"}),
            "output": shm_output,
            "expected": True
        },
        {
            "description": "FAIL: Space-separated value is incorrect",
            "rule": MockRule("check_shm_fail", {"value_0": 5000}),
            "output": shm_output,
            "expected": False
        },
        {
            "description": "PASS: Single value matches",
            "rule": MockRule("check_single_value", {"single_value": 1}),
            "output": single_val_output,
            "expected": True
        },
        {
            "description": "FAIL: Single value is incorrect",
            "rule": MockRule("check_single_value_fail", {"single_value": 0}),
            "output": single_val_output,
            "expected": False
        },
        {
            "description": "PASS: Rule has no parameters (should pass if output exists)",
            "rule": MockRule("check_no_params", {}),
            "output": single_val_output,
            "expected": True
        },
        {
            "description": "PASS: Rule has no parameters (should pass on empty output)",
            "rule": MockRule("check_no_params_empty", {}),
            "output": empty_output,
            "expected": True
        },
        {
            "description": "PASS: Rule with only documentation keys",
            "rule": MockRule("check_docs_only", {"note": "This is just a check.", "description": "Details here"}),
            "output": single_val_output,
            "expected": True
        }
    ]

    for scenario in test_scenarios:
        description = scenario['description']
        rule = scenario['rule']
        output = scenario['output']
        expected = scenario['expected']

        result = _compare_with_parameters(rule, output)
        status = "✅ PASS" if result == expected else "❌ FAIL"
        
        print(f"\n--- Testing Scenario: [{description}] ---")
        print(f"Rule: {rule.name}, Parameters: {rule.parameters}")
        print(f"Parsed Output: {output}")
        print(f"Result: {result} | Expected: {expected} -> {status}")

# --- Chạy file ---
if __name__ == "__main__":
    run_tests()