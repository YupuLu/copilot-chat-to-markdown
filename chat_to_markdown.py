#!/usr/bin/env python3
"""
Convert a Copilot chat log JSON file to markdown format.

Usage: python chat_to_markdown.py input.json output.md

This is the main entry point. The actual conversion logic is in the
chat_converter package for better maintainability.
"""

import json
import sys
import os
import argparse

# Import all functions from the modular package
from chat_converter import (
    parse_chat_log,
    process_single_file,
    parse_combined_chat_logs,
)


def main():
    parser = argparse.ArgumentParser(
        description="Convert Copilot chat log JSON file(s) to markdown format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Single file:
    python chat_to_markdown.py input.json output.md
  
  Multiple files (combined):
    python chat_to_markdown.py file1.json file2.json file3.json -o output.md --combine
  
  Folder (combined):
    python chat_to_markdown.py /path/to/folder -o output.md --combine
  
  Folder (individual files):
    python chat_to_markdown.py /path/to/folder -o /output/dir/ --separate
        """
    )
    parser.add_argument('input', nargs='+', help='Input JSON file(s) or folder path')
    parser.add_argument('-o', '--output', required=True, help='Output markdown file or directory')
    parser.add_argument('--combine', action='store_true', help='Combine multiple inputs into one file')
    parser.add_argument('--separate', action='store_true', help='Output separate markdown files (for folder input)')
    
    args = parser.parse_args()
    
    # Collect all input files
    input_files = []
    for input_path in args.input:
        if os.path.isdir(input_path):
            # Add all JSON files from directory
            json_files = sorted([
                os.path.join(input_path, f) 
                for f in os.listdir(input_path) 
                if f.endswith('.json')
            ])
            input_files.extend(json_files)
        elif os.path.isfile(input_path) and input_path.endswith('.json'):
            input_files.append(input_path)
        else:
            print(f"Warning: Skipping {input_path} (not a JSON file or directory)")
    
    if not input_files:
        print("Error: No valid JSON files found")
        return
    
    try:
        # Handle different output modes
        if args.separate:
            # Separate mode - create individual markdown files
            output_dir = args.output
            if not os.path.isdir(output_dir):
                os.makedirs(output_dir, exist_ok=True)
            
            for input_file in input_files:
                file_name = os.path.splitext(os.path.basename(input_file))[0]
                output_file = os.path.join(output_dir, f"{file_name}.md")
                markdown_content = process_single_file(input_file)
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(markdown_content)
                print(f"Converted {input_file} to {output_file}")
            
            print(f"Successfully converted {len(input_files)} files to {output_dir}")
        
        elif len(input_files) == 1 and not args.combine:
            # Single file mode
            markdown_content = process_single_file(input_files[0])
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            print(f"Successfully converted {input_files[0]} to {args.output}")
        
        else:
            # Combined mode - merge all files with unified TOC and continuous numbering
            combined_content = parse_combined_chat_logs(input_files)
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(combined_content)
            print(f"Successfully combined {len(input_files)} files into {args.output}")
        
    except FileNotFoundError as e:
        print(f"Error: Could not find file: {e}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
