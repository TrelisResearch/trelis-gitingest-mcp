import asyncio
import os
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse

from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
from pydantic import AnyUrl
import mcp.server.stdio
from gitingest import ingest, ingest_async

# Store gitingest results as a simple key-value dict
ingest_results: dict[str, tuple[str, str, str]] = {}  # uri -> (summary, tree, content)

server = Server("gitingest-mcp")

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


@server.list_prompts()
async def handle_list_prompts() -> list[types.Prompt]:
    """
    List available prompts.
    Each prompt can have optional arguments to customize its behavior.
    """
    return [
        types.Prompt(
            name="summarize-repo",
            description="Creates a summary of a repository",
            arguments=[
                types.PromptArgument(
                    name="repo_uri",
                    description="URI of the repository to summarize",
                    required=True,
                ),
                types.PromptArgument(
                    name="detail_level",
                    description="Level of detail (brief/detailed)",
                    required=False,
                )
            ],
        )
    ]

@server.get_prompt()
async def handle_get_prompt(
    name: str, arguments: dict[str, str] | None
) -> types.GetPromptResult:
    """
    Generate a prompt by combining arguments with server state.
    The prompt includes repository information from gitingest and can be customized via arguments.
    """
    if name != "summarize-repo":
        raise ValueError(f"Unknown prompt: {name}")

    if not arguments or "repo_uri" not in arguments:
        raise ValueError("Missing required argument: repo_uri")
        
    repo_uri = arguments.get("repo_uri")
    detail_level = arguments.get("detail_level", "brief")
    detail_prompt = " Provide extensive details about the code structure and implementation." if detail_level == "detailed" else ""
    
    # Check if we already have results for this repo
    # Try to find a matching repository URI
    matching_uri = None
    for key in ingest_results.keys():
        if key == repo_uri or key.endswith(repo_uri):
            matching_uri = key
            break
    
    if not matching_uri:
        available_repos = list(ingest_results.keys())
        raise ValueError(f"Repository not ingested yet: {repo_uri}. Use the ingest-repo tool first.\nAvailable repositories: {available_repos}")
        
    summary, tree, content = ingest_results[matching_uri]
    
    return types.GetPromptResult(
        description=f"Summarize the repository: {matching_uri}",
        messages=[
            types.PromptMessage(
                role="user",
                content=types.TextContent(
                    type="text",
                    text=f"Here is the repository information to summarize for {matching_uri}.{detail_prompt}\n\n"
                    + f"SUMMARY:\n{summary}\n\n"
                    + f"FILE TREE:\n{tree}\n\n"
                    + (f"CONTENT:\n{content[:2000]}..." if detail_level == "detailed" else ""),
                ),
            )
        ],
    )

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    List available tools.
    Each tool specifies its arguments using JSON Schema validation.
    """
    return [
        types.Tool(
            name="ingest-repo",
            description="Ingest a Git repository from URL or local path",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_uri": {"type": "string", "description": "URL or local path to the Git repository"},
                    "output_file": {"type": "string", "description": "Optional path to save the digest output"},
                    "max_file_size": {"type": "integer", "description": "Maximum file size in bytes (default: 10MB)"},
                    "include_patterns": {"type": "string", "description": "Comma-separated patterns of files to include"},
                    "exclude_patterns": {"type": "string", "description": "Comma-separated patterns of files to exclude"},
                    "branch": {"type": "string", "description": "Specific branch to analyze (default: main/master)"}
                },
                "required": ["repo_uri"],
            },
        ),
        types.Tool(
            name="query-repo",
            description="Query specific parts of an ingested repository (NOTE: You must call ingest-repo first)",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_uri": {"type": "string", "description": "URL or local path of the repository that was previously ingested using ingest-repo"},
                    "resource_type": {"type": "string", "enum": ["summary", "tree", "content"], "description": "Type of resource to query (required)"},
                    "file_path": {"type": "string", "description": "Optional specific file path to query (only used when resource_type is 'content')"},
                    "search_term": {"type": "string", "description": "Optional search term to find in content"}
                },
                "required": ["repo_uri", "resource_type"],
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
        
    if name == "ingest-repo":
        return await handle_ingest_repo(arguments)
    elif name == "query-repo":
        return await handle_query_repo(arguments)
    else:
        raise ValueError(f"Unknown tool: {name}")


async def handle_ingest_repo(arguments: dict) -> list[types.TextContent]:
    """
    Handle the ingest-repo tool execution.
    """
    repo_uri = arguments.get("repo_uri")
    if not repo_uri:
        raise ValueError("Missing repo_uri")
        
    # Extract optional parameters
    output_file = arguments.get("output_file")
    max_file_size = arguments.get("max_file_size", 10 * 1024 * 1024)  # Default 10MB
    branch = arguments.get("branch")
    
    # Handle include/exclude patterns
    include_patterns = None
    if arguments.get("include_patterns"):
        include_patterns = set(p.strip() for p in arguments["include_patterns"].split(","))
        
    exclude_patterns = None
    if arguments.get("exclude_patterns"):
        exclude_patterns = set(p.strip() for p in arguments["exclude_patterns"].split(","))

    try:
        # Run gitingest on the repository with all parameters
        if asyncio.get_event_loop().is_running():
            summary, tree, content = await ingest_async(
                source=repo_uri,
                max_file_size=max_file_size,
                include_patterns=include_patterns,
                exclude_patterns=exclude_patterns,
                branch=branch,
                output=output_file
            )
        else:
            summary, tree, content = ingest(
                source=repo_uri,
                max_file_size=max_file_size,
                include_patterns=include_patterns,
                exclude_patterns=exclude_patterns,
                branch=branch,
                output=output_file
            )
            
        # Store the raw content for potential file-specific queries later
        ingest_results[repo_uri] = (summary, tree, content)

        # Notify clients that resources have changed
        await server.request_context.session.send_resource_list_changed()

        # Prepare response
        token_estimate = len(content) // 4  # Rough estimate of token count
        file_count = tree.count('\n')  # Rough estimate of file count
        
        return [
            types.TextContent(
                type="text",
                text=f"Successfully ingested repository: {repo_uri}\n\n"
                     f"Summary:\n{summary[:500]}...\n\n"
                     f"Statistics:\n"
                     f"- Approximately {file_count} files processed\n"
                     f"- Approximately {token_estimate} tokens in content\n"
                     f"- Content size: {len(content)} characters\n"
                     + (f"\nOutput saved to: {output_file}" if output_file else ""),
            )
        ]
    except Exception as e:
        return [
            types.TextContent(
                type="text",
                text=f"Error ingesting repository {repo_uri}: {str(e)}",
            )
        ]


async def handle_query_repo(arguments: dict) -> list[types.TextContent]:
    """
    Handle the query-repo tool execution.
    """
    repo_uri = arguments.get("repo_uri")
    resource_type = arguments.get("resource_type")
    
    if not repo_uri:
        raise ValueError("Missing repo_uri")
    if not resource_type:
        raise ValueError("Missing resource_type")
        
    # Try to find a matching repository URI
    matching_uri = None
    for key in ingest_results.keys():
        if key == repo_uri or key.endswith(repo_uri):
            matching_uri = key
            break
    
    if not matching_uri:
        available_repos = list(ingest_results.keys())
        raise ValueError(f"Repository not ingested yet: {repo_uri}. Use the ingest-repo tool first.\nAvailable repositories: {available_repos}")
        
    summary, tree, content = ingest_results[matching_uri]
    
    # Extract repo name from the URI to help with file path matching
    repo_name = repo_uri.split('/')[-1]
    if '.' in repo_name:
        repo_name = repo_name.split('.')[0]
    
    # Handle basic resource types
    if resource_type == "summary":
        return [types.TextContent(type="text", text=summary)]
    elif resource_type == "tree":
        return [types.TextContent(type="text", text=tree)]
    elif resource_type == "content":
        # Check if we need to filter by file path
        file_path = arguments.get("file_path")
        search_term = arguments.get("search_term")
        
        if file_path:
            # Simple file extraction - this is a basic implementation
            # A more robust implementation would parse the content properly
            
            # For browser-use repository, we know the exact prefix pattern
            if "browser-use" in repo_uri:
                prefixed_path = f"browser-use-browser-use/{file_path}"
                file_marker = f"### {prefixed_path}\n"
            else:
                # Try with the exact path first
                file_marker = f"### {file_path}\n"
            
            start_idx = content.find(file_marker)
            
            # If not found and not already using a prefix, try with repository name prefix
            if start_idx == -1 and "browser-use-browser-use/" not in file_marker:
                # Try with different prefix patterns
                prefixed_path = f"{repo_name}-{repo_name}/{file_path}"
                file_marker = f"### {prefixed_path}\n"
                start_idx = content.find(file_marker)
                
                # If still not found, try with just the repo name
                if start_idx == -1:
                    prefixed_path = f"{repo_name}/{file_path}"
                    file_marker = f"### {prefixed_path}\n"
                    start_idx = content.find(file_marker)
            
            # If still not found, return error with available files
            if start_idx == -1:
                return [types.TextContent(
                    type="text", 
                    text=f"File not found: {file_path}\n\nAvailable files:\n{tree}"
                )]
                
            next_file_marker = "### "
                
            start_idx += len(file_marker)
            end_idx = content.find(next_file_marker, start_idx)
            
            if end_idx == -1:
                file_content = content[start_idx:]
            else:
                file_content = content[start_idx:end_idx]
                
            result_text = f"File: {file_path}\n\n{file_content.strip()}"
            
            # Apply search if specified
            if search_term and search_term in file_content:
                lines = file_content.split('\n')
                matching_lines = [f"{i+1}: {line}" for i, line in enumerate(lines) if search_term in line]
                result_text += f"\n\nMatches for '{search_term}':\n" + "\n".join(matching_lines)
                
            return [types.TextContent(type="text", text=result_text)]
        elif search_term:
            # Search across all content
            lines = content.split('\n')
            matching_lines = [f"{i+1}: {line}" for i, line in enumerate(lines) if search_term in line]
            
            if not matching_lines:
                return [types.TextContent(
                    type="text", 
                    text=f"No matches found for: '{search_term}'"
                )]
                
            result_text = f"Search results for '{search_term}':\n" + "\n".join(matching_lines[:100])
            if len(matching_lines) > 100:
                result_text += f"\n\n...and {len(matching_lines) - 100} more matches."
                
            return [types.TextContent(type="text", text=result_text)]
        else:
            # Return full content
            return [types.TextContent(type="text", text=content)]

async def main():
    # Run the server using stdin/stdout streams
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="gitingest-mcp",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )