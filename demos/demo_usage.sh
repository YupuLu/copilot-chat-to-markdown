#!/bin/bash

# Demo script showing different usage modes of chat_to_markdown.py

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARENT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== Testing Single File Mode ==="
python3 "$PARENT_DIR/chat_to_markdown.py" "$SCRIPT_DIR/chat.json" -o /tmp/test_single.md
echo "✓ Single file test completed"
echo ""

echo "=== Testing Multiple Files (Combined) Mode ==="
# Combine multiple JSON files if available, otherwise skip
if [ -d "$PARENT_DIR/../paper" ]; then
    python3 "$PARENT_DIR/chat_to_markdown.py" "$PARENT_DIR/../paper/chat.json" "$PARENT_DIR/../paper/long2short/docs/copilot/chat.json" -o /tmp/test_combined.md --combine 2>/dev/null
    echo "✓ Combined files test completed"
else
    echo "ℹ Skipping (test files not available)"
fi
echo ""

echo "=== Testing Folder Mode (Separate) ==="
mkdir -p /tmp/test_output
python3 "$PARENT_DIR/chat_to_markdown.py" "$SCRIPT_DIR/" -o /tmp/test_output/ --separate
echo "✓ Folder mode test completed"
echo ""

echo "=== Checking outputs ==="
ls -lh /tmp/test_single.md /tmp/test_combined.md 2>/dev/null
echo ""
echo "Files in output directory:"
ls -lh /tmp/test_output/ 2>/dev/null
