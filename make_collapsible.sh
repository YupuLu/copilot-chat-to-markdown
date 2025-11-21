#!/bin/bash
# Post-process markdown file to make request sections collapsible

if [ $# -eq 0 ]; then
    echo "Usage: $0 <markdown_file>"
    echo "Example: $0 output.md"
    exit 1
fi

INPUT_FILE="$1"

echo "Making request sections collapsible in: $INPUT_FILE"

# Create a backup
cp "$INPUT_FILE" "${INPUT_FILE}.backup"

# Use Python for more reliable processing
python3 - "$INPUT_FILE" << 'EOF'
import sys
import re

with open(sys.argv[1], 'r') as f:
    content = f.read()

# Split by the separator that comes before each request anchor
# This splits at "---\n\n" boundaries
sections = re.split(r'(\n---\n+)', content)

output = []
for i, section in enumerate(sections):
    # If this is a separator
    if re.match(r'\n---\n+', section):
        output.append(section)
    # If this section contains a request anchor, wrap it
    elif re.search(r'<a name="request-\d+"></a>', section):
        # Extract request number
        match = re.search(r'<a name="request-(\d+)"></a>', section)
        if match:
            req_num = match.group(1)
            # Wrap the entire section
            wrapped = f'<details open>\n<summary><strong>Request {req_num}</strong></summary>\n\n{section}\n</details>\n'
            output.append(wrapped)
    else:
        # Keep as-is (header, TOC, etc.)
        output.append(section)

# Write output
with open(sys.argv[1], 'w') as f:
    f.write(''.join(output))
EOF

echo "✓ Done! Backup saved as ${INPUT_FILE}.backup"
echo "✓ All request sections are now collapsible (open by default)"
