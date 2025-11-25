"""
Basic formatters for chat log conversion.

Contains functions for formatting timestamps, errors, and references.
"""

from datetime import datetime
from typing import Dict, List, Any


def format_timestamp(timestamp_ms: int) -> str:
    """Format timestamp from milliseconds to readable format."""
    try:
        timestamp_s = timestamp_ms / 1000
        dt = datetime.fromtimestamp(timestamp_s)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return "Unknown time"


def format_error_message(error_details: Dict[str, Any]) -> str:
    """Format error details into a markdown error box."""
    if not error_details or not isinstance(error_details, dict):
        return ""
    
    message = error_details.get('message', '')
    if not message:
        return ""
    
    # Clean up the error message - remove excessive whitespace
    message = message.strip()
    
    # Create a markdown error box with special styling
    lines = []
    
    # Split the error message into parts for better formatting
    lines_in_message = message.split('\n')
    for i, line in enumerate(lines_in_message):
        line = line.strip()
        if line:
            # Prefix first line with 🚫 emoji
            if i == 0:
                lines.append(f"> 🚫 {line}")
            else:
                lines.append(f"> {line}")
    
    lines.append("")
    return '\n'.join(lines)


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
