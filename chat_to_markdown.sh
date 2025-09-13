#!/bin/bash

# Convert a Copilot chat log JSON file to markdown format
# Usage: ./chat_to_markdown.sh input.json output.md

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
    
    # Generate table of contents
    request_count=$(jq -r '.requests | length' "$INPUT_FILE")
    if [ "$request_count" -gt 1 ]; then
        echo "## Table of Contents"
        echo ""
        
        for ((i=0; i<request_count; i++)); do
            # Extract first line of user message for preview
            preview=$(jq -r --argjson idx "$i" '
                .requests[$idx].message.text // 
                (.requests[$idx].message.parts // [] | map(.text // "") | join(""))
            ' "$INPUT_FILE" | head -1)
            
            # Limit preview to 80 characters
            if [ ${#preview} -gt 80 ]; then
                preview="${preview:0:77}..."
            fi
            
            if [ -z "$preview" ] || [ "$preview" = "null" ]; then
                preview="[No message content]"
            fi
            
            echo "- [Request $((i+1))](#request-$((i+1))): $preview"
        done
        
        echo ""
    fi
    
    echo "---"
    echo ""
    
    # Process each request
    request_count=$(jq -r '.requests | length' "$INPUT_FILE")
    
    for ((i=0; i<request_count; i++)); do
        # Add navigation links on same line as Request header: ^ (index), < (previous), > (next)
        nav_links="[^](#table-of-contents)"  # Up to table of contents
        
        if [ $i -gt 0 ]; then
            # Previous request link
            nav_links="$nav_links [<](#request-$i)"
        else
            # Placeholder for first request
            nav_links="$nav_links <"
        fi
        
        if [ $((i+1)) -lt $request_count ]; then
            # Next request link
            nav_links="$nav_links [>](#request-$((i+2)))"
        else
            # Placeholder for last request
            nav_links="$nav_links >"
        fi
        
        echo "## Request $((i+1)) $nav_links"
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
        
        # Try to extract comprehensive response from main response array (like Python script)
        response_text=$(jq -r --argjson idx "$i" '
            .requests[$idx].response // [] |
            map(
                if type == "array" and length > 0 then
                    # Handle nested arrays (detailed VS Code response structure)
                    map(if type == "object" and has("text") then .text else empty end) | join("")
                elif type == "object" then
                    if .kind == "progressTaskSerialized" or .kind == "prepareToolInvocation" or .kind == "toolInvocationSerialized" then
                        (.content.value // .invocationMessage.value // .pastTenseMessage.value // "")
                    elif has("value") and (.value | type) == "string" then
                        .value
                    elif has("content") and (.content | type) == "object" and .content.value then
                        .content.value
                    elif has("content") and (.content | type) == "string" then
                        .content
                    elif has("text") then
                        .text
                    else
                        ""
                    end
                else
                    if type == "string" then . else "" end
                end
            ) | 
            map(select(. != null and . != "" and . != "*")) | 
            join("")
        ' "$INPUT_FILE" 2>/dev/null)
        
        # Also try to extract from toolCallRounds as secondary source
        tool_response=$(jq -r --argjson idx "$i" '
            .requests[$idx].result.metadata.toolCallRounds // [] |
            map(.response // "") |
            map(select(. != null and . != "")) |
            join("\n")
        ' "$INPUT_FILE" 2>/dev/null)
        
        # Use the response with more content
        final_response=""
        if [ -n "$response_text" ] && [ "$response_text" != "null" ] && ! [[ "$response_text" =~ ^\s*$ ]]; then
            final_response="$response_text"
        fi
        if [ -n "$tool_response" ] && [ "$tool_response" != "null" ] && ! [[ "$tool_response" =~ ^\s*$ ]]; then
            if [ -z "$final_response" ] || [ ${#tool_response} -gt ${#final_response} ]; then
                final_response="$tool_response"
            fi
        fi
        
        # Clean up the response and output it
        if [ -n "$final_response" ]; then
            # Clean up excessive whitespace and formatting
            echo "$final_response" | sed 's/^[ \t]*//g' | sed '/^$/N;/^\n$/d'
        fi
        
        echo ""
        
        # Add response time if available
        elapsed_ms=$(jq -r --argjson idx "$i" '.requests[$idx].result.timings.totalElapsed // null' "$INPUT_FILE")
        if [ -n "$elapsed_ms" ] && [ "$elapsed_ms" != "null" ] && [[ "$elapsed_ms" =~ ^[0-9]+$ ]]; then
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