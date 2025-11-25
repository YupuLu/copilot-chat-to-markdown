"""
Text processing utilities for chat log conversion.

Contains functions for extracting text from response parts,
balancing code fences, and formatting message text.
"""

import json
import os
import re
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
            # Handle inline references - extract the referenced name/symbol
            if kind == 'inlineReference':
                inline_ref = part.get('inlineReference', {})
                if isinstance(inline_ref, dict):
                    # Try to get the name first
                    if 'name' in inline_ref:
                        return f"`{inline_ref['name']}`"
                    # If no name, try to extract filename from path
                    elif 'path' in inline_ref:
                        filename = os.path.basename(inline_ref['path'])
                        return f"`{filename}`"
                return ""
            # Skip other internal VS Code objects
            if kind in ['undoStop', 'codeblockUri']:
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
            
        # Skip objects with internal IDs or metadata structure
        if ('id' in part and ('kind' in part or '$mid' in part)) or '$mid' in part:
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


def smart_join_parts(parts: list) -> str:
    """
    Intelligently join response parts, adding spacing when needed.
    Detects paragraph boundaries and adds proper spacing.
    """
    if not parts:
        return ""
    
    result = []
    for i, part in enumerate(parts):
        if not part or not part.strip():
            continue
        
        part_stripped = part.strip()
        
        # Add the part
        result.append(part)
        
        # Check if we need spacing before the next part
        if i < len(parts) - 1:
            # Find next non-empty part
            next_idx = i + 1
            while next_idx < len(parts) and (not parts[next_idx] or not parts[next_idx].strip()):
                next_idx += 1
            
            if next_idx < len(parts):
                next_part = parts[next_idx].strip()
                
                # Add double newline if:
                # 1. Current part ends with sentence/paragraph (., !, ?) 
                # 2. Next part starts with paragraph indicator (**, #, <details)
                current_ends_sentence = part_stripped.endswith(('.', '!', '?'))
                next_starts_paragraph = (next_part.startswith('**') or 
                                        next_part.startswith('#') or
                                        next_part.startswith('<details'))
                
                if current_ends_sentence and next_starts_paragraph:
                    # Ensure we have proper spacing
                    if not result[-1].endswith('\n\n'):
                        if result[-1].endswith('\n'):
                            result.append('\n')
                        else:
                            result.append('\n\n')
    
    return ''.join(result)


def balance_code_fences(text: str) -> str:
    """Balance code fences by fixing unmatched fences to prevent rendering issues."""
    # Find all code fences with their backtick counts and positions
    # Opening fence: 3+ backticks with optional language
    # Closing fence: when stack active, any number of backticks without language
    fence_pattern = r'^(`{3,})(\w*)\s*$'
    lines = text.split('\n')
    fence_stack = []  # Stack to track opening fences
    
    # Track whether we're inside a <details> block (skip balancing there)
    in_details = False
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Track <details> blocks - don't balance fences inside them
        if '<details>' in line:
            in_details = True
            continue
        elif '</details>' in line:
            in_details = False
            continue
        
        # Skip fence processing inside <details> blocks
        if in_details:
            continue
        
        match = re.match(fence_pattern, stripped)
        
        if match:
            backticks = match.group(1)
            lang = match.group(2)
            backtick_count = len(backticks)
            
            # If there's an opening fence on the stack with same backtick count, this closes it
            if lang:  # Opening fence (has language identifier)
                fence_stack.append({'count': backtick_count, 'line': i, 'backticks': backticks, 'lang': lang})
            elif fence_stack:  # Closing fence (no language)
                if fence_stack[-1]['count'] == backtick_count:
                    # Proper match - close it
                    fence_stack.pop()
                else:
                    # Wrong backtick count - fix it to match the opening
                    expected_count = fence_stack[-1]['count']
                    expected_backticks = '`' * expected_count
                    lines[i] = expected_backticks
                    fence_stack.pop()
            else:  # Closing fence without opening - escape it
                lines[i] = line.replace(backticks, '\\' + backticks, 1)
        elif fence_stack and re.match(r'^`+$', stripped):
            # Line is only backticks (any count) and we have an open fence - this is a closing fence
            backtick_count = len(stripped)
            expected_count = fence_stack[-1]['count']
            expected_backticks = '`' * expected_count
            lines[i] = expected_backticks
            fence_stack.pop()
    
    # Fix any unmatched opening fences
    for fence in fence_stack:
        # If it's a 4+ backtick fence, convert it to 3 backticks
        if fence['count'] >= 4:
            lines[fence['line']] = lines[fence['line']].replace(fence['backticks'], '```', 1)
            # Add a closing fence after finding where it should end (heuristic: before next section marker or end)
            # Search for likely end markers like "---", blank line followed by header, or end of text
            for j in range(fence['line'] + 1, len(lines)):
                stripped = lines[j].strip()
                # Look for section breaks
                if (stripped == '---' or 
                    (j < len(lines) - 1 and lines[j] == '' and lines[j+1].strip().startswith('#')) or
                    stripped.startswith('<a name=')):
                    # Insert closing fence before this line
                    lines.insert(j, '```')
                    break
            else:
                # If no clear end found, add at the end
                lines.append('```')
        else:
            # For 3-backtick fences, just escape them
            lines[fence['line']] = lines[fence['line']].replace(fence['backticks'], '\\' + fence['backticks'], 1)
    
    return '\n'.join(lines)


def format_message_text(text: str) -> str:
    """Format message text with proper markdown."""
    if not text:
        return ""
    
    # Clean up literal \n\n escape sequences that appear in some JSON exports
    # These show up as the literal string "\n\n" instead of actual newlines
    text = re.sub(r'\\n\\n', '\n\n', text)
    
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
    
    # Balance code fences to prevent rendering issues
    text = balance_code_fences(text)
    
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
    
    # Remove empty code blocks (``` followed immediately by ```)
    text_result = '\n'.join(result_lines)
    # Remove empty code blocks with optional language specifier (``` followed immediately by ```)
    # Use line-anchored pattern to avoid matching partial fences like "```\n````"
    # which would incorrectly consume backticks from adjacent fences
    text_result = re.sub(r'^```[a-z]*\s*\n```\s*$', '', text_result, flags=re.MULTILINE)
    
    return text_result
