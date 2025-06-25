# Remote Shell MCP Server

[![smithery badge](https://smithery.ai/badge/@samihalawa/remote-shell-terminal-mcp)](https://smithery.ai/server/@samihalawa/remote-shell-terminal-mcp)

This demonstrates a structured approach for using an [MCP](https://modelcontextprotocol.io/introduction) server to execute shell commands remotely. The server can be used with any MCP-compatible client and provides essential tools for running shell commands on remote systems.

## Installation

### Installing via Smithery

To install remote-shell-terminal-mcp for Claude Desktop automatically via [Smithery](https://smithery.ai/server/@samihalawa/remote-shell-terminal-mcp):

```bash
npx -y @smithery/cli install @samihalawa/remote-shell-terminal-mcp --client claude
```

### Manual Installation
1. Clone this repository
2. Initialize the `uv` environment:

```bash
uv venv
```

3. Activate the virtual environment:

```bash
source .venv/bin/activate
```

4. Install the dependencies using `uv`:

```bash
# Install in editable mode from pyproject.toml
uv pip install -e .
```

5. Optionally, create a `.env` file for any environment-specific configuration (currently not required for basic functionality).

## Usage

1. Start the MCP server:

```bash
uv run main.py
```

2. In MCP-compatible clients, connect to the SSE endpoint:

```
http://0.0.0.0:8080/sse
```

Or use the TypeScript/Node.js version directly via stdio transport.

## Features

The server provides a shell execution tool:

1. `shell_exec` (Python version) / `shell-exec` (TypeScript version): Execute shell commands remotely with support for:
   - Custom working directory
   - Configurable timeout
   - Detailed output including stdout, stderr, and exit codes
   - Error handling and timeout management

## Node.js/TypeScript Version

For the Node.js version, navigate to the `node/shell` directory:

```bash
cd node/shell
npm install
npm run build
npm start
```

Or run directly with:
```bash
npx @remote-shell/mcp-server
```

## Why?

This implementation allows for remote shell execution via MCP. The SSE-based server can run as a process that agents connect to, use, and disconnect from whenever needed. This pattern fits well with "cloud-native" use cases where the server and clients can be decoupled processes on different nodes.

### Server

By default, the server runs on 0.0.0.0:8080 but is configurable with command line arguments like:

```
uv run main.py --host <your host> --port <your port>
```

The server exposes an SSE endpoint at `/sse` that MCP clients can connect to for executing shell commands remotely.

## Security Considerations

**WARNING**: This tool allows execution of arbitrary shell commands. Use with extreme caution and proper security measures:

- Only deploy in trusted environments
- Consider implementing authentication and authorization
- Limit network access to the server
- Monitor and log all command executions
- Consider using sandboxing or containerization

