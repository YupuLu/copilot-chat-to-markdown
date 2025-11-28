"""
Parser functions for chat log conversion.

Contains functions for parsing chat logs and generating markdown output.
"""

import json
import os
from typing import Dict, List, Any

from .text_processing import (
    extract_text_from_response_part,
    smart_join_parts,
    format_message_text,
)
from .formatters import (
    format_timestamp,
    format_error_message,
    format_references,
)
from .tool_formatters import (
    process_special_markers,
    add_spacing_after_details,
)


def parse_chat_log(chat_data: Dict[str, Any]) -> str:
    """Parse the chat log JSON and convert to markdown."""
    md_lines = []
    
    # Header
    md_lines.append("# GitHub Copilot Chat Log")
    md_lines.append("")
    md_lines.append(f"**Participant:** {chat_data.get('requesterUsername', 'User')}")
    md_lines.append(f"<br>**Assistant:** {chat_data.get('responderUsername', 'GitHub Copilot')}")
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
    for i, request in enumerate(requests, 1):
        # User message with navigation links on same line
        nav_links = []
        nav_links.append("[^^^](#table-of-contents)")  # Up to table of contents
        
        if i > 1:  # Previous request link
            nav_links.append(f"[<<<](#request-{i-1})")
        else:
            nav_links.append("<<<")  # Placeholder for first request
            
        if i < len(requests):  # Next request link
            nav_links.append(f"[>>>](#request-{i+1})")
        else:
            nav_links.append(">>>")  # Placeholder for last request
        
        # Get result for status checking
        result = request.get('result', {})
        
        # Determine status
        status_text = ""
        if isinstance(result, dict):
            if result.get('errorDetails', {}).get('message'):
                if 'canceled' in result.get('errorDetails', {}).get('message', '').lower():
                    status_text = " *(CANCELED)*"
                else:
                    status_text = " *(ERROR)*"
        
        # Add explicit anchor and header with navigation
        md_lines.append(f'<a name="request-{i}"></a>')
        md_lines.append(f"## Request {i} {' '.join(nav_links)}")
        if status_text:
            md_lines.append(status_text)
        md_lines.append("")
        
        # Add timestamp if available
        timestamp = request.get('timestamp')
        if timestamp:
            timestamp_str = format_timestamp(timestamp)
            md_lines.append(f"**Timestamp:** {timestamp_str}")
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
            md_lines.append("**USER MESSAGE:**")
            md_lines.append(f"> {format_message_text(message_text).replace(chr(10), chr(10) + '> ')}")
            md_lines.append("")
        
        # Assistant response
        response = request.get('response', [])
        
        # Check for error details
        error_details = None
        if isinstance(result, dict):
            error_details = result.get('errorDetails', {})
        
        # Process assistant responses (can have both response content and errors)
        if response or (error_details and isinstance(error_details, dict) and error_details.get('message')):
            md_lines.append("**ASSISTANT RESPONSE:**")
            
            # Add references if they exist (might be present even with errors)
            variable_data = request.get('variableData', {})
            if isinstance(variable_data, dict):
                variables = variable_data.get('variables', [])
                if variables:
                    references_formatted = format_references(variables)
                    if references_formatted.strip():
                        md_lines.append(references_formatted)
            else:
                md_lines.append("")
            
            # Process normal response content first (if any)
            if response:
                # First try to get consolidated response from toolCallRounds
                consolidated_response = ""
                if isinstance(result, dict):
                    metadata = result.get('metadata', {})
                    if isinstance(metadata, dict):
                        tool_call_rounds = metadata.get('toolCallRounds', [])
                        if isinstance(tool_call_rounds, list):
                            tool_responses = []
                            
                            for round_data in tool_call_rounds:
                                if isinstance(round_data, dict):
                                    if 'response' in round_data:
                                        round_response = round_data['response']
                                        if isinstance(round_response, str) and round_response.strip():
                                            tool_responses.append(round_response.strip())
                            
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
                
                # Always process the incremental response parts for tool details
                response_parts = []
                for part in response:
                    part_text = extract_text_from_response_part(part)
                    if part_text and part_text.strip():
                        response_parts.append(part_text)
                
                # Extract tool call results for this request
                tool_call_results = {}
                tool_call_rounds = []
                if isinstance(result, dict):
                    metadata = result.get('metadata', {})
                    if isinstance(metadata, dict):
                        tool_call_results = metadata.get('toolCallResults', {})
                        tool_call_rounds = metadata.get('toolCallRounds', [])
                
                if response_parts:
                    # Join parts with smart spacing to preserve paragraph boundaries
                    incremental_response = smart_join_parts(response_parts)
                    # Process special markers for tool invocations with tool call results
                    incremental_response = process_special_markers(incremental_response, tool_call_results, tool_call_rounds)
                    
                    # Use the incremental response if it has more detail
                    joined_for_check = ''.join(response_parts)
                    if ('__TOOL_INVOCATION__' in joined_for_check or 
                        '__TEXT_EDIT_GROUP__' in joined_for_check or 
                        not consolidated_response.strip()):
                        consolidated_response = incremental_response
                
                # Use whichever response has more meaningful content
                if consolidated_response.strip():
                    cleaned_response = format_message_text(consolidated_response)
                    if cleaned_response.strip():
                        md_lines.append(cleaned_response)
                        md_lines.append("")
            
            # Add error message if request failed (after any response content)
            if error_details and isinstance(error_details, dict) and error_details.get('message'):
                error_message = format_error_message(error_details)
                if error_message.strip():
                    md_lines.append(error_message)
                    md_lines.append("")
        
        # Add timestamp and metadata if available
        metadata_lines = []
        
        # Add timing information
        if isinstance(result, dict):
            timings = result.get('timings', {})
            if 'totalElapsed' in timings:
                elapsed_ms = timings['totalElapsed']
                elapsed_s = elapsed_ms / 1000
                metadata_lines.append(f"> *Response time: {elapsed_s:.2f} seconds*")
        
        # Add model information
        model_id = request.get('modelId', '')
        details = request.get('details', '')
        
        if model_id or details:
            model_info_parts = []
            if model_id:
                if model_id.startswith('copilot/'):
                    model_display = model_id[8:]
                else:
                    model_display = model_id
                model_info_parts.append(model_display)
            
            if details and details != model_display:
                model_info_parts.append(details)
            
            if model_info_parts:
                model_info = ' • '.join(model_info_parts)
                metadata_lines.append(f"> <br>*Model: {model_info}*")
        
        # Add all metadata lines
        if metadata_lines:
            for line in metadata_lines:
                md_lines.append(line)
            md_lines.append("")
        
        # Add separator between requests
        if i < len(requests):
            md_lines.append("---")
            md_lines.append("")
    
    markdown_text = '\n'.join(md_lines)
    return add_spacing_after_details(markdown_text)


def process_single_file(input_file: str, file_title: str = None) -> str:
    """Process a single JSON file and return markdown content."""
    with open(input_file, 'r', encoding='utf-8') as f:
        chat_data = json.load(f)
    
    markdown_content = parse_chat_log(chat_data)
    
    # If a custom title is provided, add it as a header
    if file_title:
        markdown_content = f"# {file_title}\n\n{markdown_content}"
    
    return markdown_content


def parse_combined_chat_logs(file_paths: List[str]) -> str:
    """Parse multiple chat logs with continuous numbering and unified TOC, sorted by timestamp."""
    # Load all chat data first and get first timestamp for sorting
    chat_files = []
    for file_path in file_paths:
        with open(file_path, 'r', encoding='utf-8') as f:
            chat_data = json.load(f)
        
        file_name = os.path.splitext(os.path.basename(file_path))[0]
        requests = chat_data.get('requests', [])
        
        # Get first timestamp for sorting
        first_timestamp = None
        if requests and len(requests) > 0:
            first_timestamp = requests[0].get('timestamp', 0)
        
        chat_files.append({
            'file_path': file_path,
            'file_name': file_name,
            'chat_data': chat_data,
            'requests': requests,
            'first_timestamp': first_timestamp or 0,
            'requester': chat_data.get('requesterUsername', 'User'),
            'responder': chat_data.get('responderUsername', 'GitHub Copilot')
        })
    
    # Sort by first timestamp (chronological order)
    chat_files.sort(key=lambda x: x['first_timestamp'])
    
    # Now build the combined structure with sorted files
    all_requests = []
    file_boundaries = []
    
    for chat_file in chat_files:
        file_boundaries.append({
            'start_index': len(all_requests),
            'end_index': len(all_requests) + len(chat_file['requests']),
            'file_name': chat_file['file_name'],
            'requester': chat_file['requester'],
            'responder': chat_file['responder']
        })
        
        all_requests.extend(chat_file['requests'])
    
    # Build combined markdown
    md_lines = []
    
    # Header
    md_lines.append("# GitHub Copilot Chat Log (Combined)")
    md_lines.append("")
    md_lines.append(f"**Participant:** {file_boundaries[0]['requester']}")
    md_lines.append(f"<br>**Assistant:** {file_boundaries[0]['responder']}")
    md_lines.append("")
    
    # Generate unified table of contents
    if len(all_requests) > 1:
        md_lines.append('<a name="table-of-contents"></a>')
        md_lines.append("## Table of Contents")
        md_lines.append("")
        
        # Add file sections to TOC with chat numbering
        for chat_num, boundary in enumerate(file_boundaries, 1):
            # Escape square brackets in file names
            file_name_escaped = boundary['file_name'].replace('[', '\\[').replace(']', '\\]')
            md_lines.append(f"### Chat {chat_num}: {file_name_escaped}")
            md_lines.append("")
            for i in range(boundary['start_index'], boundary['end_index']):
                local_req_num = i - boundary['start_index'] + 1
                request = all_requests[i]
                
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
                
                if preview:
                    first_line = preview.split('\n')[0]
                    if len(first_line) > 80:
                        first_line = first_line[:77] + "..."
                else:
                    first_line = "[No message content]"
                
                md_lines.append(f"- [Request {local_req_num}](#chat-{chat_num}-request-{local_req_num}): {first_line}")
            md_lines.append("")
        
    md_lines.append("---")
    md_lines.append("")
    
    # Process all requests with continuous numbering
    for i, request in enumerate(all_requests):
        req_num = i + 1
        
        # Find which file/chat this request belongs to
        current_file = None
        current_chat_num = None
        local_req_num = None
        for chat_idx, boundary in enumerate(file_boundaries, 1):
            if boundary['start_index'] <= i < boundary['end_index']:
                current_file = boundary['file_name']
                current_chat_num = chat_idx
                local_req_num = i - boundary['start_index'] + 1
                # Add chat header if this is the first request from this chat
                if i == boundary['start_index']:
                    md_lines.append(f"## Chat {chat_idx}: {current_file}")
                    md_lines.append("")
                break
        
        # Get result for status checking
        result = request.get('result', {})
        
        # Determine status
        status_text = ""
        if isinstance(result, dict):
            if result.get('errorDetails', {}).get('message'):
                if 'canceled' in result.get('errorDetails', {}).get('message', '').lower():
                    status_text = " *(CANCELED)*"
                else:
                    status_text = " *(ERROR)*"
        
        # Navigation links
        nav_links = []
        nav_links.append("[^](#table-of-contents)")
        
        # Previous link
        if req_num > 1:
            prev_chat_num = None
            prev_local_num = None
            for chat_idx, boundary in enumerate(file_boundaries, 1):
                if boundary['start_index'] <= (i-1) < boundary['end_index']:
                    prev_chat_num = chat_idx
                    prev_local_num = (i-1) - boundary['start_index'] + 1
                    break
            if prev_chat_num and prev_local_num:
                nav_links.append(f"[<](#chat-{prev_chat_num}-request-{prev_local_num})")
        else:
            nav_links.append("<")
        
        # Next link
        if req_num < len(all_requests):
            next_chat_num = None
            next_local_num = None
            for chat_idx, boundary in enumerate(file_boundaries, 1):
                if boundary['start_index'] <= (i+1) < boundary['end_index']:
                    next_chat_num = chat_idx
                    next_local_num = (i+1) - boundary['start_index'] + 1
                    break
            if next_chat_num and next_local_num:
                nav_links.append(f"[>](#chat-{next_chat_num}-request-{next_local_num})")
        else:
            nav_links.append(">")
        
        # Add request header with chat context
        md_lines.append(f'<a name="chat-{current_chat_num}-request-{local_req_num}"></a>')
        md_lines.append(f"### Chat {current_chat_num}-Request {local_req_num} {' '.join(nav_links)}")
        if status_text:
            md_lines.append(status_text)
        md_lines.append("")
        
        # Add timestamp if available
        timestamp = request.get('timestamp')
        if timestamp:
            timestamp_str = format_timestamp(timestamp)
            md_lines.append(f"**Timestamp:** {timestamp_str}")
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
            md_lines.append("**USER MESSAGE:**")
            md_lines.append(f"> {format_message_text(message_text).replace(chr(10), chr(10) + '> ')}")
            md_lines.append("")
        
        # Assistant response
        response = request.get('response', [])
        
        # Check for error details
        error_details = None
        if isinstance(result, dict):
            error_details = result.get('errorDetails', {})
        
        # Process assistant responses
        if response or (error_details and isinstance(error_details, dict) and error_details.get('message')):
            md_lines.append("**ASSISTANT RESPONSE:**")
            
            # Add references if they exist
            variable_data = request.get('variableData', {})
            if isinstance(variable_data, dict):
                variables = variable_data.get('variables', [])
                if variables:
                    references_formatted = format_references(variables)
                    if references_formatted.strip():
                        md_lines.append(references_formatted)
            else:
                md_lines.append("")
            
            # Process normal response content
            if response:
                response_parts = []
                for part in response:
                    part_text = extract_text_from_response_part(part)
                    if part_text and part_text.strip():
                        response_parts.append(part_text)
                
                # Extract tool call results
                tool_call_results = {}
                tool_call_rounds = []
                if isinstance(result, dict):
                    metadata = result.get('metadata', {})
                    if isinstance(metadata, dict):
                        tool_call_results = metadata.get('toolCallResults', {})
                        tool_call_rounds = metadata.get('toolCallRounds', [])
                
                if response_parts:
                    incremental_response = smart_join_parts(response_parts)
                    incremental_response = process_special_markers(incremental_response, tool_call_results, tool_call_rounds)
                    cleaned_response = format_message_text(incremental_response)
                    if cleaned_response.strip():
                        md_lines.append(cleaned_response)
                        md_lines.append("")
            
            # Add error message if request failed
            if error_details and isinstance(error_details, dict) and error_details.get('message'):
                error_message = format_error_message(error_details)
                if error_message.strip():
                    md_lines.append(error_message)
                    md_lines.append("")
        
        # Add separator between requests
        if req_num < len(all_requests):
            md_lines.append("---")
            md_lines.append("")
    
    markdown_text = '\n'.join(md_lines)
    return add_spacing_after_details(markdown_text)
