# trelis-gitingest-mcp MCP server

An MCP server for gitingest that provides access to Git repository analysis through the Model Context Protocol (MCP). This server leverages the gitingest library to analyze Git repositories and make their content available in a format optimized for LLMs.

## Overview

This MCP server provides a single unified tool for accessing Git repository data. It automatically handles repository ingestion as needed, so users can immediately query repository content without an explicit ingestion step.

## Tool: `gitingest`

The server implements a single unified tool that handles all gitingest functionality:

### Parameters

- `repo_uri`: URL or local path to the Git repository (required)
- `resource_type`: Type of data to retrieve (optional, default: "all")
  - `"summary"`: Repository summary
  - `"tree"`: File tree structure
  - `"content"`: Repository content
  - `"all"`: All of the above
- `max_file_size`: Maximum file size in bytes (optional, default: 10MB)
- `include_patterns`: Comma-separated patterns of files to include (optional). **Note**: These patterns only match files immediately in the specified paths, not nested files.
- `exclude_patterns`: Comma-separated patterns of files to exclude (optional). **Note**: These patterns only match files immediately in the specified paths, not nested files.
- `branch`: Specific branch to analyze (optional)
- `output`: File path to save the output to (optional)

### Automatic Ingestion and Simple Caching

The server will automatically ingest repositories on demand. You don't need to call a separate ingestion function before querying.

Results are cached in memory during the server's runtime, so subsequent requests for the same repository will be faster. However, the cache is cleared when the server restarts.

Once a repository is ingested, you can access its data either by calling the `gitingest` tool again or by using the resources interface.

### Examples

**Get everything for a repository:**
```json
{
  "repo_uri": "https://github.com/user/repo"
}
```

**Get just the summary:**
```json
{
  "repo_uri": "https://github.com/user/repo",
  "resource_type": "summary"
}
```

**Get the file tree:**
```json
{
  "repo_uri": "https://github.com/user/repo",
  "resource_type": "tree"
}
```

**Get the full content:**
```json
{
  "repo_uri": "https://github.com/user/repo",
  "resource_type": "content"
}
```

**Custom ingestion parameters:**
```json
{
  "repo_uri": "https://github.com/user/repo",
  "branch": "dev",
  "exclude_patterns": "*.md,tests/*",
  "max_file_size": 5242880
}
```

**Using include patterns to focus on specific files:**
```json
{
  "repo_uri": "https://github.com/user/repo",
  "include_patterns": "src/*.py,bin/*"
}
```

**Note:** The patterns `src/*.py` and `bin/*` will only match Python files directly in the `src` directory and any files directly in the `bin` directory, not in subdirectories.

**Save output to a file:**
```json
{
  "repo_uri": "https://github.com/user/repo",
  "resource_type": "all",
  "output": "/path/to/output/file.txt"
}
```

## Configuration

## Quickstart

### Install

#### Claude Desktop

On MacOS: `~/Library/Application\ Support/Claude/claude_desktop_config.json`
On Windows: `%APPDATA%/Claude/claude_desktop_config.json`

<details>
  <summary>Development/Unpublished Servers Configuration</summary>
  ```
  "mcpServers": {
    "trelis-gitingest-mcp": {
      "command": "uv",
      "args": [
        "--directory",
        "/Users/your-username/trelis-gitingest-mcp",
        "run",
        "trelis-gitingest-mcp"
      ]
    }
  }
  ```
</details>

<details>
  <summary>Published Servers Configuration</summary>
  ```
  "mcpServers": {
    "trelis-gitingest-mcp": {
      "command": "uvx",
      "args": [
        "trelis-gitingest-mcp"
      ]
    }
  }
  ```
</details>

## Development

### Building and Publishing

To prepare the package for distribution:

1. Sync dependencies and update lockfile:
```bash
uv sync
```

2. Build package distributions:
```bash
uv build
```

This will create source and wheel distributions in the `dist/` directory.

3. Publish to PyPI:
```bash
uv publish
```

Note: You'll need to set PyPI credentials via environment variables or command flags:
- Token: `--token` or `UV_PUBLISH_TOKEN`
- Or username/password: `--username`/`UV_PUBLISH_USERNAME` and `--password`/`UV_PUBLISH_PASSWORD`

### Debugging

Since MCP servers run over stdio, debugging can be challenging. For the best debugging
experience, we strongly recommend using the [MCP Inspector](https://github.com/modelcontextprotocol/inspector).


You can launch the MCP Inspector via [`npm`](https://docs.npmjs.com/downloading-and-installing-node-js-and-npm) with this command:

```bash
npx @modelcontextprotocol/inspector uv --directory /Users/your-username/trelis-gitingest-mcp run trelis-gitingest-mcp
```


Upon launching, the Inspector will display a URL that you can access in your browser to begin debugging.