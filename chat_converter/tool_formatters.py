"""
Tool formatters for chat log conversion.

Contains functions for formatting tool invocations, text edits,
progress tasks, and related operations.
"""

import json
import os
import re
from typing import Dict, List, Any


def extract_content_from_tool_result(tool_result: Dict[str, Any]) -> str:
    """Extract readable content from a tool call result structure."""
    if not tool_result or not isinstance(tool_result, dict):
        return ""
    
    content = tool_result.get('content', [])
    if not isinstance(content, list) or not content:
        return ""
    
    # Look for the content in the nested structure
    text_parts = []
    
    def extract_text_recursive(node):
        """Recursively extract text from nested node structure."""
        if isinstance(node, dict):
            # Check for direct text content
            if 'text' in node:
                text = node['text']
                if isinstance(text, str) and text.strip():
                    text_parts.append(text)
            
            # Check for children
            if 'children' in node and isinstance(node['children'], list):
                for child in node['children']:
                    extract_text_recursive(child)
            
            # Check for value.node structure (common in tool results)
            if 'value' in node and isinstance(node['value'], dict):
                extract_text_recursive(node['value'])
            
            # Check for node property
            if 'node' in node:
                extract_text_recursive(node['node'])
        
        elif isinstance(node, list):
            for item in node:
                extract_text_recursive(item)
    
    # Process each content item
    for content_item in content:
        extract_text_recursive(content_item)
    
    if text_parts:
        # Join and clean up the extracted text
        full_text = ''.join(text_parts)
        
        # Clean up common artifacts
        # Remove markdown code block markers at start/end if they wrap the entire content
        full_text = full_text.strip()
        if full_text.startswith('```') and full_text.endswith('```'):
            lines = full_text.split('\n')
            if len(lines) >= 2:
                # Remove first and last lines if they're just code block markers
                if lines[0].strip().startswith('```') and lines[-1].strip() == '```':
                    full_text = '\n'.join(lines[1:-1])
        
        return full_text
    
    return ""


def format_tool_invocation_details(tool_data: Dict[str, Any], tool_call_results: Dict[str, Any] = None, tool_call_rounds: List[Dict[str, Any]] = None) -> str:
    """Format tool invocation with input/output in expandable format."""
    past_tense = tool_data.get('pastTenseMessage', {}).get('value', 'Ran tool')
    invocation_msg = tool_data.get('invocationMessage', '')
    if isinstance(invocation_msg, dict):
        invocation_msg = invocation_msg.get('value', 'Ran tool')
    if not invocation_msg:
        invocation_msg = past_tense
    
    # Save original invocation message for file path matching
    original_invocation_msg = invocation_msg
    
    # Clean up the invocation message to be more readable for display
    if '[](file://' in invocation_msg:
        # Extract filename from file URI and create clean display message
        file_match = re.search(r'\[\]\(file://([^)]+)(\#[^)]+)?\)', invocation_msg)
        if file_match:
            file_path = file_match.group(1)
            fragment = file_match.group(2) or ''  # Handle URL fragments like #1-1
            file_name = file_path.split('/')[-1]
            
            # Create clean message - check for additional info like line numbers
            remaining_text = invocation_msg[invocation_msg.find(file_match.group(0)) + len(file_match.group(0)):]
            
            if fragment:
                display_name = f"{file_name}{fragment}"
            else:
                display_name = file_name
            
            if remaining_text.strip():
                invocation_msg = f"Read **{display_name}**{remaining_text}"
            else:
                invocation_msg = f"Read **{display_name}**"
    
    # Simple cleanup for other "Reading" patterns
    invocation_msg = invocation_msg.replace('Reading ', 'Read ')
    
    # Try to find the corresponding tool call in tool_call_rounds by matching the invocation message
    tool_result_content = ""
    
    if tool_call_results and tool_call_rounds:
        # Look for a tool call that matches this invocation
        for round_data in tool_call_rounds:
            if isinstance(round_data, dict) and 'toolCalls' in round_data:
                for tool_call in round_data['toolCalls']:
                    if isinstance(tool_call, dict):
                        tool_call_id = tool_call.get('id', '')
                        tool_name = tool_call.get('name', '')
                        
                        # Try to match by tool name and arguments (for file reads)
                        if tool_name == 'read_file' and 'Read' in original_invocation_msg:
                            # Extract file path from arguments to match with invocation message
                            arguments = tool_call.get('arguments', '')
                            if isinstance(arguments, str):
                                try:
                                    args_dict = json.loads(arguments)
                                    file_path = args_dict.get('filePath', '')
                                    # Use original invocation message for comparison
                                    if file_path and file_path in original_invocation_msg:
                                        # Found matching tool call, get its result
                                        if tool_call_id in tool_call_results:
                                            tool_result_content = extract_content_from_tool_result(tool_call_results[tool_call_id])
                                            break
                                except:
                                    continue
            if tool_result_content:
                break
    
    # Fallback to old method for result details
    result_details = tool_data.get('resultDetails', {})
    input_data = result_details.get('input', '')
    output_data = result_details.get('output', [])
    
    # If we have tool result content, use it; otherwise fall back to old method
    if tool_result_content.strip():
        # IMPORTANT: Process any nested tool invocations FIRST before counting backticks
        # This ensures we count backticks in the FINAL formatted content, not the raw content with markers
        if '__TOOL_INVOCATION__' in tool_result_content:
            tool_result_content = process_special_markers(tool_result_content, tool_call_results, tool_call_rounds)
        
        # Simplify format: Remove "File: path. Lines X-Y: ```lang" header that causes nesting issues
        # Pattern: "File: `path`. Lines X to Y (Z lines total): ```(`)lang" - handles multiple backticks
        file_header_pattern = r'^File:.*?Lines \d+ to \d+.*?:\s*(`+)(\w+)\s*\n'
        match = re.match(file_header_pattern, tool_result_content, re.MULTILINE)
        
        if match:
            # Extract backticks and language from the original header
            original_backticks = match.group(1)  # The backtick sequence (```, ````, etc.)
            lang = match.group(2)       # The language identifier
            # Remove everything up to and including the first newline after ```lang
            simplified_content = tool_result_content[match.end():]
            # Remove trailing backticks if present (matching the opening count)
            if simplified_content.rstrip().endswith(original_backticks):
                simplified_content = simplified_content.rstrip()[:-len(original_backticks)].rstrip()
            
            # IMPORTANT: Check if the simplified content contains code fences
            # If so, we need to use more backticks than the maximum found
            backtick_sequences = re.findall(r'`+', simplified_content)
            max_backticks_in_content = max((len(seq) for seq in backtick_sequences), default=0)
            # Use at least 3 backticks, but more if content has code fences
            num_backticks = max(3, max_backticks_in_content + 1)
            fence_backticks = '`' * num_backticks
            
            # Build clean format with properly nested fences
            lines = []
            lines.append(f"<details>")
            lines.append(f"  <summary>{invocation_msg}</summary>")
            lines.append(f"")
            lines.append(f"{fence_backticks}{lang}")
            lines.append(simplified_content.rstrip())
            lines.append(f"{fence_backticks}")
        else:
            # Fallback for other content formats
            lines = []
            lines.append(f"<details>")
            lines.append(f"  <summary>{invocation_msg}</summary>")
            lines.append(f"")
            
            # Check if the content already contains code fencing
            has_code_fencing = '```' in tool_result_content
            
            if has_code_fencing:
                # Content already has code blocks, determine safe number of backticks
                backtick_sequences = re.findall(r'`+', tool_result_content)
                max_backticks = max((len(seq) for seq in backtick_sequences), default=3)
                # Use one more than the maximum found
                fence_backticks = '`' * (max_backticks + 1)
                
                lines.append(f"{fence_backticks}markdown")
                lines.append(tool_result_content.rstrip())
                lines.append(fence_backticks)
            else:
                # No code fencing, determine content type for syntax highlighting
                file_ext = ""
                if 'file://' in original_invocation_msg:
                    file_match = re.search(r'(\.\w+)', original_invocation_msg)
                    if file_match:
                        file_ext = file_match.group(1)
                
                # Map file extensions to language identifiers
                lang_map = {
                    '.md': 'markdown',
                    '.py': 'python', 
                    '.js': 'javascript',
                    '.json': 'json',
                    '.yaml': 'yaml',
                    '.yml': 'yaml',
                    '.html': 'html',
                    '.css': 'css',
                    '.sh': 'bash',
                    '.txt': 'text'
                }
                lang = lang_map.get(file_ext, '')
                
                lines.append(f"```{lang}")
                lines.append(tool_result_content.rstrip())
                lines.append(f"```")
        
        lines.append(f"")
        lines.append(f"</details>")
        
        return '\n'.join(lines) + '\n\n'
    
    # Original fallback method for when we don't have the actual content
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
        file_name = os.path.basename(file_path) if file_path else 'Unknown file'
        
        edits = edit_data.get('edits', [])
        if not edits:
            return ""
        
        # Collect all meaningful edits
        all_edits = []
        for edit_group in edits:
            if not edit_group:
                continue
            for edit in edit_group:
                if not isinstance(edit, dict):
                    continue
                
                text_content = edit.get('text', '')
                if text_content and text_content.strip():  # Only include non-empty edits
                    all_edits.append(edit)
        
        if not all_edits:
            return ""
        
        # Build the details block
        lines = []
        lines.append(f"<details>")
        lines.append(f"  <summary>🛠️ File Edit: {file_name}</summary>")
        
        # Determine the language for syntax highlighting
        file_ext = os.path.splitext(file_name)[1] if file_name else ''
        lang = 'markdown' if file_ext == '.md' else ('python' if file_ext == '.py' else ('json' if file_ext == '.json' else ''))
        
        # If there's only one substantial edit, show it directly
        if len(all_edits) == 1:
            edit = all_edits[0]
            text_content = edit.get('text', '')
            edit_range = edit.get('range', {})
            
            if edit_range:
                start_line = edit_range.get('startLineNumber', '')
                end_line = edit_range.get('endLineNumber', '')
                if start_line and end_line:
                    if start_line == end_line:
                        lines.append(f"  <p><strong>Modified line {start_line}:</strong></p>")
                    else:
                        lines.append(f"  <p><strong>Modified lines {start_line}-{end_line}:</strong></p>")
                    lines.append(f"")
            
            # Check if content contains backtick fences - count the max and use one more
            max_backticks = 3
            fence_matches = re.findall(r'`+', text_content)
            if fence_matches:
                max_backticks = max(len(m) for m in fence_matches) + 1
                # Ensure at least 3
                max_backticks = max(3, max_backticks)
            
            backticks = '`' * max_backticks
            # Don't use rstrip() - it might remove important content
            # Instead, manually ensure clean boundaries
            clean_content = text_content
            if clean_content.endswith('\n'):
                clean_content = clean_content[:-1]
            lines.append(f"{backticks}{lang}")
            lines.append(clean_content)
            lines.append(backticks)
        
        # If there are multiple edits, try to consolidate them intelligently
        elif len(all_edits) <= 5:  # Show up to 5 edits separately
            for i, edit in enumerate(all_edits):
                text_content = edit.get('text', '')
                edit_range = edit.get('range', {})
                
                if i > 0:
                    lines.append(f"")
                
                if edit_range:
                    start_line = edit_range.get('startLineNumber', '')
                    end_line = edit_range.get('endLineNumber', '')
                    if start_line and end_line:
                        if start_line == end_line:
                            lines.append(f"  <p><strong>Line {start_line}:</strong></p>")
                        else:
                            lines.append(f"  <p><strong>Lines {start_line}-{end_line}:</strong></p>")
                        lines.append(f"")
                
                # Check if content contains backtick fences - count the max and use one more
                max_backticks = 3
                fence_matches = re.findall(r'`+', text_content)
                if fence_matches:
                    max_backticks = max(len(m) for m in fence_matches) + 1
                    max_backticks = max(3, max_backticks)
                
                backticks = '`' * max_backticks
                lines.append(f"{backticks}{lang}")
                lines.append(text_content.rstrip())
                lines.append(backticks)
        
        # If there are many edits, group them into a single consolidated block
        else:
            lines.append(f"  <p><strong>Multiple file changes ({len(all_edits)} edits)</strong></p>")
            lines.append(f"")
            
            # Sort edits by line number for better grouping
            sorted_edits = []
            for edit in all_edits:
                edit_range = edit.get('range', {})
                start_line = edit_range.get('startLineNumber', 0) if edit_range else 0
                sorted_edits.append((start_line, edit))
            sorted_edits.sort(key=lambda x: x[0])
            
            # Combine all edits into one code block, grouping consecutive lines
            combined_content = []
            has_code_blocks = False
            
            i = 0
            while i < len(sorted_edits):
                start_line_num, edit = sorted_edits[i]
                text_content = edit.get('text', '')
                edit_range = edit.get('range', {})
                
                # Check if any content has code blocks
                if '```' in text_content:
                    has_code_blocks = True
                
                # Look ahead to find consecutive edits
                consecutive_edits = [(start_line_num, edit)]
                j = i + 1
                
                while j < len(sorted_edits):
                    next_line_num, next_edit = sorted_edits[j]
                    prev_line_num = consecutive_edits[-1][0]
                    prev_edit_range = consecutive_edits[-1][1].get('range', {})
                    prev_end_line = prev_edit_range.get('endLineNumber', prev_line_num) if prev_edit_range else prev_line_num
                    
                    # Check if this edit is consecutive (starts within 1-2 lines of previous end)
                    if next_line_num != 0 and prev_end_line != 0 and next_line_num <= prev_end_line + 2:
                        consecutive_edits.append((next_line_num, next_edit))
                        j += 1
                    else:
                        break
                
                # Format the group of consecutive edits
                if len(consecutive_edits) > 1:
                    # Multiple consecutive edits - show range and combine content
                    first_line = consecutive_edits[0][0]
                    last_edit_range = consecutive_edits[-1][1].get('range', {})
                    last_line = last_edit_range.get('endLineNumber', consecutive_edits[-1][0]) if last_edit_range else consecutive_edits[-1][0]
                    
                    if first_line and last_line:
                        combined_content.append(f"# Lines {first_line}-{last_line}:")
                    
                    # Combine all consecutive edits into a single coherent text block
                    consecutive_text_parts = []
                    for _, cons_edit in consecutive_edits:
                        cons_text = cons_edit.get('text', '')
                        if cons_text is not None:
                            # Strip only leading/trailing whitespace, but preserve internal structure
                            cons_text = cons_text.strip()
                            consecutive_text_parts.append(cons_text)
                    
                    # Join and clean up the consecutive parts
                    if consecutive_text_parts:
                        combined_consecutive = '\n'.join(consecutive_text_parts)
                        # Replace multiple consecutive blank lines with maximum of 2 blank lines
                        combined_consecutive = re.sub(r'\n\s*\n\s*\n+', '\n\n', combined_consecutive)
                        # Remove any leading/trailing blank lines from the combined content
                        combined_consecutive = combined_consecutive.strip()
                        if combined_consecutive:
                            combined_content.append(combined_consecutive)
                else:
                    # Single edit - show line number
                    if edit_range:
                        start_line = edit_range.get('startLineNumber', '')
                        end_line = edit_range.get('endLineNumber', '')
                        if start_line and end_line:
                            if start_line == end_line:
                                combined_content.append(f"# Line {start_line}:")
                            else:
                                combined_content.append(f"# Lines {start_line}-{end_line}:")
                        else:
                            combined_content.append(f"# Edit {i+1}:")
                    else:
                        combined_content.append(f"# Edit {i+1}:")
                    
                    combined_content.append(text_content.rstrip())
                
                # Add separator between groups (except for the last one)
                i = j
                if i < len(sorted_edits):
                    combined_content.append("")  # Blank line separator
            
            # Use appropriate number of backticks based on content
            final_content = '\n'.join(combined_content)
            if has_code_blocks or '```' in final_content:
                # Find the maximum number of consecutive backticks in the content
                backtick_sequences = re.findall(r'`+', final_content)
                max_backticks = max((len(seq) for seq in backtick_sequences), default=3)
                # Use one more than the maximum found, but at least 4
                fence_backticks = '`' * max(max_backticks + 1, 4)
                
                lines.append(f"{fence_backticks}{lang}")
                lines.append(final_content)
                lines.append(f"{fence_backticks}")
            else:
                lines.append(f"```{lang}")
                lines.append(final_content)
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


def process_special_markers(text: str, tool_call_results: Dict[str, Any] = None, tool_call_rounds: List[Dict[str, Any]] = None) -> str:
    """Process special markers for tool invocations and progress tasks."""
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
            return format_tool_invocation_details(tool_data, tool_call_results, tool_call_rounds)
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
    
    # Fix spacing: Add double newline between sentences ending with . and paragraphs starting with **
    # This handles cases where text like "directory. **Bold text" gets concatenated
    # But NOT numbered list items like "1.\n\n**Header**"
    text = re.sub(r'([a-z][.!?])\s*(\*\*[A-Z])', r'\1\n\n\2', text)
    
    # Fix spacing: Ensure <details> tags start on a new line after list items or headers
    # Pattern matches: numbered list item, header, or any line ending, followed by <details>
    text = re.sub(r'(\n(?:\d+\.|#+)\s+[^\n]+?)(<details>)', r'\1\n\n\2', text)
    # Also handle case where <details> directly follows text without newline
    text = re.sub(r'([^\n])(<details>)', r'\1\n\n\2', text)
    
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


def add_spacing_after_details(markdown_text: str) -> str:
    """Add <br /> after </details> tags when followed by regular content (not another <details>)."""
    lines = markdown_text.split('\n')
    result = []
    
    for i, line in enumerate(lines):
        result.append(line)
        
        # Check if this line ends with </details>
        if line.strip() == '</details>':
            # Look ahead to see what comes next (skip blank lines)
            next_content_idx = i + 1
            while next_content_idx < len(lines) and lines[next_content_idx].strip() == '':
                next_content_idx += 1
            
            # If next content is not another <details> tag and not end of file
            if next_content_idx < len(lines):
                next_line = lines[next_content_idx].strip()
                # Add <br /> if next line is actual content (not <details> or empty)
                if next_line and not next_line.startswith('<details'):
                    # Add a <br /> on the next line after any existing blank line
                    result.append('<br />')
    
    return '\n'.join(result)
