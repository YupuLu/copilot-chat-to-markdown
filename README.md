# Copilot Chat to Markdown

Convert GitHub Copilot chat logs from VS Code into readable Markdown format. This repository provides two implementations (Python and Bash) that parse the chat JSON export from VS Code and generate clean Markdown files showing the conversation history.

## Features

- ✅ **Preserves markdown formatting**: Bold text, code blocks, lists, and headers render correctly
- ✅ **Shows tool operations**: Displays AI tool selection and file operations for context
- ✅ **Clean output**: Filters out internal VS Code metadata while preserving conversation flow
- ✅ **Two implementations**: Choose between Python (more robust) or Bash (lightweight)
- ✅ **Response timing**: Includes response time information for performance insights
- ✅ **Multiple requests**: Handles complete chat sessions with multiple back-and-forth exchanges
- ✅ **Table of Contents**: Auto-generated index with clickable links to each request
- ✅ **Navigation links**: Each request includes ^ (back to index), < (previous request), > (next request) navigation
- ✅ **Consolidated responses**: Extracts final AI responses rather than incremental updates

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
  - **Windows**: `choco install jq` (requires [Chocolatey](https://chocolatey.org/), a Windows package manager)

## Usage

### 1. Export Chat from VS Code

First, you need to export your chat history from VS Code:

1. Open the Command Palette (`Cmd+Shift+P` on macOS or `Ctrl+Shift+P` on Windows/Linux)
2. Type "Chat: Export Chat" and select it
3. Choose where to save your chat export JSON file
4. The file will contain your complete chat history in JSON format

### 2. Convert to Markdown

#### Using Python Script (Recommended)

```bash
python3 chat_to_markdown.py input.json output.md
```

#### Using Bash Script

```bash
./chat_to_markdown.sh input.json output.md
```

### 3. View Results

Open the generated Markdown file in any Markdown viewer or editor to see your formatted chat history.

## Sample Files

The `samples/` directory contains example files:

- **`chat.json`**: Original chat export from VS Code (404KB conversation about a repo organizer project)
- **`chat_via_script_python.md`**: Output from Python script with table of contents and navigation
- **`chat_via_script_bash.md`**: Output from Bash script with identical features and formatting

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

Optimizing tool selection...
Reading [](file:///path/to/file.md)
[AI response with proper **bold formatting** and code blocks]

*Response time: 45.32 seconds*

---

<a name="request-2"></a>
## Request 2 [^](#table-of-contents) [<](#request-1) [>](#request-3)

[Next exchange...]
```

## Troubleshooting

### Bash Script Issues

If you encounter jq errors:
```bash
# Install jq if missing
brew install jq  # macOS
sudo apt-get install jq  # Ubuntu/Debian
sudo yum install jq  # RHEL/CentOS
choco install jq  # Windows (requires Chocolatey)

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

This project is licensed under the MIT License, which allows free use, modification, and distribution - see the [LICENSE](LICENSE) file for details.