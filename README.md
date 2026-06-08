# USB Android Speaker - 物理链路免App无线音频投射工具

`USB Android Speaker` 是一款专为 Windows 电脑与 Android 手机设计的**低延迟、免安装手机客户端**的一键音频推流投射工具。

你可以将安卓手机用作 Windows 电脑的外置物理扬声器，音视频同步延迟最低可达 **20ms~40ms**，带来近乎零感的物理音频传输体验。

---

## 🌟 核心特性与架构设计

本项目基于**第一性原理**构建，拒绝任何需要用户手动下载与安装手机端 App 的繁琐体验，完全利用手机自带浏览器与底层网络隧道来实现极致的高效流转：

```
[Windows 电脑端]                                         [Android 手机端]
  +------------------+                                      +------------------+
  |  WASAPI Loopback |                                      |  系统默认浏览器  |
  | (抓取系统音频流) |                                      |                  |
  +--------+---------+                                      +--------+---------+
           |                                                         ^
           v                                                         |
  +--------+---------+                                      +--------+---------+
  |  Python 音频服务  |                                      |   Web Audio API  |
  | (WebSocket PCM)  |                                      | (PCM音频播放&防抖|
  +--------+---------+                                      +--------+---------+
           |                                                         ^
           |                                                         |
           +============[ ADB Reverse / USB 数据线 ]==================+
                     (物理调试隧道 127.0.0.1:8000 穿透防火墙)
```

1. **WASAPI Loopback 环回捕获**：
   通过 `PyAudioWPatch` 调用 Windows WASAPI 独占环回接口，直接抓取系统的活动扬声器/耳机音频输出流，没有常规麦克风录音的空腔回音，完美还原原生音质。
2. **ADB Reverse 物理隧道**：
   借助 `adb reverse tcp:8000 tcp:8000` 将手机端的本地回环端口倒灌映射到电脑端。数据传输完全走物理 USB 数据线，绕过 WiFi 物理隔离、公用局域网 AP 限制与 Windows 网络防火墙的拦截，连通率与抗干扰能力极强。
3. **免 App 轻量接收网页**：
   手机端无需安装任何额外 App，直接在系统浏览器中运行。使用现代 CSS 拟物磨砂玻璃界面（Glassmorphism），结合原生 Web Audio API，直接建立 WebSocket 连接拉取 PCM 裸流实时解码发声。
4. **多路由 IP 轮询自愈策略**：
   网页中动态注入了电脑端的所有可用网络 IP（回环隧道、USB 共享网关、WLAN IP 等）。客户端 JavaScript 会启动高频率轮询自愈，当默认的回环端口受部分自带浏览器安全沙箱限制时，会自动在一秒内重试备选链路，实现 100% 连接握手。
5. **智能自适应屏幕盲点**：
   利用 adb 智能读取手机物理屏幕分辨率，自动计算屏幕几何中心坐标，并在检测到 WebSocket 成功建连时，在后台发送屏幕 tap 动作，自动解锁安卓端浏览器对于 AudioContext 音频播放的 Autoplay Policy 自动播放拦截。

---

## 🚀 快速开始

### 前置准备

1. **电脑端**：
   - 准备一根可传输数据的 USB 数据线连接手机与电脑。
   - 电脑中已配置好 `adb` 环境变量（控制台运行 `adb devices` 能正常显示设备）。
   - 电脑已启用声音播放设备（如插有耳机或外设音箱，确保 WASAPI 环回驱动工作正常）。
2. **手机端**：
   - 手机已解锁并开启了**「USB 调试」**选项。
   - 电脑双击运行程序后，如果手机屏幕弹出“允许USB调试吗？”申请，请勾选“始终允许”并点击**确定**。

### 运行方式

#### 方式一：直接运行可执行程序（推荐）

直接双击桌面的 **`Android_Speaker.exe`**。
程序会全自动执行：
- 防火墙入站规则自检（如弹出 UAC 提权，请选择「是」允许放行 8000 端口）。
- ADB 连接与授权自动校验。
- 手机端浏览器自动调起，并在网页加载完成后由后台模拟点击屏幕中心，自动连接并发声。

#### 方式二：通过 Python 源码运行

1. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```
2. 运行脚本：
   ```bash
   python stream_audio.py
   ```

---

## 🛠️ 本地打包与构建

如果你对源码进行了二次开发，可以使用 PyInstaller 将脚本重新打包为 `.exe` 文件：

```bash
python -m PyInstaller --onefile --clean --noconfirm --distpath ./dist --name "Android_Speaker" --icon="icon.ico" "stream_audio.py"
```

---

## 🤖 GitHub Actions CI/CD 流水线

本项目已配置规范的 GitHub Action 流水线（`.github/workflows/build-executable.yml`），实现 CI/CD 自动化构建交付。

### 构建流程

每当你在分支中执行 `git push` 或者是发布 `release` 时，流水线将会：
1. 自动拉起 `windows-latest` 虚拟机环境。
2. 自动配置 Python 并利用 pip 还原依赖环境。
3. 运行 PyInstaller 重新打包，自动将最新的 `icon.ico` 嵌入 `.exe` 中。
4. 将编译好的 `Android_Speaker.exe` 上传并持久化为 GitHub Actions 产物（Artifacts），可以直接在 GitHub Commit 或 Actions 页面进行测试下载。
