from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from mcp.server.sse import SseServerTransport
from starlette.requests import Request
from starlette.routing import Mount, Route
from mcp.server import Server
import uvicorn
import subprocess
import asyncio
from dotenv import load_dotenv
import json

load_dotenv()

# Initialize FastMCP server for shell tools
mcp = FastMCP("remote-shell-mcp")

@mcp.tool(
    description="""Execute shell commands remotely. This tool allows running shell commands on the remote system and returns the output. 
    Use with caution as it can execute any command. Supports setting working directory and timeout."""
)
async def shell_exec(command: str, cwd: str = None, timeout: int = 30) -> str:
    """Execute a shell command remotely.

    Args:
        command: The shell command to execute
        cwd: Working directory for the command (optional)
        timeout: Timeout in seconds (default: 30)
    """
    try:
        # Prepare the command execution
        process_args = {
            'shell': True,
            'capture_output': True,
            'text': True,
            'timeout': timeout
        }
        
        if cwd:
            process_args['cwd'] = cwd
        
        # Execute the command
        result = subprocess.run(command, **process_args)
        
        response = {
            'command': command,
            'working_directory': cwd or subprocess.run('pwd', shell=True, capture_output=True, text=True).stdout.strip(),
            'exit_code': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'success': result.returncode == 0
        }
        
        return json.dumps(response, indent=2)
    
    except subprocess.TimeoutExpired:
        return json.dumps({
            'command': command,
            'working_directory': cwd or 'unknown',
            'error': f'Command timed out after {timeout} seconds',
            'success': False
        }, indent=2)
    except Exception as e:
        return json.dumps({
            'command': command,
            'working_directory': cwd or 'unknown',
            'error': str(e),
            'success': False
        }, indent=2)


def create_starlette_app(mcp_server: Server, *, debug: bool = False) -> Starlette:
    """Create a Starlette application that can server the provied mcp server with SSE."""
    sse = SseServerTransport("/messages/")

    async def handle_sse(request: Request) -> None:
        async with sse.connect_sse(
                request.scope,
                request.receive,
                request._send,  # noqa: SLF001
        ) as (read_stream, write_stream):
            await mcp_server.run(
                read_stream,
                write_stream,
                mcp_server.create_initialization_options(),
            )

    return Starlette(
        debug=debug,
        routes=[
            Route("/sse", endpoint=handle_sse),
            Mount("/messages/", app=sse.handle_post_message),
        ],
    )


if __name__ == "__main__":
    mcp_server = mcp._mcp_server

    import argparse

    parser = argparse.ArgumentParser(description='Run MCP SSE-based server')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8080, help='Port to listen on')
    args = parser.parse_args()

    # Bind SSE request handling to MCP server
    starlette_app = create_starlette_app(mcp_server, debug=True)

    uvicorn.run(starlette_app, host=args.host, port=args.port)
