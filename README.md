# Gitingest MCP server

An MCP server for gitingest that provides access to Git repository analysis through the Model Context Protocol (MCP). This server leverages the gitingest library to analyze Git repositories and make their content available in a format optimized for LLMs.

## Overview

This MCP server provides a single unified tool for accessing Git repository data. It automatically handles repository ingestion as needed, so users can immediately query repository content without an explicit ingestion step.

## Tool: `gitingest`

The server provides a single tool called `gitingest` that can be used to analyze Git repositories. The tool accepts the following parameters:

- `repo_uri` (required): URL or local path to the Git repository
- `resource_type`: Type of data to retrieve (`summary`, `tree`, `content`, or `all`). Default is `summary`.
- `max_file_size`: Maximum file size in bytes to include in the analysis. Default is 10MB.
- `include_patterns`: Comma-separated patterns of files to include in the analysis.
- `exclude_patterns`: Comma-separated patterns of files to exclude from the analysis.
- `branch`: Specific branch to analyze.
- `output`: File path to save the output to.

### Resource Types and Large Repositories

For large repositories, it's recommended to first request only the `summary` (which is the default). After ingestion, you can access more detailed information through the resources:

- Use the `tree` resource to explore the repository structure
- Use the `content` resource to access the full content (if not too large)

If the repository is too large, consider using `include_patterns` and/or `exclude_patterns` to limit the scope of the ingestion.

### Automatic Ingestion and Simple Caching

The server will automatically ingest repositories on demand. You don't need to call a separate ingestion function before querying.

Results are cached in memory during the server's runtime, so subsequent requests for the same repository will be faster. However, the cache is cleared when the server restarts.

Once a repository is ingested, you can access its data either by calling the `gitingest` tool again or by using the resources interface.

## New: Context Truncation with max_tokens

The gitingest MCP tool now supports an optional `max_tokens` argument. If provided, the response will be truncated to at most `max_tokens` tokens (1 token = 4 characters). This helps LLMs manage context size more effectively.

**Example usage:**
```json
{
  "repo_uri": "https://github.com/cyclotruc/gitingest",
  "resource_type": "content",
  "max_tokens": 2048
}
```

## MCP Server Configuration

To use this MCP server, add the following to your MCP config:
```json
"mcpServers": {
  "trelis-gitingest-mcp": {
    "command": "uvx",
    "args": [
      "trelis-gitingest-mcp"
    ]
  }
}
```

or to run from the github repo (less concise):

```json
"mcpServers": {
  "trelis-gitingest-mcp": {
    "command": "uvx",
    "args": [
      "git+https://github.com/TrelisResearch/trelis-gitingest-mcp"
    ]
  }
}
```

- The short config above works as long as the entry point and server name are both `trelis-gitingest-mcp` (see `pyproject.toml` and `src/gitingest_mcp/server.py`).
- If you rename the repo or entry point, you may need to use the more verbose config with `--from` and `--stdio`.

## Dependency Update

This MCP server now uses the official [`cyclotruc/gitingest`](https://github.com/cyclotruc/gitingest) repository for ingestion, ensuring you get the latest features and fixes.

## Quickstart
>[!TIP]
> The PyPI package `trelis-gitingest-mcp` does not yet support nested directories because that is supported by a branch that has not yet been merged in the gitingest library (and PyPI won't allow me to upload a package with a dependency on a branch). For this reason, using the github link to TrelisResearch/trelis-gitingest-mcp is recommended for now.

### Install

#### Claude Desktop

On MacOS: `~/Library/Application\ Support/Claude/claude_desktop_config.json`
On Windows: `%APPDATA%/Claude/claude_desktop_config.json`

Published Servers Configuration
> WARNING: Windsurf does not support passing in a github url. Use `trelis-gitingest-mcp` instead.
```json
"mcpServers": {
  "trelis-gitingest-mcp": {
    "command": "uvx",
    "args": [
      "git+https://github.com/TrelisResearch/trelis-gitingest-mcp"
    ]
  }
}
```

Development/Unpublished Servers Configuration
```json
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

## Examples & MCP Inspector

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


You can launch the MCP Inspector via [`npm`](https://docs.npmjs.com/downloading-and-installing-node-js-and-npm) with this command:

```bash
npx @modelcontextprotocol/inspector uv --directory /Users/your-username/trelis-gitingest-mcp run trelis-gitingest-mcp
```

or using uvx for the mcp server:
```bash
npx @modelcontextprotocol/inspector uvx https://github.com/TrelisResearch/trelis-gitingest-mcp.git
```

Upon launching, the Inspector will display a URL that you can access in your browser to begin debugging.
