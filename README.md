# Gitingest MCP server

An MCP server for gitingest that provides access to Git repository analysis through the Model Context Protocol (MCP). This server leverages the gitingest library to analyze Git repositories and make their content available in a format optimized for LLMs.

>[!WARNING] Private repo support in gitingest is not yet on PyPI as of June 25th 2025. Once that is pushed, this MCP will automatically support it.

## Overview

This MCP server provides a single unified tool for accessing Git repository data. It automatically handles repository ingestion as needed, so users can immediately query repository content without an explicit ingestion step.

## Tool: `gitingest`

The server provides a single tool called `gitingest` that can be used to analyze Git repositories. The tool accepts the following parameters:

-   `repo_uri` (required): URL or local path to the Git repository
-   `resource_type`: Type of data to retrieve (`summary`, `tree`, `content`, or `all`). Default is `summary`.
-   `max_file_size`: Maximum file size in bytes to include in the analysis. Default is 10MB.
-   `include_patterns`: Comma-separated patterns of files to include in the analysis.
-   `exclude_patterns`: Comma-separated patterns of files to exclude from the analysis.
-   `branch`: Specific branch to analyze.
-   `output`: File path to save the output to.
-   `max_tokens`: Truncates the response to a specified number of tokens.

### Accessing Private Repositories

You can ingest private GitHub repositories by providing a GitHub Personal Access Token (PAT).

**Recommended:** Set an Environment Variable in your MCP Config

This is the best approach for persistent configuration. Add an `env` block to your server definition in your MCP configuration file. The `gitingest` library will automatically use the `GITHUB_TOKEN` environment variable.

```json
"mcpServers": {
  "trelis-gitingest-mcp": {
    "command": "uvx",
    "args": [
      "trelis-gitingest-mcp"
    ],
    "env": {
      "GITHUB_TOKEN": "github_pat_..."
    }
  }
}
```

### Resource Types and Large Repositories

For large repositories, it's recommended to first request only the `summary` (which is the default). After ingestion, you can access more detailed information through the resources:

-   Use the `tree` resource to explore the repository structure
-   Use the `content` resource to access the full content (if not too large)

If the repository is too large, consider using `include_patterns` and/or `exclude_patterns` to limit the scope of the ingestion.

### Accessing Resources After a Tool Call

After you call the `gitingest` tool for a repository, the server defines resources for that repository:
- **Summary**: A high-level summary of the repository
- **Tree**: The file/directory structure
- **Content**: The full content (subject to size limits)

These resources can be accessed individually via the resources interface in any MCP-compatible client. This is useful for browsing or fetching specific aspects of a repository after ingestion.

## MCP Server Configuration

To use this MCP server from PyPI, add the following to your MCP config:

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

To run directly from the GitHub repository:

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

## Development

### Building and Publishing

To prepare the package for distribution:

1.  Sync dependencies and update lockfile:
    ```bash
    uv sync
    ```
2.  Build package distributions:
    ```bash
    uv build
    ```
3.  Publish to PyPI:
    ```bash
    uv publish
    ```

### Debugging

The best way to debug MCP servers is with the [MCP Inspector](https://github.com/modelcontextprotocol/inspector).

You can launch the Inspector with your local server using this command:

```bash
npx @modelcontextprotocol/inspector uv --directory /Users/RonanMcGovern/TR/trelis-gitingest-mcp run trelis-gitingest-mcp
```

or using uvx for the mcp server:
```bash
npx @modelcontextprotocol/inspector uvx https://github.com/TrelisResearch/trelis-gitingest-mcp.git
```

or using the PyPI package:
```bash
npx @modelcontextprotocol/inspector uvx trelis-gitingest-mcp
```

Upon launching, the Inspector will display a URL that you can access in your browser to begin debugging.