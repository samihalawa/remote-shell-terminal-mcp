from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from mcp.server.sse import SseServerTransport
from starlette.requests import Request
from starlette.routing import Mount, Route
from mcp.server import Server
import uvicorn
import subprocess
import asyncio
import os
from dotenv import load_dotenv
import json

load_dotenv()

# Initialize FastMCP server for shell tools
mcp = FastMCP("remote-shell-mcp")

@mcp.tool(
    description="""Initialize the remote environment with essential development tools and libraries. 
    This tool installs basic development packages, sets up the environment, and runs any initial setup scripts.
    It also loads environment variables from .env file and executes startup scripts if configured."""
)
async def initialize_environment(run_startup_script: bool = True, install_additional_packages: str = "") -> str:
    """Initialize the remote environment with essential tools and setup.

    Args:
        run_startup_script: Whether to run the startup script from .env (default: True)
        install_additional_packages: Additional packages to install (space-separated)
    """
    try:
        results = []
        
        # Step 1: Detect package manager and install basic tools
        results.append("=== Detecting package manager ===")
        
        # Check for different package managers
        pkg_managers = [
            ("apk", "apk update && apk add --no-cache bash curl wget git build-base vim nano unzip zip jq python3 py3-pip nodejs npm gcc g++ make"),
            ("apt", "apt update && apt install -y build-essential curl wget git bash vim nano unzip zip jq python3 python3-pip nodejs npm gcc g++"),
            ("yum", "yum update -y && yum install -y curl wget git bash vim nano unzip zip jq python3 python3-pip nodejs npm gcc gcc-c++ make"),
            ("dnf", "dnf update -y && dnf install -y curl wget git bash vim nano unzip zip jq python3 python3-pip nodejs npm gcc gcc-c++ make"),
            ("pacman", "pacman -Syu --noconfirm curl wget git bash vim nano unzip zip jq python python-pip nodejs npm gcc make")
        ]
        
        pkg_manager_found = None
        install_cmd = None
        
        for pm, cmd in pkg_managers:
            check_result = subprocess.run(f"which {pm}", shell=True, capture_output=True, text=True)
            if check_result.returncode == 0:
                pkg_manager_found = pm
                install_cmd = cmd
                break
        
        if not pkg_manager_found:
            return json.dumps({
                "success": False,
                "error": "No supported package manager found (apk, apt, yum, dnf, pacman)",
                "results": results
            }, indent=2)
        
        results.append(f"Found package manager: {pkg_manager_found}")
        
        # Step 2: Install basic development tools
        results.append("=== Installing basic development tools ===")
        install_result = subprocess.run(install_cmd, shell=True, capture_output=True, text=True, timeout=300)
        
        if install_result.returncode != 0:
            results.append(f"Warning: Some packages may have failed to install: {install_result.stderr}")
        else:
            results.append("Basic development tools installed successfully")
        
        # Step 3: Install additional packages if specified
        if install_additional_packages.strip():
            results.append("=== Installing additional packages ===")
            additional_cmd = f"{pkg_manager_found} install -y {install_additional_packages}" if pkg_manager_found != "apk" else f"apk add --no-cache {install_additional_packages}"
            additional_result = subprocess.run(additional_cmd, shell=True, capture_output=True, text=True, timeout=120)
            if additional_result.returncode == 0:
                results.append(f"Additional packages installed: {install_additional_packages}")
            else:
                results.append(f"Warning: Failed to install some additional packages: {additional_result.stderr}")
        
        # Step 4: Set up environment variables from .env
        results.append("=== Loading environment variables ===")
        env_vars_loaded = []
        
        if os.path.exists('.env'):
            with open('.env', 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key] = value
                        env_vars_loaded.append(key)
            
            if env_vars_loaded:
                results.append(f"Loaded environment variables: {', '.join(env_vars_loaded)}")
            else:
                results.append("No environment variables found in .env")
        else:
            results.append("No .env file found")
        
        # Step 5: Run startup script if configured and requested
        if run_startup_script:
            results.append("=== Running startup script ===")
            startup_script = os.environ.get('STARTUP_SCRIPT', '')
            
            if startup_script:
                results.append(f"Executing startup script: {startup_script}")
                startup_result = subprocess.run(startup_script, shell=True, capture_output=True, text=True, timeout=120)
                
                if startup_result.returncode == 0:
                    results.append("Startup script executed successfully")
                    if startup_result.stdout:
                        results.append(f"Startup script output: {startup_result.stdout}")
                else:
                    results.append(f"Startup script failed: {startup_result.stderr}")
            else:
                results.append("No STARTUP_SCRIPT configured in environment")
        
        # Step 6: Verify installation
        results.append("=== Verifying installation ===")
        verification_commands = ["bash --version", "curl --version", "wget --version", "git --version", "python3 --version", "node --version", "npm --version"]
        
        for cmd in verification_commands:
            verify_result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if verify_result.returncode == 0:
                version_info = verify_result.stdout.split('\n')[0]
                results.append(f"✓ {cmd.split()[0]}: {version_info}")
            else:
                results.append(f"✗ {cmd.split()[0]}: Not available")
        
        return json.dumps({
            "success": True,
            "message": "Environment initialization completed",
            "package_manager": pkg_manager_found,
            "env_vars_loaded": env_vars_loaded,
            "results": results
        }, indent=2)
        
    except subprocess.TimeoutExpired:
        return json.dumps({
            "success": False,
            "error": "Initialization timed out",
            "results": results
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "results": results
        }, indent=2)

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

@mcp.tool(
    description="""Get system information including OS, architecture, available tools, and environment status."""
)
async def get_system_info() -> str:
    """Get comprehensive system information."""
    try:
        info = {}
        
        # Basic system info
        info['os'] = subprocess.run('uname -a', shell=True, capture_output=True, text=True).stdout.strip()
        info['architecture'] = subprocess.run('uname -m', shell=True, capture_output=True, text=True).stdout.strip()
        info['kernel'] = subprocess.run('uname -r', shell=True, capture_output=True, text=True).stdout.strip()
        
        # Available tools
        tools_to_check = ['bash', 'curl', 'wget', 'git', 'python3', 'node', 'npm', 'gcc', 'make', 'vim', 'nano']
        available_tools = []
        missing_tools = []
        
        for tool in tools_to_check:
            result = subprocess.run(f'which {tool}', shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                available_tools.append(tool)
            else:
                missing_tools.append(tool)
        
        info['available_tools'] = available_tools
        info['missing_tools'] = missing_tools
        
        # Environment variables
        important_env_vars = ['HOME', 'PATH', 'USER', 'SHELL', 'PWD']
        env_info = {}
        for var in important_env_vars:
            env_info[var] = os.environ.get(var, 'Not set')
        info['environment'] = env_info
        
        # Disk space
        df_result = subprocess.run('df -h /', shell=True, capture_output=True, text=True)
        if df_result.returncode == 0:
            info['disk_space'] = df_result.stdout.strip()
        
        # Memory info
        if os.path.exists('/proc/meminfo'):
            with open('/proc/meminfo', 'r') as f:
                meminfo = f.read()
                info['memory_info'] = meminfo[:500] + '...' if len(meminfo) > 500 else meminfo
        
        return json.dumps(info, indent=2)
        
    except Exception as e:
        return json.dumps({
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
