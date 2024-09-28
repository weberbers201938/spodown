require('dotenv').config();
const { exec } = require('child_process');
const path = require('path');

const pythonPath = process.env.PYTHON_PATH || 'python3';

// Function to run monitor.js
function runMonitorJs() {
  const monitorPath = path.join(__dirname, 'monitor.js');
  console.log('Running monitor.js...');

  const monitorProcess = exec(`node ${monitorPath}`);

  monitorProcess.stdout.on('data', (data) => {
    console.log(`Monitor.js: ${data}`);
  });

  monitorProcess.stderr.on('data', (data) => {
    console.error(`Monitor.js error: ${data}`);
  });

  monitorProcess.on('close', (code) => {
    console.log(`monitor.js process exited with code ${code}`);
    if (code === 0) {
      installPythonDependencies(); // Install dependencies after monitor.js completes
    } else {
      console.log('monitor.js failed, not running pip install or main.py');
    }
  });
}

// Function to install Python dependencies using pip
function installPythonDependencies() {
  const requirementsPath = path.join(__dirname, 'requirements.txt');
  console.log('Installing Python dependencies...');

  const pipInstallProcess = exec(`${pythonPath} -m pip install -r ${requirementsPath}`);

  pipInstallProcess.stdout.on('data', (data) => {
    console.log(`pip install: ${data}`);
  });

  pipInstallProcess.stderr.on('data', (data) => {
    console.error(`pip install error: ${data}`);
  });

  pipInstallProcess.on('close', (code) => {
    console.log(`pip install process exited with code ${code}`);
    if (code === 0) {
      runMainPy(); // Run main.py after pip install completes successfully
    } else {
      console.log('pip install failed, not running main.py');
    }
  });
}

// Function to run main.py
function runMainPy() {
  const mainPyPath = path.join(__dirname, 'main.py');
  console.log('Running main.py...');

  const pythonProcess = exec(`${pythonPath} ${mainPyPath}`);

  pythonProcess.stdout.on('data', (data) => {
    console.log(`Main.py: ${data}`);
  });

  pythonProcess.stderr.on('data', (data) => {
    console.error(`Main.py error: ${data}`);
  });

  pythonProcess.on('close', (code) => {
    console.log(`main.py process exited with code ${code}`);
  });
}

// Start by running monitor.js
runMonitorJs();
