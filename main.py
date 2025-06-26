from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from mcp.server.sse import SseServerTransport
from starlette.requests import Request
from starlette.routing import Mount, Route
from mcp.server import Server
import uvicorn
import subprocess
import os
from dotenv import load_dotenv
import json

load_dotenv()

mcp = FastMCP("remote-shell-mcp")

@mcp.tool(description="Install essential development libraries and tools")
async def install_initial_libraries(additional_packages: str = "") -> str:
    """Install basic development tools and run startup scripts from .env"""
    try:
        # Install basic tools
        cmd = "apk add --no-cache bash curl wget git build-base vim nano python3 py3-pip nodejs npm jq unzip zip"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
        
        # Install additional packages
        if additional_packages.strip():
            extra_cmd = f"apk add --no-cache {additional_packages}"
            subprocess.run(extra_cmd, shell=True, capture_output=True, text=True, timeout=60)
        
        # Load .env and run startup script
        startup_output = ""
        if os.path.exists('.env'):
            load_dotenv()
            startup = os.environ.get('STARTUP_SCRIPT', '')
            if startup:
                startup_result = subprocess.run(startup, shell=True, capture_output=True, text=True, timeout=30)
                startup_output = startup_result.stdout
        
        return json.dumps({
            "success": True,
            "message": "Development libraries installed successfully",
            "additional_packages": additional_packages,
            "startup_output": startup_output
        }, indent=2)
        
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)}, indent=2)

@mcp.tool(description="Execute shell commands remotely")
async def shell_exec(command: str, cwd: str = None, timeout: int = 30) -> str:
    """Execute a shell command remotely."""
    try:
        args = {'shell': True, 'capture_output': True, 'text': True, 'timeout': timeout}
        if cwd:
            args['cwd'] = cwd
        
        result = subprocess.run(command, **args)
        
        return json.dumps({
            'command': command,
            'working_directory': cwd or os.getcwd(),
            'exit_code': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'success': result.returncode == 0
        }, indent=2)
    
    except Exception as e:
        return json.dumps({'command': command, 'error': str(e), 'success': False}, indent=2)

@mcp.tool(description="Get system information")
async def get_system_info() -> str:
    """Get system information and available tools."""
    try:
        tools = ['bash', 'curl', 'wget', 'git', 'python3', 'node', 'npm']
        available = [t for t in tools if subprocess.run(f'which {t}', shell=True, capture_output=True).returncode == 0]
        
        return json.dumps({
            'os': subprocess.run('uname -a', shell=True, capture_output=True, text=True).stdout.strip(),
            'available_tools': available,
            'pwd': os.getcwd()
        }, indent=2)
        
    except Exception as e:
        return json.dumps({'error': str(e)}, indent=2)

def create_starlette_app(mcp_server: Server, *, debug: bool = False) -> Starlette:
    sse = SseServerTransport("/messages/")
    async def handle_sse(request: Request) -> None:
        async with sse.connect_sse(request.scope, request.receive, request._send) as (read_stream, write_stream):
            await mcp_server.run(read_stream, write_stream, mcp_server.create_initialization_options())
    return Starlette(debug=debug, routes=[Route("/sse", endpoint=handle_sse), Mount("/messages/", app=sse.handle_post_message)])

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='0.0.0.0')
    parser.add_argument('--port', type=int, default=8080)
    args = parser.parse_args()
    uvicorn.run(create_starlette_app(mcp._mcp_server, debug=True), host=args.host, port=args.port)
