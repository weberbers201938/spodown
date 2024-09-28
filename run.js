const { spawn } = require("child_process");
const path = require("path");

function startBotProcess(script) {
    // Get the extension of the file to determine if it's a Python or Node script
    const extension = path.extname(script);

    // Choose the correct command based on the file type
    const command = extension === ".js" ? "node" : extension === ".py" ? "python" : null;

    if (!command) {
        console.error(`Unsupported script type: ${script}`);
        return;
    }

    const child = spawn(command, [script], {
        cwd: __dirname,
        stdio: "inherit",
        shell: true
    });

    child.on("close", (codeExit) => {
        console.log(`${script} process exited with code: ${codeExit}`);
        if (codeExit !== 0) {
            setTimeout(() => startBotProcess(script), 3000);
        }
    });

    child.on("error", (error) => {
        console.error(`An error occurred starting the ${script} process: ${error}`);
    });
}

// Start the processes for Python and Node.js scripts
startBotProcess("main.py");
startBotProcess("monitor.js");
