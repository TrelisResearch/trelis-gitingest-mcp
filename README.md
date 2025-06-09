# gitingest-mcp MCP server

An MCP server for gitingest that provides access to Git repository analysis through the Model Context Protocol (MCP). This server leverages the gitingest library to analyze Git repositories and make their content available in a format optimized for LLMs.

## Components

### Resources

The server provides access to ingested Git repositories through resources:
- Custom gitingest:// URI scheme for accessing repository data
- Each repository has three resources available:
  - `gitingest://{uri}/summary`: Repository summary
  - `gitingest://{uri}/tree`: File tree structure
  - `gitingest://{uri}/content`: Full repository content formatted for LLMs
- All resources have text/plain mimetype

### Prompts

The server provides a single prompt:
- `summarize-repo`: Creates a summary of an ingested repository
  - Required `repo_uri` argument specifying which repository to summarize
  - Optional `detail_level` argument to control detail level (brief/detailed)
  - Generates a prompt combining repository summary, file tree, and optionally content

### Tools

The server implements two tools:

#### 1. `ingest-repo`
Analyzes a Git repository using gitingest with flexible options:
- `repo_uri`: URL or local path to the Git repository (required)
- `output_file`: Optional path to save the digest output
- `max_file_size`: Maximum file size in bytes (default: 10MB)
- `include_patterns`: Comma-separated patterns of files to include
- `exclude_patterns`: Comma-separated patterns of files to exclude
- `branch`: Specific branch to analyze (default: main/master)

#### 2. `query-repo`
Query specific parts of an ingested repository:
- `repo_uri`: URL or local path of the ingested repository (required)
- `resource_type`: Type of resource to query (required, one of: "summary", "tree", "content")
- `file_path`: Optional specific file path to query (for content resource type)
- `search_term`: Optional search term to find in content

## Configuration

[TODO: Add configuration details specific to your implementation]

## Quickstart

### Install

#### Claude Desktop

On MacOS: `~/Library/Application\ Support/Claude/claude_desktop_config.json`
On Windows: `%APPDATA%/Claude/claude_desktop_config.json`

<details>
  <summary>Development/Unpublished Servers Configuration</summary>
  ```
  "mcpServers": {
    "gitingest-mcp": {
      "command": "uv",
      "args": [
        "--directory",
        "/Users/ronanmcgovern/TR/gitingest-mcp",
        "run",
        "gitingest-mcp"
      ]
    }
  }
  ```
</details>

<details>
  <summary>Published Servers Configuration</summary>
  ```
  "mcpServers": {
    "gitingest-mcp": {
      "command": "uvx",
      "args": [
        "gitingest-mcp"
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
npx @modelcontextprotocol/inspector uv --directory /Users/ronanmcgovern/TR/gitingest-mcp run gitingest-mcp
```


Upon launching, the Inspector will display a URL that you can access in your browser to begin debugging.