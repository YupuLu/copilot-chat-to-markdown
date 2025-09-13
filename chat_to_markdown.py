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
            # Handle textEditGroup - extract edit content for tool invocations
            if kind == 'textEditGroup':
                return f"__TEXT_EDIT_GROUP__{json.dumps(part)}__TEXT_EDIT_GROUP__"
            # Skip other internal VS Code objects
            if kind in ['inlineReference', 'undoStop', 'codeblockUri']:
                return ""
            # Handle tool invocation messages - return special markers for processing
            if kind == 'toolInvocationSerialized':
                return f"__TOOL_INVOCATION__{json.dumps(part)}__TOOL_INVOCATION__"
            elif kind == 'progressTaskSerialized':
                return f"__PROGRESS_TASK__{json.dumps(part)}__PROGRESS_TASK__"
            elif kind == 'prepareToolInvocation':
                return ""  # Skip these as they're handled in toolInvocationSerialized
            # Handle other progress/tool invocation messages
            if 'content' in part and isinstance(part['content'], dict) and 'value' in part['content']:
                return f"*{part['content']['value']}*"
            elif 'invocationMessage' in part and isinstance(part['invocationMessage'], dict) and 'value' in part['invocationMessage']:
                return f"*{part['invocationMessage']['value']}*"
            elif 'pastTenseMessage' in part and isinstance(part['pastTenseMessage'], dict) and 'value' in part['pastTenseMessage']:
                return f"*{part['pastTenseMessage']['value']}*"
            
        # Skip objects with internal IDs, metadata structure, or inline references
        if ('id' in part and ('kind' in part or '$mid' in part)) or '$mid' in part or 'inlineReference' in part:
            return ""
            
        # Handle regular content
        if 'value' in part:
            value = part['value']
            # Skip if the value is just a raw object representation
            if isinstance(value, str) and ('{' in value and '$mid' in value):
                return ""
            # Skip empty code block artifacts from tool invocations
            if isinstance(value, str) and value.strip() == "```":
                return ""
            return value
        elif 'content' in part:
            if isinstance(part['content'], str):
                return part['content']
            elif isinstance(part['content'], dict) and 'value' in part['content']:
                return part['content']['value']
    
    # Skip if the part itself looks like raw metadata
    if isinstance(part, str) and ('{' in part and ('$mid' in part or 'kind' in part)):
        return ""
        
    return str(part) if part else ""

def format_message_text(text: str) -> str:
    """Format message text with proper markdown."""
    if not text:
        return ""
    
    # Remove any remaining raw object representations
    if '{' in text and ('$mid' in text or 'kind' in text):
        # Try to clean out just the problematic parts
        lines = text.split('\n')
        clean_lines = []
        for line in lines:
            if not ('{' in line and ('$mid' in line or 'kind' in line)):
                clean_lines.append(line)
        text = '\n'.join(clean_lines)
    
    # Fix checkmark lists that need proper spacing for markdown rendering
    # Many markdown renderers don't properly separate lines that start with emojis
    import re
    lines = text.split('\n')
    formatted_lines = []
    
    for i, line in enumerate(lines):
        # If this line starts with a checkmark and it's not the first checkmark in a sequence,
        # add a <br> before it to force a line break
        if (line.strip().startswith('✅') and 
            i > 0 and 
            not lines[i - 1].strip().startswith('✅') and
            lines[i - 1].strip() != ''):
            formatted_lines.append(line)
        elif (line.strip().startswith('✅') and 
              i > 0 and 
              lines[i - 1].strip().startswith('✅')):
            formatted_lines.append('<br>' + line)
        else:
            formatted_lines.append(line)
    
    text = '\n'.join(formatted_lines)
    
    # Clean up excessive whitespace but preserve intentional line breaks
    lines = text.split('\n')
    formatted_lines = []
    
    for line in lines:
        # Clean up the line but preserve leading/trailing spaces for formatting
        clean_line = line.rstrip()
        formatted_lines.append(clean_line)
    
    
    # Remove excessive blank lines and clean up artifacts
    result_lines = []
    prev_blank = False
    
    for line in formatted_lines:
        is_blank = line.strip() == ''
        # Skip consecutive blank lines
        if is_blank and prev_blank:
            continue
        # Skip lines that are just malformed artifacts
        if line.strip() and not ('{' in line and ('$mid' in line or 'kind' in line)):
            result_lines.append(line)
        elif is_blank:
            result_lines.append(line)
        prev_blank = is_blank
    
    # Remove trailing empty lines
    while result_lines and result_lines[-1].strip() == '':
        result_lines.pop()
    
    return '\n'.join(result_lines)

def format_timestamp(timestamp_ms: int) -> str:
    """Format timestamp from milliseconds to readable format."""
    try:
        timestamp_s = timestamp_ms / 1000
        dt = datetime.fromtimestamp(timestamp_s)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return "Unknown time"

def format_references(variables: List[Dict[str, Any]]) -> str:
    """Format variable data references in the expandable format."""
    if not variables:
        return ""
    
    content_lines = []
    reference_count = 0
    
    for var in variables:
        name = var.get('name', 'Unknown')
        kind = var.get('kind', '')
        origin_label = var.get('originLabel', '')
        
        # Format the reference name
        if name.startswith('prompt:'):
            display_name = name[7:]  # Remove 'prompt:' prefix
            icon = "☰"
        else:
            display_name = name
            icon = "📄"
        
        content_lines.append(f"{icon} {display_name}")
        reference_count += 1
        
        # Add origin label info if available - count as separate reference
        if kind == 'promptFile' and origin_label:
            # Extract the key part from origin label
            if 'github.copilot.chat.' in origin_label:
                label_part = origin_label.split('github.copilot.chat.')[-1].split(' ')[0]
                content_lines.append(f"⚙️ github.copilot.chat.{label_part}")
                reference_count += 1
    
    # Create details block with correct count
    summary = f"Used {reference_count} references"
    content = '<br>'.join(content_lines)
    
    return f"""<details>
  <summary>{summary}</summary>
  <p>{content}</p>
</details>


"""

def format_tool_invocation_details(tool_data: Dict[str, Any]) -> str:
    """Format tool invocation with input/output in expandable format."""
    past_tense = tool_data.get('pastTenseMessage', {}).get('value', 'Ran tool')
    invocation_msg = tool_data.get('invocationMessage', '')
    if isinstance(invocation_msg, dict):
        invocation_msg = invocation_msg.get('value', 'Ran tool')
    if not invocation_msg:
        invocation_msg = past_tense
    
    result_details = tool_data.get('resultDetails', {})
    
    # Get input and output data
    input_data = result_details.get('input', '')
    output_data = result_details.get('output', [])
    
    if not input_data:
        return ""
    
    try:
        if isinstance(input_data, str):
            input_obj = json.loads(input_data)
        else:
            input_obj = input_data
        
        # Format input as JSON
        input_json = json.dumps(input_obj, indent=2)
        
        # Build the details block
        lines = []
        lines.append(f"<details>")
        lines.append(f"  <summary>{invocation_msg}</summary>")
        lines.append(f"  <p>Input</p>")
        lines.append(f"")
        lines.append(f"```json")
        lines.append(f"{input_json}")
        lines.append(f"```")
        lines.append(f"")
        
        # Add output if available
        if output_data and isinstance(output_data, list) and output_data:
            output_value = output_data[0].get('value', '') if isinstance(output_data[0], dict) else str(output_data[0])
            lines.append(f"  <p>Output</p>")
            lines.append(f"")
            lines.append(f"```json")
            lines.append(f"{output_value}")
            lines.append(f"```")
            lines.append(f"")
        
        lines.append(f"</details>")
        
        return '\n'.join(lines) + '\n\n'
        
    except:
        # Fallback for malformed input
        return f"<details>\n  <summary>{invocation_msg}</summary>\n  <p>Completed with input: {input_data}</p>\n</details>\n\n"


def format_text_edit_group(edit_data: Dict[str, Any]) -> str:
    """Format textEditGroup data showing the actual file changes."""
    try:
        uri = edit_data.get('uri', {})
        file_path = uri.get('fsPath', '')
        if not file_path:
            file_path = uri.get('path', 'Unknown file')
        
        # Extract just the filename for display
        import os
        file_name = os.path.basename(file_path) if file_path else 'Unknown file'
        
        edits = edit_data.get('edits', [])
        if not edits:
            return ""
        
        # Build the details block
        lines = []
        lines.append(f"<details>")
        lines.append(f"  <summary>🛠️ File Edit: {file_name}</summary>")
        
        # Process each edit
        for edit_group in edits:
            if not edit_group:
                continue
            for edit in edit_group:
                if not isinstance(edit, dict):
                    continue
                
                text_content = edit.get('text', '')
                edit_range = edit.get('range', {})
                
                if not text_content:
                    continue
                
                # Show the range if available
                if edit_range:
                    start_line = edit_range.get('startLineNumber', '')
                    end_line = edit_range.get('endLineNumber', '')
                    if start_line and end_line:
                        lines.append(f"  <p><strong>Modified lines {start_line}-{end_line}:</strong></p>")
                        lines.append(f"")
                
                # Determine the language for syntax highlighting
                file_ext = os.path.splitext(file_name)[1] if file_name else ''
                lang = 'markdown' if file_ext == '.md' else ('python' if file_ext == '.py' else ('json' if file_ext == '.json' else ''))
                
                lines.append(f"```{lang}")
                lines.append(text_content)
                lines.append(f"```")
                lines.append(f"")
        
        lines.append(f"</details>")
        
        return '\n'.join(lines) + '\n\n'
        
    except Exception as e:
        return ""

def format_progress_task(task_data: Dict[str, Any]) -> str:
    """Format progress task with checkmark."""
    content = task_data.get('content', {})
    if isinstance(content, dict):
        value = content.get('value', '')
        if value:
            return f"\n✔️ {value}\n"
    return ""

def process_special_markers(text: str) -> str:
    """Process special markers for tool invocations and progress tasks."""
    import re
    
    # Process text edit group markers
    def replace_text_edit_group(match):
        try:
            edit_data = json.loads(match.group(1))
            return format_text_edit_group(edit_data)
        except:
            return ""
    
    text = re.sub(r'__TEXT_EDIT_GROUP__(.*?)__TEXT_EDIT_GROUP__', replace_text_edit_group, text, flags=re.DOTALL)
    
    # Process tool invocation markers
    def replace_tool_invocation(match):
        try:
            tool_data = json.loads(match.group(1))
            return format_tool_invocation_details(tool_data)
        except:
            return ""
    
    text = re.sub(r'__TOOL_INVOCATION__(.*?)__TOOL_INVOCATION__', replace_tool_invocation, text, flags=re.DOTALL)
    
    # Process progress task markers
    def replace_progress_task(match):
        try:
            task_data = json.loads(match.group(1))
            return format_progress_task(task_data)
        except:
            return ""
    
    text = re.sub(r'__PROGRESS_TASK__(.*?)__PROGRESS_TASK__', replace_progress_task, text, flags=re.DOTALL)
    
    return text

def format_tool_calls(tool_calls: list) -> str:
    """Format tool calls for display."""
    if not tool_calls:
        return ""
    
    formatted_calls = []
    for tool_call in tool_calls:
        if not isinstance(tool_call, dict):
            continue
            
        name = tool_call.get('name', 'Unknown tool')
        
        # Format the tool call as a compact command
        call_line = f"🔧 **{name}**"
        
        # Format arguments if present - compact style
        arguments = tool_call.get('arguments')
        if arguments:
            try:
                if isinstance(arguments, str):
                    # Try to parse as JSON for parameter extraction
                    import json
                    args_dict = json.loads(arguments)
                elif isinstance(arguments, dict):
                    args_dict = arguments
                else:
                    args_dict = {"arguments": str(arguments)}
                
                # Format key parameters compactly
                params = []
                for key, value in args_dict.items():
                    if isinstance(value, str) and len(value) > 50:
                        # Truncate long strings
                        value = value[:47] + "..."
                    elif isinstance(value, list) and len(value) > 3:
                        # Truncate long arrays
                        value = value[:3] + ["..."]
                    params.append(f"{key}={value}")
                
                if params:
                    call_line += f" `{', '.join(params)}`"
                    
            except (json.JSONDecodeError, ImportError):
                # Fallback to simple string representation
                if isinstance(arguments, str) and len(arguments) > 50:
                    call_line += f" `{arguments[:47]}...`"
                else:
                    call_line += f" `{arguments}`"
        
        formatted_calls.append(call_line)
    
    return '\n'.join(formatted_calls) + '\n'

def parse_chat_log(chat_data: Dict[str, Any]) -> str:
    """Parse the chat log JSON and convert to markdown."""
    md_lines = []
    
    # Header
    md_lines.append("# GitHub Copilot Chat Log")
    md_lines.append("")
    md_lines.append(f"**Participant:** {chat_data.get('requesterUsername', 'User')}")
    md_lines.append(f"**Assistant:** {chat_data.get('responderUsername', 'GitHub Copilot')}")
    md_lines.append("")
    
    # Generate table of contents
    requests = chat_data.get('requests', [])
    if len(requests) > 1:
        md_lines.append('<a name="table-of-contents"></a>')
        md_lines.append("## Table of Contents")
        md_lines.append("")
        for i, request in enumerate(requests, 1):
            # Extract first line of user message for preview
            message = request.get('message', {})
            preview = ""
            if isinstance(message, dict):
                if 'text' in message:
                    preview = message['text']
                elif 'parts' in message:
                    parts = message['parts']
                    if isinstance(parts, list):
                        for part in parts:
                            if isinstance(part, dict) and 'text' in part:
                                preview = part['text']
                                break
            
            # Get first line for preview (limit to 80 chars)
            if preview:
                first_line = preview.split('\n')[0]
                if len(first_line) > 80:
                    first_line = first_line[:77] + "..."
            else:
                first_line = "[No message content]"
            
            md_lines.append(f"- [Request {i}](#request-{i}): {first_line}")
        
        md_lines.append("")
    
    md_lines.append("---")
    md_lines.append("")
    
    # Process requests
    requests = chat_data.get('requests', [])
    
    for i, request in enumerate(requests, 1):
        # User message with navigation links on same line
        nav_links = []
        nav_links.append("[^](#table-of-contents)")  # Up to table of contents
        
        if i > 1:  # Previous request link
            nav_links.append(f"[<](#request-{i-1})")
        else:
            nav_links.append("<")  # Placeholder for first request
            
        if i < len(requests):  # Next request link
            nav_links.append(f"[>](#request-{i+1})")
        else:
            nav_links.append(">")  # Placeholder for last request
        
        # Add explicit anchor and header with navigation
        md_lines.append(f'<a name="request-{i}"></a>')
        md_lines.append(f"## Request {i} {' '.join(nav_links)}")
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
            
            # Add references if they exist
            variable_data = request.get('variableData', {})
            if isinstance(variable_data, dict):
                variables = variable_data.get('variables', [])
                if variables:
                    references_formatted = format_references(variables)
                    if references_formatted.strip():
                        md_lines.append(references_formatted)
            
            # First try to get consolidated response from toolCallRounds (like bash script)
            consolidated_response = ""
            result = request.get('result', {})
            if isinstance(result, dict):
                metadata = result.get('metadata', {})
                if isinstance(metadata, dict):
                    tool_call_rounds = metadata.get('toolCallRounds', [])
                    if isinstance(tool_call_rounds, list):
                        tool_responses = []
                        all_tool_calls = []
                        
                        for round_data in tool_call_rounds:
                            if isinstance(round_data, dict):
                                # Skip collecting tool calls - we'll get them from the detailed response parts
                                # Collect response from this round
                                if 'response' in round_data:
                                    round_response = round_data['response']
                                    if isinstance(round_response, str) and round_response.strip():
                                        tool_responses.append(round_response.strip())
                        
                        # Don't format tool calls here - they'll be handled by the detailed response processing
                        
                        # Add consolidated responses
                        if tool_responses:
                            consolidated_response = '\n'.join(tool_responses)
            
            # If no consolidated response available, fall back to incremental response parts
            if not consolidated_response.strip():
                response_parts = []
                for part in response:
                    part_text = extract_text_from_response_part(part)
                    if part_text and part_text.strip():
                        response_parts.append(part_text)
                
                if response_parts:
                    consolidated_response = '\n'.join(response_parts)
            
            # Always process the incremental response parts for tool details, even if we have consolidated response
            response_parts = []
            for part in response:
                part_text = extract_text_from_response_part(part)
                if part_text and part_text.strip():
                    response_parts.append(part_text)
            
            if response_parts:
                incremental_response = '\n'.join(response_parts)
                # Process special markers for tool invocations
                incremental_response = process_special_markers(incremental_response)
                
                # Use the incremental response if it has more detail, otherwise use consolidated
                if ('__TOOL_INVOCATION__' in '\n'.join(response_parts) or 
                    '__TEXT_EDIT_GROUP__' in '\n'.join(response_parts) or 
                    not consolidated_response.strip()):
                    consolidated_response = incremental_response
            
            # Use whichever response has more meaningful content
            if consolidated_response.strip():
                cleaned_response = format_message_text(consolidated_response)
                if cleaned_response.strip():
                    md_lines.append(cleaned_response)
                    md_lines.append("")
        
        # Add timestamp and metadata if available
        if not result:  # Only get result if not already retrieved above
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