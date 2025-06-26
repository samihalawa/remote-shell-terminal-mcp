# Remote Shell Terminal MCP Server

A Model Context Protocol (MCP) server that provides remote shell execution capabilities with automatic environment initialization.

## Features

- **Shell Command Execution**: Execute shell commands remotely with timeout and working directory support
- **Environment Initialization**: Automatically install essential development tools and libraries
- **System Information**: Get comprehensive system information including available tools and environment status
- **Multi-Platform Support**: Works with various package managers (apk, apt, yum, dnf, pacman)
- **Environment Variable Loading**: Automatically loads variables from .env file
- **Startup Script Execution**: Run custom initialization scripts on environment setup

## Tools Available

### 1. `initialize_environment`
Initializes the remote environment with essential development tools and libraries.

**Parameters:**
- `run_startup_script` (bool, default: true): Whether to run the startup script from .env
- `install_additional_packages` (string): Additional packages to install (space-separated)

**What it installs:**
- Basic development tools: bash, curl, wget, git, build tools
- Programming languages: Python3, Node.js, npm
- Text editors: vim, nano
- Utilities: unzip, zip, jq
- Compilers: gcc, g++, make

### 2. `shell_exec`
Execute shell commands remotely with full control.

**Parameters:**
- `command` (string): The shell command to execute
- `cwd` (string, optional): Working directory for the command
- `timeout` (int, default: 30): Timeout in seconds

### 3. `get_system_info`
Get comprehensive system information including OS, architecture, available tools, and environment status.

## Environment Configuration

The server reads configuration from a `.env` file:

```env
# Your API keys and configuration
MEM0_API_KEY=<your-api-key>

# Startup script to run after environment initialization
STARTUP_SCRIPT=echo "Environment initialized!" && date && whoami

# Add any other environment variables you need
CUSTOM_VAR=value
```

## Usage Examples

1. **Initialize Environment:**
   ```
   Call initialize_environment() to set up the development environment
   ```

2. **Execute Commands:**
   ```
   Call shell_exec("ls -la", cwd="/tmp") to list files in /tmp directory
   ```

3. **Get System Info:**
   ```
   Call get_system_info() to see what's available on the system
   ```

## Installation

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt` (or use uv)
3. Configure your `.env` file
4. Run the server: `python main.py`

## Development

The server automatically detects the package manager and installs appropriate tools for the system. It supports:

- **Alpine Linux** (apk)
- **Ubuntu/Debian** (apt)
- **CentOS/RHEL** (yum)
- **Fedora** (dnf)
- **Arch Linux** (pacman)

## Security Note

This server executes shell commands remotely. Use with caution and ensure proper access controls are in place.
