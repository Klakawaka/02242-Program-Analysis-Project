#!/usr/bin/env python3
"""
Expanded syntactic analysis using tree-sitter to detect various patterns:
- Assertions
- Divide by zero
- Array access (out of bounds, null pointer)
- String operations (null pointer, out of bounds)
- Method calls
- Loops (infinite loops)
- Boolean operations
"""

import logging
import tree_sitter
import tree_sitter_java
import jpamb
import sys
from pathlib import Path
from collections import defaultdict

# Handle info command
if len(sys.argv) == 2 and sys.argv[1] == "info":
    print("syntaxer_expanded")
    print("2.0")
    print("The Rice Theorem Cookers")
    print("syntactic,python,tree-sitter")
    print("no")
    sys.exit(0)

# Initialize analyzer info
methodid = jpamb.getmethodid(
    "syntaxer_expanded",
    "2.0",
    "The Rice Theorem Cookers",
    ["syntactic", "python", "tree-sitter"],
    for_science=True,
)

JAVA_LANGUAGE = tree_sitter.Language(tree_sitter_java.language())
parser = tree_sitter.Parser(JAVA_LANGUAGE)

log = logging
log.basicConfig(level=logging.WARNING)  # Set to DEBUG for more output

# Get source file and parse
srcfile = jpamb.sourcefile(methodid).relative_to(Path.cwd())

with open(srcfile, "rb") as f:
    log.debug("parse sourcefile %s", srcfile)
    tree = parser.parse(f.read())

simple_classname = str(methodid.classname.name)
method_name = methodid.extension.name

# Find the class
class_q = tree_sitter.Query(
    JAVA_LANGUAGE,
    f"""
    (class_declaration 
        name: ((identifier) @class-name 
               (#eq? @class-name "{simple_classname}"))) @class
""",
)

class_node = None
for node in tree_sitter.QueryCursor(class_q).captures(tree.root_node)["class"]:
    class_node = node
    break
else:
    log.error(f"could not find a class of name {simple_classname} in {srcfile}")
    sys.exit(-1)

# Find the method
method_q = tree_sitter.Query(
    JAVA_LANGUAGE,
    f"""
    (method_declaration name: 
      ((identifier) @method-name (#eq? @method-name "{method_name}"))
    ) @method
""",
)

method_node = None
for node in tree_sitter.QueryCursor(method_q).captures(class_node)["method"]:
    if not (p := node.child_by_field_name("parameters")):
        continue
    params = [c for c in p.children if c.type == "formal_parameter"]
    if len(params) != len(methodid.extension.params):
        continue
    method_node = node
    break
else:
    log.warning(f"could not find a method of name {method_name} in {simple_classname}")
    sys.exit(-1)

body = method_node.child_by_field_name("body")
assert body and body.text

# Dictionary to store detected patterns
patterns = defaultdict(float)

# ============================================================================
# 1. ASSERTION DETECTION
# ============================================================================
assert_q = tree_sitter.Query(JAVA_LANGUAGE, """(assert_statement) @assert""")
assert_found = any(
    capture_name == "assert"
    for capture_name, _ in tree_sitter.QueryCursor(assert_q).captures(body).items()
)
if assert_found:
    log.debug("Found assertion")
    patterns["assertion error"] = 0.8
else:
    patterns["assertion error"] = 0.1

# ============================================================================
# 2. DIVIDE BY ZERO DETECTION
# ============================================================================
# Look for division operations: x / y or x / 0
divide_q = tree_sitter.Query(
    JAVA_LANGUAGE,
    """
    (binary_expression
        operator: "/"
        right: (_) @divisor) @division
""",
)

divide_by_zero = False
divide_by_variable = False

# Check for division operations
divide_captures = tree_sitter.QueryCursor(divide_q).captures(body)
if "division" in divide_captures:
    for division_node in divide_captures["division"]:  # This is a list
        # Find the right child (divisor) of this division node
        right_child = division_node.child_by_field_name("right")
        if right_child:
            divisor_text = right_child.text.decode() if right_child.text else ""
            if divisor_text.strip() == "0":
                divide_by_zero = True
                log.debug("Found division by literal zero")
                break
            else:
                divide_by_variable = True
                log.debug(f"Found division by variable: {divisor_text}")

if divide_by_zero:
    patterns["divide by zero"] = 0.95
elif divide_by_variable:
    patterns["divide by zero"] = 0.4
else:
    patterns["divide by zero"] = 0.05

# ============================================================================
# 3. ARRAY ACCESS DETECTION
# ============================================================================
# Look for array access: array[index] or array.length
array_access_q = tree_sitter.Query(
    JAVA_LANGUAGE,
    """
    (array_access) @array-access
    (field_access
        object: (_) @array-obj
        field: (identifier) @field-name) @field-access
""",
)

array_access_found = False
array_length_found = False
array_null_assignment = False

array_captures = tree_sitter.QueryCursor(array_access_q).captures(body)
if "array-access" in array_captures:
    array_access_found = True
    log.debug("Found array access")

if "field-access" in array_captures:
    # Check if it's array.length - need to check field-name from the same query
    # Re-run query to get field-name captures
    field_name_q = tree_sitter.Query(
        JAVA_LANGUAGE,
        """
        (field_access
            field: (identifier) @field-name) @field-access
    """,
    )
    field_captures = tree_sitter.QueryCursor(field_name_q).captures(body)
    if "field-name" in field_captures:
        for field_node in field_captures["field-name"]:
            if field_node.text and field_node.text.decode() == "length":
                array_length_found = True
                log.debug("Found array.length access")
                break

# Check for null assignments: array = null
null_assignment_q = tree_sitter.Query(
    JAVA_LANGUAGE,
    """
    (assignment_expression
        left: (_) @left
        right: (null_literal) @null) @null-assign
""",
)

null_captures = tree_sitter.QueryCursor(null_assignment_q).captures(body)
# Get left side from null assignments
left_q = tree_sitter.Query(
    JAVA_LANGUAGE,
    """
    (assignment_expression
        left: (_) @left
        right: (null_literal)) @null-assign
""",
)
left_captures = tree_sitter.QueryCursor(left_q).captures(body)

if "null-assign" in null_captures:
    if "left" in left_captures:
        for left_node in left_captures["left"]:
            left_text = left_node.text.decode() if left_node.text else ""
            # Check if it's an array variable
            if "[]" in left_text or "array" in left_text.lower():
                array_null_assignment = True
                log.debug("Found array null assignment")
                break

if array_null_assignment:
    patterns["null pointer"] = 0.7
    patterns["out of bounds"] = 0.3
elif array_access_found or array_length_found:
    patterns["out of bounds"] = 0.5
    patterns["null pointer"] = 0.3
else:
    patterns["out of bounds"] = 0.1
    patterns["null pointer"] = 0.1

# ============================================================================
# 4. STRING OPERATIONS DETECTION
# ============================================================================
# Look for String method calls: str.length(), str.charAt(), etc.
string_method_q = tree_sitter.Query(
    JAVA_LANGUAGE,
    """
    (method_invocation
        object: (_) @string-obj
        name: (identifier) @method-name) @string-call
""",
)

string_methods = set()
string_null_assignment = False

# Get string method calls
string_captures = tree_sitter.QueryCursor(string_method_q).captures(body)
if "string-call" in string_captures:
    # Get method names from the same query
    if "method-name" in string_captures:
        for method_name_node in string_captures["method-name"]:
            if method_name_node.text:
                method_name = method_name_node.text.decode()
                # Common String methods that can cause errors
                if method_name in ["charAt", "substring", "indexOf", "equals", "concat", "length"]:
                    string_methods.add(method_name)
                    log.debug(f"Found String method: {method_name}")

# Check for String null assignments: String str = null
# Reuse the left_captures from array null assignment check above
if "left" in left_captures:
    for left_node in left_captures["left"]:
        left_text = left_node.text.decode() if left_node.text else ""
        if "String" in left_text or "str" in left_text.lower():
            string_null_assignment = True
            log.debug("Found String null assignment")
            break

if string_null_assignment:
    patterns["null pointer"] = max(patterns.get("null pointer", 0), 0.8)
if "charAt" in string_methods or "substring" in string_methods:
    patterns["out of bounds"] = max(patterns.get("out of bounds", 0), 0.6)

# ============================================================================
# 5. METHOD CALLS DETECTION
# ============================================================================
# Look for method invocations (other than String methods)
method_call_q = tree_sitter.Query(
    JAVA_LANGUAGE,
    """
    (method_invocation) @method-call
""",
)

method_calls = 0
for capture_name, node in tree_sitter.QueryCursor(method_call_q).captures(body).items():
    if capture_name == "method-call":
        method_calls += 1
        log.debug("Found method call")

if method_calls > 0:
    # Method calls can lead to various outcomes depending on what they do
    # Increase probability of assertion errors if there are calls
    patterns["assertion error"] = max(patterns.get("assertion error", 0), 0.3)

# ============================================================================
# 6. LOOP DETECTION (for infinite loops)
# ============================================================================
# Look for while(true) or for(;;) loops
infinite_loop_q = tree_sitter.Query(
    JAVA_LANGUAGE,
    """
    (while_statement) @while-stmt
""",
)

for_loop_q = tree_sitter.Query(
    JAVA_LANGUAGE,
    """
    (for_statement) @for-loop
""",
)

infinite_loop_found = False
# Check for while(true) - check condition manually
while_captures = tree_sitter.QueryCursor(infinite_loop_q).captures(body)
if "while-stmt" in while_captures:
    for while_node in while_captures["while-stmt"]:
        condition = while_node.child_by_field_name("condition")
        if condition and condition.text and condition.text.decode().strip() == "true":
            infinite_loop_found = True
            log.debug("Found while(true) loop")
            break

# Check for for(;;) - empty condition
for_captures = tree_sitter.QueryCursor(for_loop_q).captures(body)
if "for-loop" in for_captures:
    for for_node in for_captures["for-loop"]:
        condition_node = for_node.child_by_field_name("condition")
        if condition_node is None or not condition_node.text or condition_node.text.decode().strip() == "":
            infinite_loop_found = True
            log.debug("Found for(;;) loop")
            break

if infinite_loop_found:
    patterns["*"] = 0.9  # Infinite loop
else:
    patterns["*"] = 0.05

# ============================================================================
# 7. BOOLEAN OPERATIONS DETECTION
# ============================================================================
# Look for boolean parameters and operations
boolean_param_q = tree_sitter.Query(
    JAVA_LANGUAGE,
    """
    (formal_parameter
        type: (boolean_type) @bool-type) @bool-param
""",
)

boolean_params = 0
for capture_name, node in tree_sitter.QueryCursor(boolean_param_q).captures(method_node).items():
    if capture_name == "bool-param":
        boolean_params += 1
        log.debug("Found boolean parameter")

if boolean_params > 0:
    # Boolean parameters often used in assertions
    patterns["assertion error"] = max(patterns.get("assertion error", 0), 0.5)

# ============================================================================
# 8. RETURN STATEMENT DETECTION
# ============================================================================
# If method has early returns, it might avoid errors
return_q = tree_sitter.Query(JAVA_LANGUAGE, """(return_statement) @return""")
returns = sum(1 for capture_name, _ in tree_sitter.QueryCursor(return_q).captures(body).items() if capture_name == "return")

if returns > 1:
    # Multiple returns might indicate early exit paths
    # Reduce some error probabilities
    for key in ["divide by zero", "out of bounds", "null pointer"]:
        if key in patterns:
            patterns[key] *= 0.7

# ============================================================================
# OUTPUT PREDICTIONS
# ============================================================================
# Normalize probabilities (they should sum to reasonable values)
# Output all possible outcomes with their probabilities

outcomes = [
    "ok",
    "divide by zero",
    "assertion error",
    "out of bounds",
    "null pointer",
    "*",  # infinite loop
]

# Ensure all outcomes have some probability
for outcome in outcomes:
    if outcome not in patterns:
        patterns[outcome] = 0.05

# Normalize so probabilities are reasonable (not necessarily summing to 1)
# We'll output percentages
for outcome in outcomes:
    prob = patterns[outcome]
    # Clamp between 0% and 100%
    prob = max(0.0, min(1.0, prob))
    percentage = int(prob * 100)
    print(f"{outcome};{percentage}%")

sys.exit(0)

