#!/usr/bin/env node

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  Tool,
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import { exec, spawn } from 'child_process';
import { promisify } from 'util';
import dotenv from 'dotenv';

dotenv.config();

const execAsync = promisify(exec);

// Tool definitions
const SHELL_EXEC_TOOL: Tool = {
  name: 'shell-exec',
  description: 'Execute shell commands remotely. This tool allows running shell commands on the remote system and returns the output. Use with caution as it can execute any command.',
  inputSchema: {
    type: 'object',
    properties: {
      command: {
        type: 'string',
        description: 'The shell command to execute',
      },
      cwd: {
        type: 'string',
        description: 'Working directory for the command (optional)',
      },
      timeout: {
        type: 'number',
        description: 'Timeout in milliseconds (default: 30000)',
      },
    },
    required: ['command'],
  },
};

// Create server instance
const server = new Server(
  {
    name: 'remote-shell-mcp',
    version: '0.0.1',
  },
  {
    capabilities: {
      tools: {},
      logging: {},
    },
  }
);

// Helper function to execute shell commands
async function executeShellCommand(command: string, cwd?: string, timeout: number = 30000) {
  try {
    const options: any = { timeout };
    if (cwd) {
      options.cwd = cwd;
    }
    
    const { stdout, stderr } = await execAsync(command, options);
    return {
      success: true,
      stdout: stdout.toString(),
      stderr: stderr.toString(),
      command,
      cwd: cwd || process.cwd()
    };
  } catch (error: any) {
    return {
      success: false,
      stdout: error.stdout?.toString() || '',
      stderr: error.stderr?.toString() || error.message,
      command,
      cwd: cwd || process.cwd(),
      error: error.message
    };
  }
}

// Register tool handlers
server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [SHELL_EXEC_TOOL],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  try {
    const { name, arguments: args } = request.params;
    
    if (!args) {
      throw new Error('No arguments provided');
    }
    
    switch (name) {
      case 'shell-exec': {
        const { command, cwd, timeout } = args as { command: string, cwd?: string, timeout?: number };
        const result = await executeShellCommand(command, cwd, timeout);
        
        let responseText = `Command: ${result.command}\n`;
        responseText += `Working Directory: ${result.cwd}\n`;
        responseText += `Success: ${result.success}\n\n`;
        
        if (result.stdout) {
          responseText += `STDOUT:\n${result.stdout}\n`;
        }
        
        if (result.stderr) {
          responseText += `STDERR:\n${result.stderr}\n`;
        }
        
        if (result.error) {
          responseText += `ERROR: ${result.error}\n`;
        }
        
        return {
          content: [
            {
              type: 'text',
              text: responseText,
            },
          ],
          isError: !result.success,
        };
      }
      
      default:
        return {
          content: [
            { type: 'text', text: `Unknown tool: ${name}` },
          ],
          isError: true,
        };
    }
  } catch (error) {
    return {
      content: [
        {
          type: 'text',
          text: `Error: ${error instanceof Error ? error.message : String(error)}`,
        },
      ],
      isError: true,
    };
  }
});

// Function to log safely
function safeLog(
  level: 'error' | 'debug' | 'info' | 'notice' | 'warning' | 'critical' | 'alert' | 'emergency',
  data: any
): void {
  // For stdio transport, log to stderr to avoid protocol interference
  console.error(`[${level}] ${typeof data === 'object' ? JSON.stringify(data) : data}`);
  
  // Send to logging capability if available
  try {
    server.sendLoggingMessage({ level, data });
  } catch (error) {
    // Ignore errors when logging is not available
  }
}

// Server startup
async function main() {
  try {
    console.error('Initializing Remote Shell MCP Server...');
    
    const transport = new StdioServerTransport();
    await server.connect(transport);
    
    safeLog('info', 'Remote Shell MCP Server initialized successfully');
    console.error('Remote Shell MCP Server running on stdio');
  } catch (error) {
    console.error('Fatal error running server:', error);
    process.exit(1);
  }
}

main().catch((error) => {
  console.error('Fatal error in main():', error);
  process.exit(1);
});