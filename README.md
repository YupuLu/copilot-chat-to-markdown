# Copilot Chat to Markdown

Convert GitHub Copilot chat logs from VS Code into readable Markdown format. This tool parses the chat JSON export from VS Code and generates clean Markdown files showing the conversation history with proper formatting and navigation.

## Quick Start

### 1. Export Chat from VS Code
1. Open Command Palette (`Cmd+Shift+P` or `Ctrl+Shift+P`)
2. Type "Chat: Export Chat" and select it
3. Save the JSON file

### 2. Convert to Markdown
```bash
# Single file
python3 chat_to_markdown.py chat.json -o output.md

# Multiple files (combined with unified TOC)
python3 chat_to_markdown.py file1.json file2.json -o combined.md --combine

# Entire folder
python3 chat_to_markdown.py ./chat_logs/ -o output.md --combine

# Separate files for each input
python3 chat_to_markdown.py ./chat_logs/ -o ./output/ --separate
```

### 3. Make Collapsible (Optional)
For long conversations with many requests:
```bash
chmod +x make_collapsible.sh
./make_collapsible.sh output.md
```

This wraps each request section in collapsible HTML `<details>` tags, making it easier to navigate long conversations.

## Features

### Core Conversion Features
- ✅ **Clean output**: Filters out internal VS Code metadata while preserving conversation flow
- ✅ **Preserves markdown formatting**: Bold text, code blocks, lists, and headers render correctly
- ✅ **Multiple requests**: Handles complete chat sessions with multiple back-and-forth exchanges
- ✅ **Inline code preservation**: Properly renders backticked file names and code snippets

### Navigation & Organization
- ✅ **Table of Contents**: Auto-generated index with clickable links to each request
- ✅ **Navigation links**: Each request includes ^ (index), < (previous), > (next) navigation
- ✅ **Status indicators**: Shows CANCELED or ERROR status for incomplete requests

### Batch Processing
- ✅ **Multi-file support**: Process multiple JSON files at once
- ✅ **Folder processing**: Automatically discover and process all JSON files in a directory
- ✅ **Combined mode**: Merge multiple chat logs into one document with:
  - **Chronological ordering**: Files automatically sorted by first chat timestamp
  - **Chat-level grouping**: Requests labeled as "Chat N - Request M" for clarity
  - **Unified TOC**: Single table of contents organized by chat sessions with clickable links
  - **Continuous numbering**: Global request numbering across all chats
- ✅ **Separate mode**: Generate individual markdown files for each input
- ✅ **Collapsible sections**: Optional HTML details/summary tags for easier navigation in long documents

### Contextual Information
- ✅ **Shows references**: Displays attached files and settings in expandable sections
- ✅ **Tool invocation details**: Shows detailed tool operations with input/output in collapsible blocks
- ✅ **Progress indicators**: Includes progress messages like "✔️ Optimizing tool selection..."
- ✅ **Timestamps**: Displays when each request was made

### Metadata & Analytics
- ✅ **Response timing**: Includes response time information for performance insights
- ✅ **Model information**: Shows which Copilot model was used for each response

## Prerequisites

- Python 3.6+
- No additional dependencies (uses only standard library)
- Bash shell (for `make_collapsible.sh` script)

## Project Structure

The codebase is organized into a modular package for maintainability:

```
copilot-chat-to-markdown/
├── chat_to_markdown.py      # Main CLI entry point (simplified)
├── chat_converter/          # Core conversion package
│   ├── __init__.py          # Package exports
│   ├── text_processing.py   # Text extraction and formatting
│   ├── formatters.py        # Basic formatters (timestamp, errors, references)
│   ├── tool_formatters.py   # Tool invocation and edit group formatters
│   └── parser.py            # Chat log parsing and markdown generation
├── make_collapsible.sh      # Script to add collapsible sections
├── demos/                   # Example files and demo scripts
├── data/                    # Sample JSON files for testing
└── backup/                  # Backup of original monolithic script
```

### Module Overview

| Module | Purpose |
|--------|---------|
| `text_processing.py` | Extract text from response parts, balance code fences, format messages |
| `formatters.py` | Format timestamps, error messages, and file references |
| `tool_formatters.py` | Format tool invocations, file edits, and progress tasks |
| `parser.py` | Parse chat logs and generate markdown with TOC and navigation |

## Usage Examples

### Basic Conversion
```bash
# Single file
python3 chat_to_markdown.py chat.json -o output.md
```

### Combining Multiple Files
Merge multiple chat logs into one document with unified TOC and continuous numbering:
```bash
# Multiple specific files
python3 chat_to_markdown.py chat1.json chat2.json chat3.json -o combined.md --combine

# Entire folder
python3 chat_to_markdown.py ./chat_logs/ -o combined_all.md --combine
```

**Combined mode features:**
- **Chronological ordering**: Files sorted by first chat timestamp (earliest first)
- **Chat-level structure**: Each file becomes "Chat N" with its own section
- **Smart labeling**: Requests shown as "Chat N - Request M" for better context
- **Unified Table of Contents**: Organized by chat sessions with clickable chat headers
- **Continuous global numbering**: Requests numbered sequentially across all chats
- **Easy navigation**: Links to jump between chats and return to TOC

### Separate File Processing
Process each JSON file independently:
```bash
python3 chat_to_markdown.py ./chat_logs/ -o ./markdown_output/ --separate
```

### Adding Collapsibility
Make sections collapsible for easier navigation in long documents:
```bash
./make_collapsible.sh output.md
```

**What it does:**
- Wraps each request in `<details open>` tags
- Creates clickable section headers
- Creates a `.backup` file before modifying
- Sections remain expanded by default but can be collapsed
- Works in GitHub, VS Code, and most markdown viewers

## Known Issues & Fixes

All major issues have been resolved:

✅ **Backtick/Inline Code Rendering** - File names and class names in backticks now display correctly  
✅ **Text Flow** - Text no longer splits across unnecessary lines  
✅ **Request Numbering** - Continuous numbering across combined files (no restarts)  
✅ **Empty Code Blocks** - Automatically removed from output  
✅ **Paragraph Spacing** - Proper spacing between sections and after collapsible blocks  
✅ **Nested Code Blocks** - Fixed rendering issues when tool invocations contain files with code blocks  
✅ **Jupyter Notebooks** - Notebook content properly wrapped in collapsible sections  
✅ **Tool Result Formatting** - Simplified "Read file" results to avoid markdown nesting conflicts  

## Demo & Sample Files

The `demos/` directory contains:

- **`chat.json`**: Example chat export from VS Code
- **`chat.md`**: Example output showing proper formatting
- **`demo_usage.sh`**: Executable script demonstrating all usage modes

Run the demo script to see the tool in action:
```bash
cd demos
./demo_usage.sh
```

See `data/` folder for additional examples of combined multi-file output.

## Output Format

The generated Markdown includes:

```markdown
# GitHub Copilot Chat Log

**Participant:** username
**Assistant:** GitHub Copilot

<a name="table-of-contents"></a>
## Table of Contents

- [Request 1](#request-1): Brief summary of user request...
- [Request 2](#request-2): Another request summary...
- [Request 3](#request-3): Third request summary...

---

<a name="request-1"></a>
## Request 1 [^](#table-of-contents) < [>](#request-2)

### User

[User's question or request]

### Assistant

<details>
  <summary>Used 2 references</summary>
  <p>☰ copilot-instructions.md<br>⚙️ github.copilot.chat.codeGeneration.instructions</p>
</details>

[AI response with proper **bold formatting** and code blocks]

<details>
  <summary>Ran Get file contents</summary>
  <p>Completed with input: {
  "filePath": "/path/to/file.md",
  "startLine": 1,
  "endLine": 50
}</p>
</details>

✔️ Optimizing tool selection...

[Continued AI response...]

*Response time: 45.32 seconds*

---

<a name="request-2"></a>
## Request 2 [^](#table-of-contents) [<](#request-1) [>](#request-3)

[Next exchange...]
```

## Troubleshooting

### Common Issues

1. **"No valid JSON files found"**
   - Ensure files have `.json` extension
   - Check file paths are correct
   - Verify JSON is valid: `python3 -c "import json; json.load(open('chat.json'))"`

2. **"Permission denied" for make_collapsible.sh**
   ```bash
   chmod +x make_collapsible.sh
   ```

3. **Empty output**
   - Check if the input JSON has the expected VS Code chat structure
   - Try with sample files first to verify setup

4. **Python errors**
   ```bash
   python3 chat_to_markdown.py chat.json -o output.md 2>&1
   ```

## Command Reference

| Task | Command |
|------|---------|
| Single file | `python3 chat_to_markdown.py input.json -o output.md` |
| Multiple files (combined) | `python3 chat_to_markdown.py *.json -o out.md --combine` |
| Folder (combined) | `python3 chat_to_markdown.py ./folder/ -o out.md --combine` |
| Folder (separate) | `python3 chat_to_markdown.py ./folder/ -o ./out/ --separate` |
| Add collapsibility | `./make_collapsible.sh output.md` |

## Contributing

Feel free to submit issues or pull requests to improve the scripts or add new features.

When filing an issue or creating a pull request, please include:
- A sample `chat.json` file that demonstrates the problem or use case
  - Redact any secrets or other private information before submitting
- The expected vs. actual output behavior
- Steps to reproduce the issue

This helps with debugging and ensures fixes work correctly across different chat formats.

## License

This project is licensed under the MIT License, which allows free use, modification, and distribution - see the [LICENSE](LICENSE) file for details.