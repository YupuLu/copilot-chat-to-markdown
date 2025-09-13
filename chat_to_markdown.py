#!/usr/bin/env python3
"""
Convert a Copilot chat log JSON file to markdown format.

Usage: python chat_to_markdown.py input.json output.md
"""

import json
import sys
import argparse
from datetime import datetime
from typing import Dict, List, Any

def extract_text_from_response_part(part: Dict[str, Any]) -> str:
    """Extract text content from a response part, handling different formats."""
    if isinstance(part, dict):
        # Skip internal VS Code/Copilot metadata
        if 'kind' in part:
            kind = part['kind']
            # Handle tool invocation messages
            if kind in ['progressTaskSerialized', 'prepareToolInvocation', 'toolInvocationSerialized']:
                content_value = ""
                if 'content' in part and isinstance(part['content'], dict):
                    content_value = part['content'].get('value', '')
                elif 'invocationMessage' in part and isinstance(part['invocationMessage'], dict):
                    content_value = part['invocationMessage'].get('value', '')
                elif 'pastTenseMessage' in part and isinstance(part['pastTenseMessage'], dict):
                    content_value = part['pastTenseMessage'].get('value', '')
                return content_value
            # Skip other internal system messages and metadata
            if kind in ['undoStop', 'codeblockUri', 'textEditGroup']:
                return ""
            # Handle other progress/tool invocation messages
            if 'content' in part and isinstance(part['content'], dict) and 'value' in part['content']:
                return f"*{part['content']['value']}*"
            elif 'invocationMessage' in part and isinstance(part['invocationMessage'], dict) and 'value' in part['invocationMessage']:
                return f"*{part['invocationMessage']['value']}*"
            elif 'pastTenseMessage' in part and isinstance(part['pastTenseMessage'], dict) and 'value' in part['pastTenseMessage']:
                return f"*{part['pastTenseMessage']['value']}*"
            
        # Skip objects with internal IDs or metadata structure
        if 'id' in part and ('kind' in part or '$mid' in part):
            return ""
            
        # Handle regular content
        if 'value' in part:
            return part['value']
        elif 'content' in part:
            if isinstance(part['content'], str):
                return part['content']
            elif isinstance(part['content'], dict) and 'value' in part['content']:
                return part['content']['value']
    
    return str(part) if part else ""

def format_message_text(text: str) -> str:
    """Format message text with proper markdown."""
    if not text:
        return ""
    
    # Clean up excessive whitespace but preserve intentional line breaks
    lines = text.split('\n')
    formatted_lines = []
    
    for line in lines:
        # Clean up the line but preserve leading/trailing spaces for formatting
        clean_line = line.rstrip()
        formatted_lines.append(clean_line)
    
    # Remove excessive blank lines to match bash script formatting
    result_lines = []
    prev_blank = False
    
    for line in formatted_lines:
        is_blank = line.strip() == ''
        # Skip consecutive blank lines
        if is_blank and prev_blank:
            continue
        result_lines.append(line)
        prev_blank = is_blank
    
    return '\n'.join(result_lines)

def format_timestamp(timestamp_ms: int) -> str:
    """Format timestamp from milliseconds to readable format."""
    try:
        timestamp_s = timestamp_ms / 1000
        dt = datetime.fromtimestamp(timestamp_s)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return "Unknown time"

def parse_chat_log(chat_data: Dict[str, Any]) -> str:
    """Parse the chat log JSON and convert to markdown."""
    md_lines = []
    
    # Header
    md_lines.append("# GitHub Copilot Chat Log")
    md_lines.append("")
    md_lines.append(f"**Participant:** {chat_data.get('requesterUsername', 'User')}")
    md_lines.append(f"**Assistant:** {chat_data.get('responderUsername', 'GitHub Copilot')}")
    md_lines.append("")
    md_lines.append("---")
    md_lines.append("")
    
    # Process requests
    requests = chat_data.get('requests', [])
    
    for i, request in enumerate(requests, 1):
        # User message
        md_lines.append(f"## Request {i}")
        md_lines.append("")
        
        # Extract user message text
        message = request.get('message', {})
        message_text = ""
        
        if isinstance(message, dict):
            if 'text' in message:
                message_text = message['text']
            elif 'parts' in message:
                parts = message['parts']
                if isinstance(parts, list):
                    text_parts = []
                    for part in parts:
                        if isinstance(part, dict) and 'text' in part:
                            text_parts.append(part['text'])
                    message_text = ''.join(text_parts)
        
        if message_text:
            md_lines.append("### User")
            md_lines.append("")
            md_lines.append(format_message_text(message_text))
            md_lines.append("")
        
        # Assistant response
        response = request.get('response', [])
        if response:
            md_lines.append("### Assistant")
            md_lines.append("")
            
            response_parts = []
            for part in response:
                part_text = extract_text_from_response_part(part)
                if part_text.strip():
                    response_parts.append(part_text)
            
            if response_parts:
                full_response = '\n'.join(response_parts)
                md_lines.append(format_message_text(full_response))
                md_lines.append("")
        
        # Add timestamp and metadata if available
        result = request.get('result', {})
        if isinstance(result, dict):
            timings = result.get('timings', {})
            if 'totalElapsed' in timings:
                elapsed_ms = timings['totalElapsed']
                elapsed_s = elapsed_ms / 1000
                md_lines.append(f"*Response time: {elapsed_s:.2f} seconds*")
                md_lines.append("")
        
        # Add separator between requests
        if i < len(requests):
            md_lines.append("---")
            md_lines.append("")
    
    return '\n'.join(md_lines)

def main():
    parser = argparse.ArgumentParser(
        description="Convert a Copilot chat log JSON file to markdown format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python chat_to_markdown.py input.json output.md
        """
    )
    parser.add_argument('input_file', help='Input JSON file (chat log)')
    parser.add_argument('output_file', help='Output markdown file')
    
    args = parser.parse_args()
    
    try:
        # Read the JSON file
        with open(args.input_file, 'r', encoding='utf-8') as f:
            chat_data = json.load(f)
        
        # Convert to markdown
        markdown_content = parse_chat_log(chat_data)
        
        # Write the markdown file
        with open(args.output_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        print(f"Successfully converted {args.input_file} to {args.output_file}")
        
    except FileNotFoundError:
        print(f"Error: Could not find input file '{args.input_file}'", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in '{args.input_file}': {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()