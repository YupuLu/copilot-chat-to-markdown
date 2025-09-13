# Copilot Chat to Markdown

Convert GitHub Copilot chat logs from VS Code into readable Markdown format. This tool parses the chat JSON export from VS Code and generates clean Markdown files showing the conversation history with proper formatting and navigation.

## Features

- ✅ **Preserves markdown formatting**: Bold text, code blocks, lists, and headers render correctly
- ✅ **Shows references**: Displays attached files and settings in expandable sections
- ✅ **Tool invocation details**: Shows detailed tool operations with input/output in collapsible blocks
- ✅ **Progress indicators**: Includes progress messages like "✔️ Optimizing tool selection..."
- ✅ **Clean output**: Filters out internal VS Code metadata while preserving conversation flow
- ✅ **Response timing**: Includes response time information for performance insights
- ✅ **Multiple requests**: Handles complete chat sessions with multiple back-and-forth exchanges
- ✅ **Table of Contents**: Auto-generated index with clickable links to each request
- ✅ **Navigation links**: Each request includes ^ (index), < (previous), > (next) navigation

## Prerequisites

- Python 3.6+
- No additional dependencies (uses only standard library)

## Usage

### 1. Export Chat from VS Code

First, you need to export your chat history from VS Code:

1. Open the Command Palette (`Cmd+Shift+P` on macOS or `Ctrl+Shift+P` on Windows/Linux)
2. Type "Chat: Export Chat" and select it
3. Choose where to save your chat export JSON file
4. The file will contain your complete chat history in JSON format

### 2. Convert to Markdown

```bash
python3 chat_to_markdown.py chat.json chat.md
```

### 3. View Results

Open the generated Markdown file in any Markdown viewer or editor to see your formatted chat history.

## Sample Files

The `samples/` directory contains example files:

- **`chat.json`**: Original chat export from VS Code (404KB conversation about a repo organizer project)
- **`chat.md`**: Output from the conversion script with proper formatting, references, and navigation

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

1. **Invalid JSON**: Ensure the exported chat file is valid JSON
   ```bash
   python3 -c "import json; json.load(open('chat.json'))"
   ```

2. **Python errors**: Run with error output for debugging
   ```bash
   python3 chat_to_markdown.py chat.json chat.md 2>&1
   ```

3. **Empty output**: Check if the input JSON has the expected VS Code chat structure
4. **File not found**: Verify file paths are correct and files exist

## Contributing

Feel free to submit issues or pull requests to improve the scripts or add new features.

## License

This project is licensed under the MIT License, which allows free use, modification, and distribution - see the [LICENSE](LICENSE) file for details.