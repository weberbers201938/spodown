from flask import Flask, request, send_file, jsonify
import subprocess, json
import time, os, zipfile, shutil
from threading import Thread
from sys import platform
import uuid

app = Flask(__name__)

# Global dictionary to store download states for multiple users
download_states = {}

# Install FFMPEG if needed
def installFFMPEG():
    binary = "python3"
    if platform == "win32":
        binary += ".exe"
    proc = subprocess.Popen([binary, "-m", "spotdl", "--download-ffmpeg"], stdout=subprocess.PIPE, stdin=subprocess.PIPE)
    time.sleep(5)
    proc.stdin.write(b"y")
    proc.stdin.flush()

installFFMPEG()

# Function to read stdout and update progress for a specific session
def readStdout(process, session_id):
    while True:
        line = process.stdout.readline()
        if not line:
            break
        if line.startswith(b"Found "):
            try:
                download_states[session_id]["num"] = int(line.split(b" ")[1].decode())
            except:
                pass
        if line.startswith(b"Downloaded ") or line.startswith(b"Skipping "):
            download_states[session_id]["downloaded_size"] += 1
        download_states[session_id]["output"] += line
        time.sleep(0.05)

# Cleanup function to delete old sessions after 1 hour
def cleanup_sessions():
    while True:
        current_time = time.time()
        for session_id, state in list(download_states.items()):
            folder_creation_time = os.path.getctime(state["folder"])
            if current_time - folder_creation_time > 3600:
                try:
                    shutil.rmtree(state["folder"])
                    del download_states[session_id]
                except Exception as e:
                    print(f"Failed to delete session {session_id}: {e}")
        time.sleep(3600)

# Start the cleanup thread
Thread(target=cleanup_sessions).start()

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        try:
            url = json.loads(request.data.decode())["url"]
        except Exception as e:
            return jsonify({"error": "Invalid data format"}), 400

        if not url.startswith("https://open.spotify.com/"):
            return jsonify({"error": "Invalid Spotify URL"}), 400

        session_id = str(uuid.uuid4())
        download_folder = f"./downloads/{session_id}/"

        if not os.path.exists(download_folder):
            os.makedirs(download_folder)

        download_states[session_id] = {
            "output": b"",
            "n": 1,
            "num": 1,
            "download_size": 1,
            "downloaded_size": 0,
            "folder": download_folder,
            "timestamp": time.time(),
            "error": None
        }

        process = subprocess.Popen(
            ["python3", '-m', 'spotdl', f'{url}', '--output', download_folder], 
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        def monitor_process(process, session_id):
            try:
                readStdout(process, session_id)
            except Exception as e:
                download_states[session_id]["error"] = str(e)

        Thread(target=monitor_process, args=(process, session_id)).start()

        return jsonify({"session_id": session_id})

    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>SpoDown</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha3/dist/css/bootstrap.min.css" rel="stylesheet">
        <script src="https://cdn.jsdelivr.net/npm/sweetalert2@11"></script>
        <style>
            body {
                background: linear-gradient(to right, #e0f7fa, #80deea);
                font-family: 'Poppins', sans-serif;
                color: #333;
            }
            .header {
                background-color: #0288d1;
                color: white;
                padding: 20px;
                text-align: center;
            }
            .header h1 {
                margin: 0;
                font-size: 2.5rem;
            }
            .container {
                max-width: 600px;
                margin: 50px auto;
                padding: 20px;
                background-color: #ffffff;
                color: #333;
                box-shadow: 0px 0px 15px rgba(0, 0, 0, 0.2);
                border-radius: 10px;
            }
            .search-container input[type="text"] {
                width: 100%;
                padding: 15px;
                margin: 10px 0;
                border: 2px solid #0288d1;
                border-radius: 5px;
                font-size: 16px;
                background-color: #f9f9f9;
                color: #333;
            }
            .search-container button[type="submit"] {
                background: linear-gradient(to right, #0288d1, #00acc1);
                color: white;
                padding: 12px 20px;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                width: 100%;
                font-size: 18px;
            }
            .search-container button[type="submit"]:hover {
                background: linear-gradient(to right, #00acc1, #0288d1);
            }
            textarea#output {
                width: 100%;
                height: 300px;
                margin-top: 20px;
                padding: 15px;
                border: 2px solid #0288d1;
                border-radius: 5px;
                resize: none;
                font-size: 14px;
                background-color: #f9f9f9;
                color: #333;
            }
            .btn-download {
                background: linear-gradient(to right, #28a745, #218838);
                color: white;
                padding: 12px 20px;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                display: none;
                text-align: center;
                width: 100%;
                margin-top: 20px;
                font-size: 18px;
            }
            .btn-download:hover {
                background: linear-gradient(to right, #218838, #28a745);
            }
            .progress {
                height: 30px;
                background-color: #e9ecef;
                border-radius: 5px;
                overflow: hidden;
                margin-top: 20px;
            }
            .progress-bar {
                background-color: #0288d1;
                height: 100%;
                width: 0%;
                text-align: center;
                line-height: 30px;
                color: white;
                font-weight: bold;
                transition: width 0.4s ease;
            }
        </style>
    </head>
    <body>

        <div class="header">
            <h1>SpoDown</h1>
        </div>

        <div class="container">
            <form id="form" method="POST" class="search-container">
                <label for="url">Enter Playlist or Track URL:</label>
                <input type="text" id="url" name="url" placeholder="Enter Spotify Playlist or Track URL">
                <button type="submit"><i class="fas fa-download"></i> Start Download</button>
            </form>

            <div class="progress">
                <div class="progress-bar" id="progressBar">%</div>
            </div>

            <textarea id="output" readonly placeholder="Download output will appear here..."></textarea>

            <button id="downloadBtn" class="btn-download">
                <i class="fas fa-file-archive"></i> Download ZIP
            </button>
        </div>
        <script>
            const form = document.getElementById('form');
            const output = document.getElementById('output');
            const progressBar = document.getElementById('progressBar');
            const downloadBtn = document.getElementById('downloadBtn');
            let sessionId = null;
            let downloadComplete = false;

            form.addEventListener('submit', async (event) => {
                event.preventDefault();
                const url = document.getElementById('url').value;

                if (!url) {
                    Swal.fire({
                        icon: 'error',
                        title: 'Oops...',
                        text: 'Please enter a valid URL!',
                    });
                    return;
                }

                if (url.includes("track")) {
                    Swal.fire({
                        title: 'Downloading your track',
                        text: 'Please wait while your track is being downloaded.',
                        icon: 'info',
                        showConfirmButton: false,
                        timer: 2000
                    });
                } else if (url.includes("playlist")) {
                    Swal.fire({
                        title: 'Downloading your playlist',
                        text: 'Please wait while your playlist is being downloaded.',
                        icon: 'info',
                        showConfirmButton: false,
                        timer: 2000
                    });
                }

                const response = await fetch('/', {
                    method: 'POST',
                    body: JSON.stringify({ url }),
                    headers: { 'Content-Type': 'application/json' }
                });

                const data = await response.json();
                sessionId = data.session_id;
                downloadComplete = false;
            });

            setInterval(async () => {
                if (!sessionId || downloadComplete) return;

                const response = await fetch(`/output?session_id=${sessionId}`);
                const text = await response.text();
                output.value = text;

                const sizeResponse = await fetch(`/download-progress?session_id=${sessionId}`);
                const { percentage } = await sizeResponse.json();
                progressBar.style.width = percentage + '%';
                progressBar.textContent = percentage + '%';

                if (percentage === 100 && !downloadComplete) {
                    downloadComplete = true;
                    downloadBtn.style.display = 'block';
                    Swal.fire({
                        title: 'Download Complete!',
                        icon: 'success',
                        showConfirmButton: false,
                        timer: 2000
                    });
                }
            }, 1000);
            downloadBtn.addEventListener('click', () => {
                window.location.href = `/download/${sessionId}`;
            });
        </script>
    </body>
    </html>
    """

@app.route('/output', methods=['GET'])
def get_output():
    session_id = request.args.get('session_id')
    if not session_id or session_id not in download_states:
        return "No such session", 404
    return download_states[session_id]["output"]

@app.route('/download-progress', methods=['GET'])
def download_progress():
    session_id = request.args.get('session_id')
    if not session_id or session_id not in download_states:
        return jsonify({"error": "No such session"}), 404

    state = download_states[session_id]
    percentage = 0
    if state["num"] > 0:
        percentage = int((state["downloaded_size"] / state["num"]) * 100)
    return jsonify({"percentage": percentage})

@app.route('/download/<session_id>', methods=['GET'])
def download_zip(session_id):
    folder = f"./downloads/{session_id}/"
    if not os.path.exists(folder):
        return jsonify({"error": "No such session"}), 404

    zip_filename = f"./downloads/{session_id}.zip"
    with zipfile.ZipFile(zip_filename, 'w') as zf:
        for foldername, subfolders, filenames in os.walk(folder):
            for filename in filenames:
                zf.write(os.path.join(foldername, filename),
                         os.path.relpath(os.path.join(foldername, filename), folder))

    return send_file(zip_filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=6237)
