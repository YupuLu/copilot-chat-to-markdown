# Copilot Chat to Markdown

Convert GitHub Copilot chat logs from VS Code into readable Markdown format. This repository provides two implementations (Python and Bash) that parse the chat JSON export from VS Code and generate clean Markdown files showing the conversation history.

## Features

- ✅ **Preserves markdown formatting**: Bold text, code blocks, lists, and headers render correctly
- ✅ **Shows tool operations**: Displays AI tool selection and file operations for context
- ✅ **Clean output**: Filters out internal VS Code metadata while preserving conversation flow
- ✅ **Two implementations**: Choose between Python (more robust) or Bash (lightweight)
- ✅ **Response timing**: Includes response time information
- ✅ **Multiple requests**: Handles complete chat sessions with multiple back-and-forth exchanges

## Prerequisites

### For Python Script
- Python 3.6+
- No additional dependencies (uses only standard library)

### For Bash Script  
- Bash shell
- `jq` (JSON processor)
  - **macOS**: `brew install jq`
  - **Ubuntu/Debian**: `sudo apt-get install jq`
  - **RHEL/CentOS**: `sudo yum install jq`

## Usage

### 1. Export Chat from VS Code

First, you need to export your chat history from VS Code:

1. Open the GitHub Copilot Chat panel in VS Code
2. Find the three dots menu (⋯) or export button in the chat panel
3. Select "Export Chat" or "Copy Chat" 
4. If copying, paste the content into a JSON file (e.g., `chat.json`)

### 2. Convert to Markdown

#### Using Python Script (Recommended)

```bash
python3 chat_to_markdown.py input.json output.md
```

**Example:**
```bash
python3 chat_to_markdown.py samples/chat.json my_chat_session.md
```

#### Using Bash Script

```bash
./chat_to_markdown.sh input.json output.md
```

**Example:**
```bash
./chat_to_markdown.sh samples/chat.json my_chat_session.md
```

### 3. View Results

Open the generated Markdown file in any Markdown viewer or editor to see your formatted chat history.

## Sample Files

The `samples/` directory contains example files:

- **`chat.json`**: Original chat export from VS Code
- **`chat_via_manual_copy.md`**: Manually copied chat (for comparison)
- **`chat_via_script_python.md`**: Output from Python script
- **`chat_via_script_bash.md`**: Output from Bash script

## Output Format

The generated Markdown includes:

```markdown
# GitHub Copilot Chat Log

**Participant:** username
**Assistant:** GitHub Copilot

---

## Request 1

### User

[User's question or request]

### Assistant

Optimizing tool selection...
Reading [](file:///path/to/file.md)
[AI response with proper **bold formatting** and code blocks]

*Response time: 45.32 seconds*

---

## Request 2

[Next exchange...]
```

## Key Features Demonstrated

- **Tool Operations**: Shows when AI selects tools, reads files, or performs operations
- **Markdown Preservation**: Bold text (`**text**`), code blocks, and lists render correctly
- **Clean Formatting**: Removes VS Code internal metadata while preserving conversation context
- **Timing Information**: Includes response times for performance insights

## Troubleshooting

### Bash Script Issues

If you encounter jq errors:
```bash
# Install jq if missing
brew install jq  # macOS
sudo apt-get install jq  # Ubuntu/Debian

# Check if JSON is valid
jq empty your_chat.json
```

### Python Script Issues

```bash
# Test the script
python3 -c "import chat_to_markdown; print('Import successful')"

# Run with error output
python3 chat_to_markdown.py input.json output.md 2>&1
```

### Common Issues

1. **Invalid JSON**: Ensure the exported chat file is valid JSON
2. **File permissions**: Make sure the bash script is executable (`chmod +x chat_to_markdown.sh`)
3. **Empty output**: Check if the input JSON has the expected structure

## Contributing

Feel free to submit issues or pull requests to improve the scripts or add new features.

## License

This project is provided as-is for educational and personal use.