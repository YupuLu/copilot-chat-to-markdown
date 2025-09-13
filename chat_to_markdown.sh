#!/bin/bash

# Convert a Copilot chat log JSON file to markdown format
# Usage: ./chat_to_markdown.sh input.json output.md

set -e

# Check if jq is installed
if ! command -v jq &> /dev/null; then
    echo "Error: jq is required but not installed. Please install jq first." >&2
    echo "On macOS: brew install jq" >&2
    echo "On Linux: sudo apt-get install jq (Ubuntu/Debian) or sudo yum install jq (RHEL/CentOS)" >&2
    exit 1
fi

# Check arguments
if [ $# -ne 2 ]; then
    echo "Usage: $0 <input.json> <output.md>"
    echo "Convert a Copilot chat log JSON file to markdown format"
    echo ""
    echo "Examples:"
    echo "  $0 chat.json chat.md"
    echo "  $0 input.json output.md"
    exit 1
fi

INPUT_FILE="$1"
OUTPUT_FILE="$2"

# Check if input file exists
if [ ! -f "$INPUT_FILE" ]; then
    echo "Error: Input file '$INPUT_FILE' not found" >&2
    exit 1
fi

# Check if input file is valid JSON
if ! jq empty "$INPUT_FILE" 2>/dev/null; then
    echo "Error: '$INPUT_FILE' is not valid JSON" >&2
    exit 1
fi

# Function to format timestamp (if needed)
format_timestamp() {
    local timestamp_ms="$1"
    if [ -n "$timestamp_ms" ] && [ "$timestamp_ms" != "null" ]; then
        local timestamp_s=$((timestamp_ms / 1000))
        date -r "$timestamp_s" "+%Y-%m-%d %H:%M:%S" 2>/dev/null || echo "Unknown time"
    else
        echo "Unknown time"
    fi
}

# Start generating markdown
{
    echo "# GitHub Copilot Chat Log"
    echo ""
    
    # Extract basic info
    requester=$(jq -r '.requesterUsername // "User"' "$INPUT_FILE")
    responder=$(jq -r '.responderUsername // "GitHub Copilot"' "$INPUT_FILE")
    
    echo "**Participant:** $requester"
    echo "**Assistant:** $responder"
    echo ""
    echo "---"
    echo ""
    
    # Process each request
    request_count=$(jq -r '.requests | length' "$INPUT_FILE")
    
    for ((i=0; i<request_count; i++)); do
        echo "## Request $((i+1))"
        echo ""
        
        # Extract user message
        user_message=$(jq -r --argjson idx "$i" '
            .requests[$idx].message.text // 
            (.requests[$idx].message.parts // [] | map(.text // "") | join(""))
        ' "$INPUT_FILE")
        
        if [ -n "$user_message" ] && [ "$user_message" != "null" ] && [ "$user_message" != "" ]; then
            echo "### User"
            echo ""
            echo "$user_message"
            echo ""
        fi
        
        # Extract assistant response
        echo "### Assistant"
        echo ""
        
        # Get response parts and extract text
        jq -r --argjson idx "$i" '
            .requests[$idx].response // [] | 
            map(
                if type == "object" then
                    if .kind == "progressTaskSerialized" or .kind == "prepareToolInvocation" or .kind == "toolInvocationSerialized" then
                        (.content.value // .invocationMessage.value // .pastTenseMessage.value // "")
                    elif (.value and (.value | type) == "string") then
                        .value
                    elif (.content and (.content | type) == "object" and .content.value) then
                        .content.value
                    elif (.content and (.content | type) == "string") then
                        .content
                    else
                        ""
                    end
                else
                    if type == "string" then . else "" end
                end
            ) | 
            map(select(. != null and . != "" and . != "*")) | 
            join("\n")
        ' "$INPUT_FILE" 2>/dev/null | sed '/^$/d'
        
        echo ""
        
        # Add response time if available
        elapsed_ms=$(jq -r --argjson idx "$i" '.requests[$idx].result.timings.totalElapsed // null' "$INPUT_FILE")
        if [ -n "$elapsed_ms" ] && [ "$elapsed_ms" != "null" ]; then
            elapsed_s=$(echo "scale=2; $elapsed_ms / 1000" | bc -l 2>/dev/null || echo "$elapsed_ms")
            echo "*Response time: ${elapsed_s} seconds*"
            echo ""
        fi
        
        # Add separator between requests (except for last one)
        if [ $((i+1)) -lt "$request_count" ]; then
            echo "---"
            echo ""
        fi
    done
    
} > "$OUTPUT_FILE"

echo "Successfully converted $INPUT_FILE to $OUTPUT_FILE"