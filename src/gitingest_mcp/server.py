import asyncio
import os
import sys
from urllib.parse import urlparse
from typing import Dict, List, Optional, Any, Tuple

from gitingest import ingest, ingest_async
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
import mcp.server.stdio
import mcp.types as types
from pydantic import AnyUrl

# Dictionary to store ingestion results in memory
ingest_results: Dict[str, Tuple[str, str, str]] = {}

server = Server("trelis-gitingest-mcp")

@server.list_resources()
async def handle_list_resources() -> list[types.Resource]:
    """
    List available gitingest resources.
    Each ingest result is exposed as a resource with a custom gitingest:// URI scheme.
    """
    resources = []
    
    for uri, (summary, tree, content) in ingest_results.items():
        # Parse the URI to extract repository name
        parsed_uri = urlparse(uri)
        path_parts = parsed_uri.path.strip('/').split('/')
        repo_name = path_parts[-1] if path_parts else 'repository'
        
        # Create a safe identifier for the URI that can be used in a new URI
        # Replace problematic characters with underscores
        safe_uri = uri.replace('://', '_').replace('/', '_').replace('.', '_')
        
        # Add summary resource
        resources.append(
            types.Resource(
                uri=AnyUrl(f"gitingest://{safe_uri}/summary"),
                name=f"Summary: {repo_name}",
                description=f"Repository summary for {uri}",
                mimeType="text/plain",
            )
        )
        
        # Add tree resource
        resources.append(
            types.Resource(
                uri=AnyUrl(f"gitingest://{safe_uri}/tree"),
                name=f"Tree: {repo_name}",
                description=f"File tree for {uri}",
                mimeType="text/plain",
            )
        )
        
        # Add content resource
        resources.append(
            types.Resource(
                uri=AnyUrl(f"gitingest://{safe_uri}/content"),
                name=f"Content: {repo_name}",
                description=f"Full content for {uri}",
                mimeType="text/plain",
            )
        )
    
    return resources

@server.read_resource()
async def handle_read_resource(uri: AnyUrl) -> str:
    """
    Read a specific gitingest resource content by its URI.
    The resource type is extracted from the URI path component.
    """
    if uri.scheme != "gitingest":
        raise ValueError(f"Unsupported URI scheme: {uri.scheme}")

    # Extract the original URI and resource type from the path
    path_parts = uri.path.lstrip('/').split('/')
    if not path_parts:
        raise ValueError(f"Invalid gitingest URI: {uri}")
        
    resource_type = path_parts[-1]  # Last part is the resource type (summary, tree, content)
    
    # The original URI is encoded in the host part and possibly part of the path
    # We need to reconstruct it properly
    original_uri = None
    
    # Check all keys in ingest_results to find a match
    for key in ingest_results.keys():
        # Create a normalized version of the key for comparison
        normalized_key = key.replace('://', '_').replace('/', '_').replace('.', '_')
        normalized_host = uri.host.replace('://', '_').replace('/', '_').replace('.', '_')
        
        if normalized_key == normalized_host or key == uri.host:
            original_uri = key
            break
    
    if not original_uri:
        # Print available keys for debugging
        available_keys = list(ingest_results.keys())
        raise ValueError(f"No gitingest results found for: {uri.host}. Available keys: {available_keys}")
    
    # Return the appropriate part of the ingest results
    if resource_type == "summary":
        return ingest_results[original_uri][0]
    elif resource_type == "tree":
        return ingest_results[original_uri][1]
    elif resource_type == "content":
        return ingest_results[original_uri][2]
    else:
        raise ValueError(f"Unknown resource type: {resource_type}")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    List available tools.
    Each tool specifies its arguments using JSON Schema validation.
    """
    return [
        types.Tool(
            name="gitingest",
            description="Access Git repository data with automatic ingestion as needed",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_uri": {"type": "string", "description": "URL or local path to the Git repository"},
                    "resource_type": {"type": "string", "enum": ["summary", "tree", "content", "all"], "description": "Type of data to retrieve (default: summary)"},
                    "max_file_size": {"type": "integer", "description": "Maximum file size in bytes (default: 10MB)"},
                    "include_patterns": {"type": "string", "description": "Comma-separated fnmatch-style glob patterns (e.g., 'src/module/*.py', 'docs/file.md')."},
                    "exclude_patterns": {"type": "string", "description": "Comma-separated fnmatch-style glob patterns (e.g., 'tests/*', '*.tmp')."},
                    "branch": {"type": "string", "description": "Specific branch to analyze"},
                    "output": {"type": "string", "description": "File path to save the output to"},
                    "max_tokens": {"type": "integer", "description": "Maximum number of tokens to return (1 token = 4 characters). If set, response will be truncated."},
                    "token": {"type": "string", "description": "GitHub Personal Access Token (PAT) for private repositories."}
                },
                "required": ["repo_uri"],
            },
        )
    ]

@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """
    Handle tool execution requests.
    Tools can modify server state and notify clients of changes.
    """
    if not arguments:
        raise ValueError("Missing arguments")
        
    if name != "gitingest":
        raise ValueError(f"Unknown tool: {name}")
    
    return await handle_gitingest(arguments)


async def handle_gitingest(arguments: dict) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle the gitingest tool call"""
    # Get the repository URI
    repo_uri = arguments.get("repo_uri")
    if not repo_uri:
        raise ValueError("Missing repo_uri parameter")
    
    # Extract all parameters
    resource_type = arguments.get("resource_type", "summary")
    max_file_size = arguments.get("max_file_size", 10 * 1024 * 1024)  # Default 10MB
    branch = arguments.get("branch")
    output = arguments.get("output")
    include_patterns = arguments.get("include_patterns")
    exclude_patterns = arguments.get("exclude_patterns")
    max_tokens = arguments.get("max_tokens")
    token = arguments.get("token")
    
    # Extract repo name for better display
    parsed_uri = urlparse(repo_uri)
    repo_name = os.path.basename(parsed_uri.path)
    if repo_name.endswith(".git"):
        repo_name = repo_name[:-4]
    
    try:
        matching_uri = repo_uri
    
        # Need to ingest the repository
        try:
            print(f"Ingesting {repo_uri}...", file=sys.stderr)
            if asyncio.get_event_loop().is_running():
                summary, tree, content = await ingest_async(
                    source=repo_uri,
                    max_file_size=max_file_size,
                    include_patterns=include_patterns,
                    exclude_patterns=exclude_patterns,
                    branch=branch,
                    output=output,
                    token=token
                )
            else:
                summary, tree, content = ingest(
                    source=repo_uri,
                    max_file_size=max_file_size,
                    include_patterns=include_patterns,
                    exclude_patterns=exclude_patterns,
                    branch=branch,
                    output=output,
                    token=token
                )
                
            ingest_results[repo_uri] = (summary, tree, content)
        except Exception as e:
            print(f"Error ingesting repository: {e}", file=sys.stderr)
            raise
        
    except Exception as e:
        return [types.TextContent(
            type="text", 
            text=f"Error ingesting repository {repo_uri}: {str(e)}"
        )]
    
    summary, tree, content = ingest_results[matching_uri]
    
    def truncate_to_tokens(text: str, max_tokens: int | None) -> str:
        if max_tokens is None:
            return text
        max_chars = max_tokens * 4
        if len(text) > max_chars:
            return text[:max_chars] + "... (truncated)"
        return text
    
    if resource_type == "all":
        return [
            types.TextContent(
                type="text",
                text=truncate_to_tokens(
                    f"Repository: {repo_uri}\n\n"
                    f"SUMMARY:\n{summary}\n\n"
                    f"FILE TREE:\n{tree}\n\n"
                    f"CONTENT:\n{content}\n\n",
                    max_tokens
                )
            )
        ]
    elif resource_type == "summary":
        return [types.TextContent(type="text", text=truncate_to_tokens(summary, max_tokens))]
    elif resource_type == "tree":
        return [types.TextContent(type="text", text=truncate_to_tokens(tree, max_tokens))]
    elif resource_type == "content":
        return [types.TextContent(type="text", text=truncate_to_tokens(content, max_tokens))]
    
    return [types.TextContent(type="text", text="Invalid resource_type specified.")]


def main():
    asyncio.run(_main())

async def _main():
    # Run the server using stdin/stdout streams
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="trelis-gitingest-mcp",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    main()