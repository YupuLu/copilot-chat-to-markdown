"""
Chat Converter Package

Converts Copilot chat log JSON files to markdown format.
"""

from .text_processing import (
    extract_text_from_response_part,
    smart_join_parts,
    balance_code_fences,
    format_message_text,
    strip_details_blocks,
)

from .formatters import (
    format_timestamp,
    format_error_message,
    format_references,
)

from .tool_formatters import (
    extract_content_from_tool_result,
    format_tool_invocation_details,
    format_text_edit_group,
    format_progress_task,
    process_special_markers,
    format_tool_calls,
    add_spacing_after_details,
)

from .parser import (
    parse_chat_log,
    process_single_file,
    parse_combined_chat_logs,
)

__all__ = [
    # Text processing
    'extract_text_from_response_part',
    'smart_join_parts',
    'balance_code_fences',
    'format_message_text',
    'strip_details_blocks',
    # Basic formatters
    'format_timestamp',
    'format_error_message',
    'format_references',
    # Tool formatters
    'extract_content_from_tool_result',
    'format_tool_invocation_details',
    'format_text_edit_group',
    'format_progress_task',
    'process_special_markers',
    'format_tool_calls',
    'add_spacing_after_details',
    # Parsers
    'parse_chat_log',
    'process_single_file',
    'parse_combined_chat_logs',
]
