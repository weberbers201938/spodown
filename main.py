from flask import Flask, request, send_file, jsonify
import subprocess, json, time, os, zipfile, shutil
from threading import Thread
from sys import platform
import uuid
import signal

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
            "error": None,
            "process": None
        }

        process = subprocess.Popen(
            ["python3", '-m', 'spotdl', f'{url}', '--output', download_folder], 
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setsid)

        download_states[session_id]["process"] = process

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
                border-radius: 10 px;
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
            .progress {
                height: 30px;
                background-color: #e9ecef;
                border-radius: 5px;
                overflow: hidden;
                margin-top: 20px;
                display: none;
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
            .tracks-container {
                margin-top: 20px;
            }
            .track {
                padding: 10px;
                border-bottom: 1px solid #ccc;
            }
            .track:last-child {
                border-bottom: none;
            }
            .track-name {
                font-weight: bold;
            }
            .download-btn {
                background: linear-gradient(to right, #28a745, #218838);
                color: white;
                padding: 5px 10px;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                font-size: 14px;
            }
            .download-btn:hover {
                background: linear-gradient(to right, #218838, #28a745);
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
                <button type="submit" id="startDownloadBtn"><i class="fas fa-download"></i> Start Download</button>
                <button type="button" id="cancelDownloadBtn" style="display: none;">Cancel Download</button>
            </form>

            <div class="progress">
                <div class="progress-bar" id="progressBar">%</div>
            </div>

            <textarea id="output" readonly placeholder="Download output will appear here..."></textarea>

            <button id="seeAllTracksBtn" class="btn btn-primary" style="display: none;">
                See All Tracks
            </button>
        </div>

        <script>
            const form = document.getElementById('form');
            const output = document.getElementById('output');
            const progressBar = document.getElementById('progressBar');
            const downloadBtn = document.getElementById('downloadBtn');
            const seeAllTracksBtn = document.getElementById('seeAllTracksBtn');
            const startDownloadBtn = document.getElementById('startDownloadBtn');
            const cancelDownloadBtn = document.getElementById('cancelDownloadBtn');
            let sessionId = null;
            let downloadComplete = false;
            let tracks = [];

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

                progressBar.parentElement.style.display = 'block';
                startDownloadBtn.style.display = 'none';
                cancelDownloadBtn.style.display = 'block';

                const response = await fetch('/', {
                    method: 'POST',
                    body: JSON.stringify({ url }),
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });

                const data = await response.json();

                if (data.error) {
                    Swal.fire({
                        icon: 'error',
                        title: 'Download Error',
                        text: data.error,
                    });
                    progressBar.parentElement.style.display = 'none';
                    startDownloadBtn.style.display = 'block';
                    cancelDownloadBtn.style.display = 'none';
                    return;
                }

                sessionId = data.session_id;
                downloadComplete = false;
                checkProgress();
 });

            async function checkProgress() {
                if (downloadComplete) return;

                const response = await fetch(`/progress/${sessionId}`);
                const data = await response.json();

                if (data.error) {
                    output.value += `\nError: ${data.error}`;
                    return;
                }

                output.value = data.output;
                const progress = Math.floor((data.downloaded_size / data.download_size) * 100);
                progressBar.style.width = progress + '%';
                progressBar.innerText = progress + '%';

                if (progress < 100) {
                    setTimeout(checkProgress, 1000);
                } else {
                    downloadComplete = true;
                    Swal.fire({
                        icon: 'success',
                        title: 'Download Complete',
                        text: 'Your download has been completed!',
                    });
                    seeAllTracksBtn.style.display = 'block';
                    cancelDownloadBtn.style.display = 'none';
                    startDownloadBtn.style.display = 'block';
                }
            }

            cancelDownloadBtn.addEventListener('click', async () => {
                if (!sessionId) return;

                const response = await fetch(`/cancel/${sessionId}`, {
                    method: 'POST'
                });

                const data = await response.json();

                if (data.success) {
                    Swal.fire({
                        icon: 'success',
                        title: 'Download Canceled',
                        text: 'Your download has been successfully canceled.',
                    });
                    progressBar.style.width = '0%';
                    progressBar.innerText = '';
                    progressBar.parentElement.style.display = 'none';
                    startDownloadBtn.style.display = 'block';
                    cancelDownloadBtn.style.display = 'none';
                }
            });

            seeAllTracksBtn.addEventListener('click', async () => {
                const response = await fetch(`/tracks/${sessionId}`);
                const data = await response.json();

                if (data.error) {
                    Swal.fire({
                        icon: 'error',
                        title: 'Error',
                        text: 'Unable to retrieve tracks.',
                    });
                    return;
                }

                tracks = data.tracks;

                let htmlContent = '';
                tracks.forEach((track, index) => {
                    htmlContent += `
                        <div class="track">
                            <span class="track-name">${track}</span>
                            <button class="download-btn" onclick="downloadTrack('${track}')">Download</button>
                        </div>
                    `;
                });

                Swal.fire({
                    title: 'Downloaded Tracks',
                    html: htmlContent,
                    width: '600px',
                    showCancelButton: true
                });
            });

            async function downloadTrack(track) {
                const response = await fetch(`/download/${sessionId}/${track}`);
                const data = await response.blob();
                const url = window.URL.createObjectURL(data);
                const a = document.createElement('a');
                a.href = url;
                a.download = `${track}.mp3`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
            }
        </script>

    </body>
    </html>
    """

@app.route('/progress/<session_id>', methods=['GET'])
def progress(session_id):
    if session_id not in download_states:
        return jsonify({"error": "Invalid session ID"}), 404

    state = download_states[session_id]
    return jsonify({
        "output": state["output"].decode(),
        "download_size": state["num"],
        "downloaded_size": state["downloaded_size"]
    })

@app.route('/cancel/<session_id>', methods=['POST'])
def cancel(session_id):
    if session_id not in download_states:
        return jsonify({"error": "Invalid session ID"}), 404

    process = download_states[session_id]["process"]
    try:
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/tracks/<session_id>', methods=['GET'])
def tracks(session_id):
    if session_id not in download_states:
        return jsonify({"error": "Invalid session ID"}), 404

    folder = download_states[session_id]["folder"]
    try:
        files = [f for f in os.listdir(folder) if f.endswith(".mp3")]
        return jsonify({"tracks": files})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/download/<session_id>/<track>', methods=['GET'])
def download(session_id, track):
    if session_id not in download_states:
        return jsonify({"error": "Invalid session ID"}), 404

    folder = download_states[session_id]["folder"]
    file_path = os.path.join(folder, track)

    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        return jsonify({"error": "Track not found"}), 404


if __name__ == '__main__':
    if not os.path.exists("./downloads"):
        os.makedirs("./downloads")
    app.run(debug=True, host='0.0.0.0', port=3000)
