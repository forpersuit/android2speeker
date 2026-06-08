import time
import socket
import hashlib
import base64
import threading
import subprocess
import re
import sys
import ctypes
import json
import xml.etree.ElementTree as ET
import pyaudiowpatch as pyaudio

PORT = 8000
CHUNK = 512
FORMAT = pyaudio.paInt16
CHANNELS = 2
RATE = 44100

SERVER_READY = False
SERVER_ERROR = None

def write_error_log(msg):
    try:
        with open("C:/Users/PC/Desktop/error_log.txt", "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
    except:
        pass

def get_websocket_handshake_response(key):
    guid = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
    sha1 = hashlib.sha1((key + guid).encode('utf-8')).digest()
    accept = base64.b64encode(sha1).decode('utf-8')
    response = (
        "HTTP/1.1 101 Switching Protocols\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Accept: {accept}\r\n\r\n"
    )
    return response.encode('utf-8')

def make_websocket_binary_frame(data):
    frame = bytearray()
    frame.append(0x82)  # FIN = 1, Opcode = 2
    length = len(data)
    if length < 126:
        frame.append(length)
    elif length < 65536:
        frame.append(126)
        frame.extend(length.to_bytes(2, 'big'))
    else:
        frame.append(127)
        frame.extend(length.to_bytes(8, 'big'))
    frame.extend(data)
    return bytes(frame)

HTML_PAGE = """<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>零延迟音频接收器</title>
    <style>
        body {
            background: radial-gradient(circle at center, #141529, #070814);
            color: #ffffff;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 100vh;
            margin: 0;
            overflow: hidden;
            user-select: none;
            -webkit-user-select: none;
        }
        .card {
            background: rgba(255, 255, 255, 0.03);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 32px;
            padding: 40px 30px;
            text-align: center;
            box-shadow: 0 20px 50px rgba(0, 0, 0, 0.5);
            max-width: 90%;
            width: 320px;
            box-sizing: border-box;
        }
        h1 {
            font-size: 22px;
            margin-top: 0;
            margin-bottom: 6px;
            background: linear-gradient(135deg, #00ffcc, #0072ff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: 700;
            letter-spacing: 0.5px;
        }
        p {
            color: #8c8caf;
            font-size: 13px;
            margin-bottom: 25px;
            line-height: 1.5;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .control-group {
            margin-bottom: 25px;
            background: rgba(255, 255, 255, 0.02);
            padding: 16px;
            border-radius: 18px;
            border: 1px solid rgba(255, 255, 255, 0.04);
        }
        .control-label {
            display: flex;
            justify-content: space-between;
            font-size: 11px;
            color: #8c8caf;
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .slider {
            width: 100%;
            -webkit-appearance: none;
            background: rgba(255, 255, 255, 0.08);
            outline: none;
            border-radius: 4px;
            height: 6px;
        }
        .slider::-webkit-slider-thumb {
            -webkit-appearance: none;
            width: 18px;
            height: 18px;
            border-radius: 50%;
            background: #00ffcc;
            cursor: pointer;
            box-shadow: 0 0 10px rgba(0, 255, 204, 0.6);
            transition: transform 0.1s ease;
        }
        .slider::-webkit-slider-thumb:active {
            transform: scale(1.2);
        }
        .play-btn {
            background: linear-gradient(135deg, #00ffcc, #0072ff);
            border: none;
            color: #0f0f15;
            padding: 16px 20px;
            font-size: 16px;
            font-weight: bold;
            border-radius: 20px;
            cursor: pointer;
            box-shadow: 0 4px 20px rgba(0, 255, 204, 0.25);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            outline: none;
            width: 100%;
        }
        .play-btn:active {
            transform: scale(0.96);
        }
        .playing {
            background: linear-gradient(135deg, #f857a6, #ff5858);
            color: #ffffff;
            box-shadow: 0 4px 20px rgba(248, 87, 166, 0.3);
        }
        .visualizer {
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 6px;
            margin-top: 25px;
            height: 35px;
        }
        .bar {
            width: 4px;
            height: 6px;
            background: #00ffcc;
            border-radius: 2px;
            animation: bounce 0.8s infinite ease-in-out;
            animation-play-state: paused;
            transition: background 0.3s;
        }
        .bar:nth-child(2) { animation-delay: 0.1s; background: #00d2ff; }
        .bar:nth-child(3) { animation-delay: 0.2s; background: #0072ff; }
        .bar:nth-child(4) { animation-delay: 0.3s; background: #7f00ff; }
        .bar:nth-child(5) { animation-delay: 0.4s; background: #ff007b; }
        @keyframes bounce {
            0%, 100% { height: 6px; }
            50% { height: 30px; }
        }
        .status-dot {
            display: inline-block;
            width: 8px;
            height: 8px;
            background-color: #ff3b30;
            border-radius: 50%;
            margin-right: 8px;
            transition: background-color 0.3s, box-shadow 0.3s;
        }
        .connected {
            background-color: #4cd964;
            box-shadow: 0 0 10px #4cd964;
        }
        .connecting {
            background-color: #ffcc00;
            box-shadow: 0 0 10px #ffcc00;
        }
    </style>
</head>
<body>
    <div class="card">
        <h1>零延迟无线扬声器</h1>
        <p>
            <span class="status-dot" id="dot"></span>
            <span id="status-text">正在初始化...</span>
        </p>
        
        <div class="control-group">
            <div class="control-label">
                <span>防抖缓冲延迟</span>
                <span id="delay-val">40ms</span>
            </div>
            <input type="range" min="15" max="200" value="40" class="slider" id="delay-slider" oninput="updateDelay(this.value)">
            <div style="font-size: 11px; color: #8c8caf; margin-top: 10px; display: flex; justify-content: space-between;">
                <span>传输链路延迟:</span>
                <span id="realtime-latency" style="color: #00ffcc; font-weight: bold;">0ms</span>
            </div>
        </div>

        <button id="btn" class="play-btn" onclick="togglePlay()">点此开启实时声音</button>
        
        <div class="visualizer" id="vis">
            <div class="bar"></div>
            <div class="bar"></div>
            <div class="bar"></div>
            <div class="bar"></div>
            <div class="bar"></div>
        </div>
    </div>
    <script>
        const computerIps = {{COMPUTER_IPS}}; // 后端动态注入的物理 IP 列表
        let wsUrlIndex = 0;
        
        let audioCtx = null;
        let ws = null;
        let nextPlayTime = 0;
        let bufferDelay = 0.04;
        let shouldReconnect = true;
        let reconnectTimer = null;

        function updateDelay(val) {
            document.getElementById('delay-val').textContent = val + 'ms';
            bufferDelay = val / 1000.0;
        }

        const unlockAudio = () => {
            if (audioCtx && audioCtx.state === 'suspended') {
                audioCtx.resume();
            }
        };
        document.body.addEventListener('click', unlockAudio);
        document.body.addEventListener('touchstart', unlockAudio);

        function initAudioCtx() {
            if (!audioCtx) {
                try {
                    audioCtx = new (window.AudioContext || window.webkitAudioContext)({
                        latencyHint: 'interactive'
                    });
                } catch (e) {
                    try {
                        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                    } catch (err) {
                        console.error("Web Audio API not supported", err);
                    }
                }
            }
            nextPlayTime = 0;
        }

        function togglePlay(isAuto = false) {
            const btn = document.getElementById('btn');
            const dot = document.getElementById('dot');
            const statusText = document.getElementById('status-text');
            const bars = document.querySelectorAll('.bar');

            if (!ws) {
                if (isAuto) {
                    shouldReconnect = true;
                }
                initAudioCtx();
                
                // 轮询尝试可用 IP
                const targetIp = computerIps[wsUrlIndex];
                const wsUrl = "ws://" + targetIp + ":8000/ws";
                
                dot.className = 'status-dot connecting';
                statusText.textContent = '连接中 (' + targetIp + ')...';
                
                ws = new WebSocket(wsUrl);
                ws.binaryType = 'arraybuffer';

                ws.onopen = () => {
                    dot.className = 'status-dot connected';
                    statusText.textContent = '已连接：实时零延时推送中';
                    btn.textContent = '暂停播放';
                    btn.classList.add('playing');
                    bars.forEach(b => b.style.animationPlayState = 'running');
                    nextPlayTime = 0;
                    if (audioCtx && audioCtx.state === 'suspended') {
                        audioCtx.resume();
                    }
                };

                ws.onmessage = (event) => {
                    playAudioChunk(event.data);
                };

                ws.onclose = () => {
                    cleanup();
                    if (shouldReconnect) {
                        // 连不上则快速切换到下一个 IP 路由进行自愈重连
                        wsUrlIndex = (wsUrlIndex + 1) % computerIps.length;
                        dot.className = 'status-dot';
                        statusText.textContent = '连接已断开，尝试备用链路...';
                        if (!reconnectTimer) {
                            reconnectTimer = setTimeout(() => {
                                reconnectTimer = null;
                                togglePlay(true);
                            }, 1000);
                        }
                    }
                };

                ws.onerror = () => {
                    cleanup();
                };
            } else {
                shouldReconnect = false;
                if (reconnectTimer) {
                    clearTimeout(reconnectTimer);
                    reconnectTimer = null;
                }
                cleanup();
            }
        }

        function cleanup() {
            const btn = document.getElementById('btn');
            const dot = document.getElementById('dot');
            const statusText = document.getElementById('status-text');
            const bars = document.querySelectorAll('.bar');

            if (ws) {
                try { ws.close(); } catch(e) {}
                ws = null;
            }
            dot.className = 'status-dot';
            statusText.textContent = '已断开';
            btn.textContent = '点此开启实时声音';
            btn.classList.remove('playing');
            bars.forEach(b => b.style.animationPlayState = 'paused');
        }

        function playAudioChunk(arrayBuffer) {
            if (!audioCtx) return;
            
            const sampleRate = {{SAMPLE_RATE}};
            const channels = {{CHANNELS}};
            
            const int16Array = new Int16Array(arrayBuffer);
            if (int16Array.length === 0) return;
            const numSamples = int16Array.length / channels;
            
            const currentTime = audioCtx.currentTime;
            const currentLatency = (nextPlayTime < currentTime) ? bufferDelay : (nextPlayTime - currentTime);
            document.getElementById('realtime-latency').textContent = Math.round(currentLatency * 1000) + 'ms';
            
            if (currentLatency > bufferDelay + 0.06) {
                return;
            }
            
            const audioBuffer = audioCtx.createBuffer(channels, numSamples, sampleRate);
            const leftChannel = audioBuffer.getChannelData(0);
            const rightChannel = audioBuffer.getChannelData(1);
            
            for (let i = 0; i < numSamples; i++) {
                leftChannel[i] = int16Array[i * 2] / 32768.0;
                rightChannel[i] = int16Array[i * 2 + 1] / 32768.0;
            }
            
            const source = audioCtx.createBufferSource();
            source.buffer = audioBuffer;
            source.connect(audioCtx.destination);
            
            if (nextPlayTime < currentTime) {
                nextPlayTime = currentTime + bufferDelay;
            }
            
            source.start(nextPlayTime);
            nextPlayTime += audioBuffer.duration;
        }
        
        window.addEventListener('DOMContentLoaded', () => {
            togglePlay(true);
        });
    </script>
</body>
</html>
"""

def get_loopback_device_info(p):
    wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
    default_speakers = p.get_device_info_by_index(wasapi_info["defaultOutputDevice"])
    
    device_index = None
    if not default_speakers["isLoopbackDevice"]:
        for loopback in p.get_loopback_device_info_generator():
            if default_speakers["name"] in loopback["name"]:
                device_index = loopback["index"]
                break
    else:
        device_index = default_speakers["index"]
    
    if device_index is None:
        for loopback in p.get_loopback_device_info_generator():
            device_index = loopback["index"]
            break
            
    if device_index is None:
        raise Exception("未找到 WASAPI 环回声卡设备，请确认系统音频输出正常")
        
    dev_info = p.get_device_info_by_index(device_index)
    rate = int(dev_info.get("defaultSampleRate", 44100))
    channels = int(dev_info.get("maxInputChannels", 2))
    if channels > 2:
        channels = 2
        
    return device_index, rate, channels

# 全局单例初始化
GLOBAL_P = None
DEVICE_INDEX = None
SAMPLE_RATE = 44100
CHANNELS = 2

def get_all_local_ips():
    ips = ["127.0.0.1"]
    # 优先获取当前电脑所有的物理网卡 IP
    try:
        hostname = socket.gethostname()
        for ip in socket.gethostbyname_ex(hostname)[2]:
            if not ip.startswith("127.") and not ip.startswith("169.254."):
                if ip not in ips:
                    ips.append(ip)
    except Exception:
        pass
        
    # 通过 ipconfig 补充
    try:
        out = subprocess.check_output("ipconfig", shell=True, text=True, encoding="gbk", errors="ignore")
        found = re.findall(r"IPv4 地址[\.\s]*: (\d+\.\d+\.\d+\.\d+)", out)
        for ip in found:
            if not ip.startswith("127.") and not ip.startswith("169.254."):
                if ip not in ips:
                    ips.append(ip)
    except Exception:
        pass
    return ips

def fix_firewall_rules():
    print("[Firewall] [Step 0.5] Checking Windows firewall inbound settings...")
    try:
        res = subprocess.run(
            ["powershell", "-Command", "Get-NetFirewallRule | Where-Object { $_.DisplayName -eq 'android_speaker.exe' -and $_.Action -eq 'Block' }"],
            capture_output=True, text=True, encoding="gbk", errors="ignore"
        )
        has_block_rule = len(res.stdout.strip()) > 0
        
        res_port = subprocess.run(
            ["powershell", "-Command", "Get-NetFirewallRule | Where-Object { $_.DisplayName -eq 'Android2Speaker_Port_8000' }"],
            capture_output=True, text=True, encoding="gbk", errors="ignore"
        )
        has_allow_port_rule = len(res_port.stdout.strip()) > 0
        
        if has_block_rule or not has_allow_port_rule:
            print("[INFO] Firewall block detected or allow rule missing. Requesting Admin privilege to heal...")
            ps_cmd = (
                "Set-NetFirewallRule -DisplayName 'android_speaker.exe' -Action Allow -ErrorAction SilentlyContinue; "
                "New-NetFirewallRule -DisplayName 'Android2Speaker_Port_8000' -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8000 -ErrorAction SilentlyContinue"
            )
            ret = ctypes.windll.shell32.ShellExecuteW(
                None, 
                "runas", 
                "powershell.exe", 
                f"-Command \"{ps_cmd}\"", 
                None, 
                0
            )
            if int(ret) > 32:
                print("[OK] Firewall update command sent successfully!")
                print("[INFO] Please click 'Yes' on the User Account Control (UAC) prompt to apply!")
                time.sleep(3)
            else:
                print("[WARN] Admin request denied. Please manually allow inbound connections for port 8000.")
        else:
            print("[OK] Firewall rules check passed.")
    except Exception as e:
        write_error_log(f"Firewall heal exception: {e}")
        print(f"[WARN] Firewall tool exception: {e}")

def handle_client(client_socket, client_address):
    try:
        client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        request_data = client_socket.recv(2048).decode('utf-8', errors='ignore')
        if not request_data:
            return
        
        if "Upgrade: websocket" in request_data:
            key = None
            for line in request_data.split("\r\n"):
                if line.startswith("Sec-WebSocket-Key:"):
                    key = line.split(":")[1].strip()
                    break
            
            if key:
                handshake_resp = get_websocket_handshake_response(key)
                client_socket.sendall(handshake_resp)
                stream_audio_to_socket(client_socket)
            else:
                client_socket.sendall(b"HTTP/1.1 400 Bad Request\r\n\r\n")
        else:
            # 动态获取本机 IP 列表注入 HTML 页面
            local_ips = get_all_local_ips()
            dynamic_html = HTML_PAGE.replace("{{SAMPLE_RATE}}", str(SAMPLE_RATE)).replace("{{CHANNELS}}", str(CHANNELS)).replace("{{COMPUTER_IPS}}", json.dumps(local_ips))
            
            # 使用 No-Cache 强制清空浏览器端网页缓存，保证最新 JS 载入
            response = (
                "HTTP/1.1 200 OK\r\n"
                "Content-Type: text/html; charset=utf-8\r\n"
                f"Content-Length: {len(dynamic_html.encode('utf-8'))}\r\n"
                "Cache-Control: no-cache, no-store, must-revalidate\r\n"
                "Pragma: no-cache\r\n"
                "Expires: 0\r\n"
                "Connection: close\r\n\r\n"
                + dynamic_html
            )
            client_socket.sendall(response.encode('utf-8'))
    except Exception as e:
        write_error_log(f"handle_client exception: {e}")
    finally:
        try:
            client_socket.close()
        except:
            pass

def stream_audio_to_socket(ws_socket):
    stream = None
    try:
        if GLOBAL_P is None or DEVICE_INDEX is None:
            write_error_log("Soundcard not initialized")
            return

        stream = GLOBAL_P.open(format=FORMAT,
                               channels=CHANNELS,
                               rate=SAMPLE_RATE,
                               input=True,
                               input_device_index=DEVICE_INDEX,
                               frames_per_buffer=CHUNK)

        while True:
            data = stream.read(CHUNK, exception_on_overflow=False)
            frame = make_websocket_binary_frame(data)
            ws_socket.sendall(frame)
    except socket.error as e:
        pass
    except Exception as e:
        write_error_log(f"Audio stream loop crash: {e}")
    finally:
        if stream:
            try:
                if stream.is_active():
                    stream.stop_stream()
                stream.close()
            except:
                pass

def run_server():
    global SERVER_READY, SERVER_ERROR
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server.bind(('0.0.0.0', PORT))
    except Exception as e:
        SERVER_ERROR = e
        write_error_log(f"Port 8000 bind failed: {e}")
        return
        
    SERVER_READY = True
    server.listen(5)
    try:
        while True:
            client_socket, client_address = server.accept()
            t = threading.Thread(target=handle_client, args=(client_socket, client_address))
            t.daemon = True
            t.start()
    except Exception as e:
        pass
    finally:
        server.close()

def get_usb_tethering_ip():
    try:
        out = subprocess.check_output("ipconfig", shell=True, text=True, encoding="gbk", errors="ignore")
        ips = re.findall(r"IPv4 地址[\.\s]*: (192\.168\.42\.\d+)", out)
        if ips:
            return ips[0]
            
        all_192_ips = re.findall(r"IPv4 地址[\.\s]*: (192\.168\.\d+\.\d+)", out)
        for ip in all_192_ips:
            if not re.match(r"192\.168\.(0|1|31)\.", ip):
                return ip
    except Exception:
        pass
    return None

def check_adb_and_setup_reverse():
    print("[Detect] [Step 1/2] Detecting Android ADB connection and authorization...")
    try:
        res = subprocess.run(["adb", "devices"], capture_output=True, text=True, check=True)
        lines = res.stdout.strip().split("\n")
        device_lines = [line for line in lines[1:] if line.strip()]
        
        if not device_lines:
            print("[ERROR] No connected Android devices detected!")
            print("[INFO] Please verify:")
            print("   1. USB cable is securely connected to the PC.")
            print("   2. 'USB Debugging' is enabled in the Developer options.")
            return False, None
            
        device_info = device_lines[0].split()
        device_id = device_info[0]
        device_status = device_info[1]
        
        if device_status == "unauthorized":
            print("[WARN] Device status is [Unauthorized]!")
            print("[INFO] Unlock phone, check screen prompt, tick 'Always allow' and click 'OK'!")
            print("[WAIT] Waiting for authorization...")
            for _ in range(15):
                time.sleep(2)
                check_res = subprocess.run(["adb", "devices"], capture_output=True, text=True)
                if f"{device_id}\tdevice" in check_res.stdout:
                    print("[OK] Authorized successfully!")
                    device_status = "device"
                    break
            if device_status == "unauthorized":
                print("[ERROR] Authorization timeout! Please replug the USB cable.")
                return False, None
                
        if device_status == "device":
            print(f"[OK] Phone connected successfully (ID: {device_id}).")
            # 建立物理 adb 端口倒灌映射，将手机端的 8000 转发至电脑的 8000
            subprocess.run(["adb", "reverse", "tcp:8000", "tcp:8000"], capture_output=True)
            return True, device_id
            
        print(f"[ERROR] ADB device status error: {device_status}")
        return False, None
    except FileNotFoundError:
        print("[ERROR] ADB not found in system PATH. Please check configuration.")
        return False, None

def get_screen_center():
    try:
        res = subprocess.run(["adb", "shell", "wm", "size"], capture_output=True, text=True)
        match = re.search(r"Physical size:\s*(\d+)x(\d+)", res.stdout)
        if match:
            w = int(match.group(1))
            h = int(match.group(2))
            return w // 2, h // 2
    except Exception:
        pass
    return 360, 600

def auto_connect_phone():
    success, device_id = check_adb_and_setup_reverse()
    if not success or not device_id:
        return False
        
    # 默认通过最稳定、免疫防火墙的 ADB 本地回环进行拉起
    url = f"http://127.0.0.1:8000/?t={int(time.time())}"
    print(f"[Phone] [Step 2/2] Requesting phone browser to load: {url}")
    
    # 自动拉起
    subprocess.run(["adb", "shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", url], capture_output=True)
    
    print("[WAIT] Waiting for WebSocket connection and dynamic clicking validation...")
    connected = False
    for i in range(8):
        time.sleep(1.2)
        net_res = subprocess.run("netstat -ano | findstr :8000", shell=True, capture_output=True, text=True)
        if "ESTABLISHED" in net_res.stdout:
            connected = True
            cx, cy = get_screen_center()
            subprocess.run(["adb", "shell", "input", "tap", str(cx), str(cy)], capture_output=True)
            break
            
        cx, cy = get_screen_center()
        subprocess.run(["adb", "shell", "input", "tap", str(cx), str(cy)], capture_output=True)
        
    if connected:
        print("\n=======================================================")
        print("      [OK] USB Android Speaker Connected Successfully!")
        print("      Play any audio on PC, phone will speaker it out.")
        print("=======================================================\n")
        return True
    else:
        print("\n[WARN] Failed to establish WebSocket connection in time.")
        print("[INFO] Please verify:")
        print("   1. Mobile screen is unlocked.")
        print("   2. Allowed web browser network/audio permissions.")
        return False

if __name__ == '__main__':
    print("=======================================================")
    print("    [USB Android Speaker] 一键物理链路音频传输工具")
    print("=======================================================")
    
    # 0. 防火墙自愈检测
    fix_firewall_rules()
    
    # 0.6. 全局声卡初始化
    try:
        GLOBAL_P = pyaudio.PyAudio()
        DEVICE_INDEX, SAMPLE_RATE, CHANNELS = get_loopback_device_info(GLOBAL_P)
        write_error_log(f"Global soundcard initialized: index={DEVICE_INDEX}, rate={SAMPLE_RATE}, channels={CHANNELS}")
        print(f"[OK] WASAPI Loopback soundcard connected (Rate: {SAMPLE_RATE}Hz, Channels: {CHANNELS})")
    except Exception as e:
        write_error_log(f"Soundcard init error: {e}")
        print(f"[ERROR] Soundcard initialization failed: {e}")
        print("[INFO] Please connect your headphones or speakers on PC, and verify Windows sound works.")
        print("Press Enter to exit...")
        input()
        sys.exit(1)

    # 1. 启动音频服务器
    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()
    time.sleep(1.0)
    
    if SERVER_ERROR:
        print(f"[ERROR] Server boot failed: port 8000 is occupied. Detail: {SERVER_ERROR}")
        print("[INFO] Please terminate duplicate Python/Android_Speaker processes from Task Manager.")
        print("Press Enter to exit...")
        input()
        sys.exit(1)
        
    # 检测 USB 网络共享 IP (只做温和的背景诊断提示，不再强求或阻塞，因为 127.0.0.1 也能 100% 成功工作)
    usb_ip = get_usb_tethering_ip()
    if usb_ip:
        print(f"[INFO] USB network tethering is active (IP: {usb_ip}).")
    else:
        print("[INFO] USB network sharing is not active. Will run via ADB debug loopback (127.0.0.1).")
        # 顺便静默拉起设置菜单方便用户如果想开启
        subprocess.run(["adb", "shell", "am", "start", "-n", "com.android.settings/.TetherSettings"], capture_output=True)

    # 2. 循环建立物理投音握手
    while True:
        success = auto_connect_phone()
        if success:
            break
        print("\n[Retry] Connection incomplete. Keep running in background.")
        print("Press [Enter] to re-trigger phone browser launch, or [Ctrl+C] to abort.")
        try:
            input()
        except KeyboardInterrupt:
            print("[Exit] Cleaning up services and exiting...")
            sys.exit(0)
    
    print("=======================================================")
    print("[INFO] Active. Press [Enter] key in this window to close server and exit.")
    print("=======================================================")
    try:
        input()
    except KeyboardInterrupt:
        pass
    print("[Exit] Closing services and cleaning up...")
