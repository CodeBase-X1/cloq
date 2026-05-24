import * as vscode from 'vscode';
import { spawn, ChildProcess } from 'child_process';
import * as os from 'os';

let proxyProcess: ChildProcess | undefined;
let statusBarItem: vscode.StatusBarItem;

export function activate(context: vscode.ExtensionContext) {
    console.log('Cloq extension is now active!');

    // Create status bar item
    statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
    statusBarItem.command = 'cloq.openDashboard';
    context.subscriptions.push(statusBarItem);

    // Register commands
    let startCmd = vscode.commands.registerCommand('cloq.startProxy', () => {
        startCloqProxy();
    });

    let dashboardCmd = vscode.commands.registerCommand('cloq.openDashboard', () => {
        vscode.env.openExternal(vscode.Uri.parse('http://127.0.0.1:8989/ui'));
    });

    context.subscriptions.push(startCmd, dashboardCmd);

    // Auto-start the proxy when extension loads
    startCloqProxy();
}

function startCloqProxy() {
    if (proxyProcess) {
        vscode.window.showInformationMessage('Cloq Proxy is already running.');
        return;
    }

    const config = vscode.workspace.getConfiguration('cloq');
    let cliCommand = config.get<string>('cliCommand') || 'cloq-cli';
    const port = config.get<number>('proxyPort') || 8989;

    // Handle Windows execution if it's the raw command
    if (os.platform() === 'win32' && cliCommand === 'cloq-cli') {
        cliCommand = 'cloq-cli.exe'; // or .cmd depending on installation
    }

    statusBarItem.text = '$(sync~spin) Cloq Starting...';
    statusBarItem.show();

    // Spawn the proxy
    proxyProcess = spawn(cliCommand, ['start', '--port', port.toString()], {
        shell: os.platform() === 'win32' // Use shell on Windows to resolve PATH better
    });

    proxyProcess.on('error', (err) => {
        console.error('Failed to start Cloq CLI:', err);
        statusBarItem.text = '$(error) Cloq Failed';
        statusBarItem.tooltip = `Error starting Cloq: ${err.message}. Check if it is installed in your PATH.`;
        vscode.window.showErrorMessage(`Cloq failed to start: ${err.message}. Please install it via "pip install cloq" and ensure it is in your PATH.`);
        proxyProcess = undefined;
    });

    proxyProcess.stdout?.on('data', (data) => {
        const output = data.toString();
        console.log(`Cloq: ${output}`);
        if (output.includes('Uvicorn running on') || output.includes('Proxy Active')) {
            statusBarItem.text = '$(shield) Cloq Active';
            statusBarItem.tooltip = 'Cloq Proxy is protecting your LLM requests. Click to open dashboard.';
        }
    });

    proxyProcess.stderr?.on('data', (data) => {
        console.error(`Cloq Log: ${data}`);
        // Sometimes FastAPI/Uvicorn logs to stderr even for normal startup
        if (data.toString().includes('Uvicorn running on')) {
            statusBarItem.text = '$(shield) Cloq Active';
            statusBarItem.tooltip = 'Cloq Proxy is protecting your LLM requests. Click to open dashboard.';
        }
    });

    proxyProcess.on('close', (code) => {
        console.log(`Cloq proxy exited with code ${code}`);
        proxyProcess = undefined;
        statusBarItem.text = '$(error) Cloq Stopped';
        statusBarItem.tooltip = 'Click to restart';
        statusBarItem.command = 'cloq.startProxy';
    });
}

export function deactivate() {
    if (proxyProcess) {
        console.log('Shutting down Cloq proxy...');
        proxyProcess.kill();
    }
}
