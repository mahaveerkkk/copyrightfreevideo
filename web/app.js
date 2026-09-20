document.addEventListener("DOMContentLoaded", async () => {
    // Elements
    const dropZone = document.getElementById("dropZone");
    const fileInput = document.getElementById("fileInput");
    const dropPrompt = document.getElementById("dropPrompt");
    const selectedPreview = document.getElementById("selectedPreview");
    const sourceVideoPlayer = document.getElementById("sourceVideoPlayer");
    const fileNameLabel = document.getElementById("fileNameLabel");
    const fileSizeLabel = document.getElementById("fileSizeLabel");
    const changeFileBtn = document.getElementById("changeFileBtn");

    const modeTurboCard = document.getElementById("modeTurboCard");
    const modeDeepCard = document.getElementById("modeDeepCard");
    const aiConfigPanel = document.getElementById("aiConfigPanel");
    const vocalSwapToggle = document.getElementById("vocalSwapToggle");
    const splitScreenToggle = document.getElementById("splitScreenToggle");
    const bgmChoice = document.getElementById("bgmChoice");

    const presetsContainer = document.getElementById("presetsContainer");
    const startBtn = document.getElementById("startBtn");
    const startBtnLabel = document.getElementById("startBtnLabel");

    const configCard = document.getElementById("configCard");
    const progressCard = document.getElementById("progressCard");
    const processingView = document.getElementById("processingView");
    const completedView = document.getElementById("completedView");

    const mainStatusText = document.getElementById("mainStatusText");
    const subStatusText = document.getElementById("subStatusText");
    const progressBar = document.getElementById("progressBar");
    const progressPercentLabel = document.getElementById("progressPercentLabel");
    const terminalOutput = document.getElementById("terminalOutput");

    // Output Player Elements
    const tabSinglePlayer = document.getElementById("tabSinglePlayer");
    const tabDualPlayer = document.getElementById("tabDualPlayer");
    const singlePlayerBox = document.getElementById("singlePlayerBox");
    const dualPlayerBox = document.getElementById("dualPlayerBox");
    const finalVideoPlayer = document.getElementById("finalVideoPlayer");
    const rawVideoPlayer = document.getElementById("rawVideoPlayer");
    const dualCleanPlayer = document.getElementById("dualCleanPlayer");
    const downloadSafeBtn = document.getElementById("downloadSafeBtn");
    const restartBtn = document.getElementById("restartBtn");

    // Input Source Tabs & YouTube Elements
    const tabUploadMode = document.getElementById("tabUploadMode");
    const tabYoutubeMode = document.getElementById("tabYoutubeMode");
    const youtubeZone = document.getElementById("youtubeZone");
    const ytUrlInput = document.getElementById("ytUrlInput");
    const fetchYtBtn = document.getElementById("fetchYtBtn");
    const fetchBtnSpinner = document.getElementById("fetchBtnSpinner");
    const fetchBtnText = document.getElementById("fetchBtnText");

    const ytDetailsCard = document.getElementById("ytDetailsCard");
    const ytThumbImg = document.getElementById("ytThumbImg");
    const ytTitleText = document.getElementById("ytTitleText");
    const ytAuthorText = document.getElementById("ytAuthorText");
    const ytDurationBadge = document.getElementById("ytDurationBadge");

    const clipDurationLabel = document.getElementById("clipDurationLabel");
    const trimStartInput = document.getElementById("trimStartInput");
    const trimEndInput = document.getElementById("trimEndInput");
    const btnFullVideo = document.getElementById("btnFullVideo");
    const sliderStart = document.getElementById("sliderStart");
    const sliderEnd = document.getElementById("sliderEnd");

    let currentInputMode = "upload"; // 'upload' or 'youtube'
    let ytVideoData = null; // { title, duration, thumbnail, author, url }
    let trimRange = { start: 0, end: 0 };

    let selectedFile = null;
    let activeMode = "turbo";
    let selectedPreset = "stealth_deep";
    let activeEventSource = null;

    // Helper functions for time formatting
    function secondsToMMSS(sec) {
        const m = Math.floor(sec / 60);
        const s = Math.floor(sec % 60);
        return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
    }

    function mmssToSeconds(str) {
        const parts = str.trim().split(":");
        if (parts.length === 2) {
            const m = parseFloat(parts[0]) || 0;
            const s = parseFloat(parts[1]) || 0;
            return Math.max(0, m * 60 + s);
        }
        return parseFloat(str) || 0;
    }

    function updateClipDurationBadge() {
        const len = Math.max(0, trimRange.end - trimRange.start);
        clipDurationLabel.innerText = `Selected: ${secondsToMMSS(len)} (${Math.round(len)}s)`;
    }

    // Tab Switching: Local File vs YouTube
    tabUploadMode.addEventListener("click", () => {
        currentInputMode = "upload";
        tabUploadMode.classList.add("active");
        tabYoutubeMode.classList.remove("active");
        dropZone.style.display = "block";
        youtubeZone.style.display = "none";
        updateButtonLabel();
    });

    tabYoutubeMode.addEventListener("click", () => {
        currentInputMode = "youtube";
        tabYoutubeMode.classList.add("active");
        tabUploadMode.classList.remove("active");
        dropZone.style.display = "none";
        youtubeZone.style.display = "block";
        updateButtonLabel();
    });

    // Fetch YouTube Video Info
    fetchYtBtn.addEventListener("click", async () => {
        const url = ytUrlInput.value.trim();
        if (!url) {
            alert("Please paste a valid YouTube video or Shorts link");
            return;
        }

        fetchBtnSpinner.style.display = "inline-block";
        fetchBtnText.innerText = "Fetching...";
        fetchYtBtn.disabled = true;

        try {
            const form = new FormData();
            form.append("url", url);
            const res = await fetch("/api/youtube/info", {
                method: "POST",
                body: form
            });

            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || "Failed to fetch YouTube video info");
            }

            const data = await res.json();
            ytVideoData = { ...data, url: url };

            // Update UI
            ytThumbImg.src = data.thumbnail || "";
            ytTitleText.innerText = data.title;
            ytAuthorText.innerText = data.channel;
            ytDurationBadge.innerText = data.duration_str || secondsToMMSS(data.duration);

            // Initialize Trimmer
            const totalSec = Math.max(5, Math.round(data.duration));
            trimRange.start = 0;
            trimRange.end = totalSec;

            sliderStart.max = totalSec;
            sliderEnd.max = totalSec;
            sliderStart.value = 0;
            sliderEnd.value = totalSec;

            trimStartInput.value = "00:00";
            trimEndInput.value = secondsToMMSS(totalSec);
            updateClipDurationBadge();

            ytDetailsCard.style.display = "block";
            updateButtonLabel();

        } catch (err) {
            alert(`YouTube Error: ${err.message}`);
        } finally {
            fetchBtnSpinner.style.display = "none";
            fetchBtnText.innerText = "Fetch Video";
            fetchYtBtn.disabled = false;
        }
    });

    // Trimmer Sliders & Inputs sync
    sliderStart.addEventListener("input", () => {
        let val = parseFloat(sliderStart.value);
        if (val >= trimRange.end) {
            val = Math.max(0, trimRange.end - 1);
            sliderStart.value = val;
        }
        trimRange.start = val;
        trimStartInput.value = secondsToMMSS(val);
        updateClipDurationBadge();
    });

    sliderEnd.addEventListener("input", () => {
        let val = parseFloat(sliderEnd.value);
        if (val <= trimRange.start) {
            val = Math.min(parseFloat(sliderEnd.max), trimRange.start + 1);
            sliderEnd.value = val;
        }
        trimRange.end = val;
        trimEndInput.value = secondsToMMSS(val);
        updateClipDurationBadge();
    });

    trimStartInput.addEventListener("change", () => {
        let sec = mmssToSeconds(trimStartInput.value);
        sec = Math.min(sec, trimRange.end - 1);
        trimRange.start = Math.max(0, sec);
        sliderStart.value = trimRange.start;
        trimStartInput.value = secondsToMMSS(trimRange.start);
        updateClipDurationBadge();
    });

    trimEndInput.addEventListener("change", () => {
        let sec = mmssToSeconds(trimEndInput.value);
        const maxSec = parseFloat(sliderEnd.max);
        sec = Math.min(maxSec, Math.max(trimRange.start + 1, sec));
        trimRange.end = sec;
        sliderEnd.value = trimRange.end;
        trimEndInput.value = secondsToMMSS(trimRange.end);
        updateClipDurationBadge();
    });

    btnFullVideo.addEventListener("click", () => {
        if (!ytVideoData) return;
        trimRange.start = 0;
        trimRange.end = ytVideoData.duration;
        sliderStart.value = 0;
        sliderEnd.value = ytVideoData.duration;
        trimStartInput.value = "00:00";
        trimEndInput.value = secondsToMMSS(ytVideoData.duration);
        updateClipDurationBadge();
    });

    // 1. Load Presets
    try {
        const res = await fetch("/api/presets");
        const presets = await res.json();
        presetsContainer.innerHTML = "";

        presets.forEach(p => {
            const card = document.createElement("div");
            card.className = `preset-pill-card ${p.id === selectedPreset ? "active" : ""}`;
            card.dataset.id = p.id;
            card.innerHTML = `
                <div class="preset-pill-name">${p.name}</div>
                <div class="preset-pill-desc">${p.description}</div>
            `;
            card.addEventListener("click", () => {
                document.querySelectorAll(".preset-pill-card").forEach(c => c.classList.remove("active"));
                card.classList.add("active");
                selectedPreset = p.id;
            });
            presetsContainer.appendChild(card);
        });
    } catch (err) {
        console.error("Failed to load presets", err);
    }

    // 2. Mode Toggle
    modeTurboCard.addEventListener("click", () => {
        modeTurboCard.classList.add("active");
        modeDeepCard.classList.remove("active");
        activeMode = "turbo";
        aiConfigPanel.style.display = "none";
        updateButtonLabel();
    });

    modeDeepCard.addEventListener("click", () => {
        modeDeepCard.classList.add("active");
        modeTurboCard.classList.remove("active");
        activeMode = "ai_deep";
        aiConfigPanel.style.display = "block";
        updateButtonLabel();
    });

    function updateButtonLabel() {
        const hasMedia = (currentInputMode === "upload" && selectedFile) || (currentInputMode === "youtube" && ytVideoData);
        if (!hasMedia) {
            startBtnLabel.innerText = currentInputMode === "upload" ? "Select a Video to Begin" : "Fetch a YouTube Video to Begin";
            startBtn.disabled = true;
        } else {
            startBtnLabel.innerText = activeMode === "turbo" ? "⚡ Remove Copyright (Turbo 5s)" : "🧠 Run AI Deep Studio Transformation";
            startBtn.disabled = false;
        }
    }

    // 3. File Selection & Drag Drop
    dropZone.addEventListener("click", (e) => {
        if (e.target !== changeFileBtn) {
            fileInput.click();
        }
    });

    changeFileBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        fileInput.click();
    });

    fileInput.addEventListener("change", (e) => {
        if (e.target.files.length > 0) {
            handleSelectedFile(e.target.files[0]);
        }
    });

    ["dragenter", "dragover"].forEach(evt => {
        dropZone.addEventListener(evt, (e) => {
            e.preventDefault();
            dropZone.classList.add("dragover");
        });
    });

    ["dragleave", "drop"].forEach(evt => {
        dropZone.addEventListener(evt, (e) => {
            e.preventDefault();
            dropZone.classList.remove("dragover");
        });
    });

    dropZone.addEventListener("drop", (e) => {
        if (e.dataTransfer.files.length > 0) {
            handleSelectedFile(e.dataTransfer.files[0]);
        }
    });

    function handleSelectedFile(file) {
        selectedFile = file;
        fileNameLabel.innerText = file.name;
        const sizeMb = (file.size / (1024 * 1024)).toFixed(1);
        fileSizeLabel.innerText = `${sizeMb} MB`;

        // Show Video Preview
        sourceVideoPlayer.src = URL.createObjectURL(file);
        dropPrompt.style.display = "none";
        selectedPreview.style.display = "flex";

        updateButtonLabel();
    }

    // 2.5 One-Tap Defense Arsenal Interactive Toggles
    const toolMirrorCard = document.getElementById("toolMirrorCard");
    const toolBorderCard = document.getElementById("toolBorderCard");
    const toolSpeedCard = document.getElementById("toolSpeedCard");
    const toolAudioCard = document.getElementById("toolAudioCard");

    const arsenalState = {
        mirror_flip: true,
        border_frame: true,
        speed_ramp: true,
        audio_pitch: true
    };

    function setupArsenalToggle(card, key) {
        if (!card) return;
        card.addEventListener("click", () => {
            arsenalState[key] = !arsenalState[key];
            card.classList.toggle("active", arsenalState[key]);
            const statusEl = card.querySelector(".arsenal-status");
            if (statusEl) {
                statusEl.innerText = arsenalState[key] ? "ON" : "OFF";
                statusEl.className = `arsenal-status ${arsenalState[key] ? "on" : "off"}`;
            }
        });
    }

    setupArsenalToggle(toolMirrorCard, "mirror_flip");
    setupArsenalToggle(toolBorderCard, "border_frame");
    setupArsenalToggle(toolSpeedCard, "speed_ramp");
    setupArsenalToggle(toolAudioCard, "audio_pitch");

    // 4. Chunked Upload Implementation — Mobile Golden Spot: 4MB slices + 2 parallel uploads
    const CHUNK_SIZE = 4 * 1024 * 1024; // 4 MB (Super smooth on mobile networks)
    const PARALLEL_UPLOADS = 2;         // 2 parallel streams (prevents mobile socket choke)

    async function uploadInChunks(file) {
        const totalChunks = Math.ceil(file.size / CHUNK_SIZE);
        logTerminal(`[INIT] File Size: ${(file.size / (1024 * 1024)).toFixed(2)} MB (${totalChunks} chunks × 4MB, mobile-optimized)`);

        // Step 1: Init upload
        mainStatusText.innerText = "Initializing secure chunked upload...";
        subStatusText.innerText = "Connecting to Railway buffer...";

        const initForm = new FormData();
        initForm.append("filename", file.name);
        initForm.append("total_chunks", totalChunks);
        initForm.append("file_size", file.size);

        const initRes = await fetch("/api/upload/init", {
            method: "POST",
            body: initForm
        });

        if (!initRes.ok) {
            const err = await initRes.json();
            throw new Error(err.detail || "Failed to initialize upload");
        }

        const initData = await initRes.json();
        const uploadId = initData.upload_id;

        // Step 2: Upload Chunks in Parallel Batches of 2
        let uploadedBytes = 0;
        const uploadStartTime = Date.now();

        for (let batch = 0; batch < totalChunks; batch += PARALLEL_UPLOADS) {
            const batchEnd = Math.min(batch + PARALLEL_UPLOADS, totalChunks);
            const promises = [];

            for (let i = batch; i < batchEnd; i++) {
                const start = i * CHUNK_SIZE;
                const end = Math.min(file.size, start + CHUNK_SIZE);
                const chunkBlob = file.slice(start, end);

                const chunkForm = new FormData();
                chunkForm.append("upload_id", uploadId);
                chunkForm.append("chunk_index", i);
                chunkForm.append("chunk", chunkBlob, `part_${i}.bin`);

                promises.push(
                    fetch("/api/upload/chunk", { method: "POST", body: chunkForm })
                        .then(res => {
                            if (!res.ok) throw new Error(`Chunk ${i + 1}/${totalChunks} failed`);
                            return end - start;
                        })
                );
            }

            const results = await Promise.all(promises);
            results.forEach(bytes => { uploadedBytes += bytes; });

            const pct = Math.round((uploadedBytes / file.size) * 100);
            const uploadedMb = (uploadedBytes / (1024 * 1024)).toFixed(1);
            const totalMb = (file.size / (1024 * 1024)).toFixed(1);
            const elapsed = (Date.now() - uploadStartTime) / 1000;
            const speed = elapsed > 0 ? (uploadedBytes / (1024 * 1024) / elapsed).toFixed(1) : "—";

            progressBar.style.width = `${pct}%`;
            progressPercentLabel.innerText = `${pct}%`;
            mainStatusText.innerText = "Uploading to Cloud Engine...";
            subStatusText.innerText = `${uploadedMb} / ${totalMb} MB (${pct}%) • ${speed} MB/s • Chunk ${batchEnd}/${totalChunks}`;
        }

        logTerminal(`[SUCCESS] All ${totalChunks} chunks uploaded! Assembling video...`);
        mainStatusText.innerText = "Assembling video stream...";
        subStatusText.innerText = "Validating binary integrity...";

        // Step 3: Complete & Trigger Job
        const customSettings = {
            video: {
                mirror_flip: arsenalState.mirror_flip,
                border_frame: arsenalState.border_frame
            },
            audio: {
                speed_ramp: arsenalState.speed_ramp,
                pitch_semitones: arsenalState.audio_pitch ? 0.5 : 0.0,
                stereo_widen: arsenalState.audio_pitch
            },
            ai_options: {
                vocal_swap: vocalSwapToggle.checked,
                split_screen: splitScreenToggle.checked,
                bgm_type: bgmChoice.value
            }
        };

        const compForm = new FormData();
        compForm.append("upload_id", uploadId);
        compForm.append("filename", file.name);
        compForm.append("preset", selectedPreset);
        compForm.append("mode", activeMode);
        compForm.append("custom_settings", JSON.stringify(customSettings));

        const compRes = await fetch("/api/upload/complete", {
            method: "POST",
            body: compForm
        });

        if (!compRes.ok) {
            const err = await compRes.json();
            throw new Error(err.detail || "Assembly failed");
        }

        return await compRes.json();
    }

    // 5. Start Process Button
    startBtn.addEventListener("click", async () => {
        const hasMedia = (currentInputMode === "upload" && selectedFile) || (currentInputMode === "youtube" && ytVideoData);
        if (!hasMedia) return;

        configCard.style.display = "none";
        progressCard.style.display = "block";
        processingView.style.display = "block";
        completedView.style.display = "none";

        progressBar.style.width = "0%";
        progressPercentLabel.innerText = "0%";
        terminalOutput.innerHTML = "";

        try {
            let jobId = null;

            if (currentInputMode === "youtube") {
                mainStatusText.innerText = "Connecting to YouTube stream...";
                subStatusText.innerText = `Trimming: ${secondsToMMSS(trimRange.start)} ➔ ${secondsToMMSS(trimRange.end)}`;
                logTerminal(`[INIT] YouTube URL: ${ytVideoData.url}`);
                logTerminal(`[TRIM] Start: ${trimRange.start}s, End: ${trimRange.end}s`);

                const customSettings = {
                    video: {
                        mirror_flip: arsenalState.mirror_flip,
                        border_frame: arsenalState.border_frame
                    },
                    audio: {
                        speed_ramp: arsenalState.speed_ramp,
                        pitch_semitones: arsenalState.audio_pitch ? 0.5 : 0.0,
                        stereo_widen: arsenalState.audio_pitch
                    },
                    ai_options: {
                        vocal_swap: vocalSwapToggle.checked,
                        split_screen: splitScreenToggle.checked,
                        bgm_type: bgmChoice.value
                    }
                };

                const ytForm = new FormData();
                ytForm.append("url", ytVideoData.url);
                ytForm.append("start_sec", trimRange.start);
                ytForm.append("end_sec", trimRange.end);
                ytForm.append("preset", selectedPreset);
                ytForm.append("mode", activeMode);
                ytForm.append("custom_settings", JSON.stringify(customSettings));

                const ytRes = await fetch("/api/youtube/process", {
                    method: "POST",
                    body: ytForm
                });

                if (!ytRes.ok) {
                    const err = await ytRes.json();
                    throw new Error(err.detail || "YouTube transformation failed");
                }

                const jobData = await ytRes.json();
                jobId = jobData.job_id;

            } else {
                const jobData = await uploadInChunks(selectedFile);
                jobId = jobData.job_id;
            }

            logTerminal(`[ENQUEUED] Job ID: ${jobId}`);
            mainStatusText.innerText = "Running Anti-Copyright Engine...";
            subStatusText.innerText = "Disrupting pHash & acoustic fingerprints...";

            // Subscribe to progress stream
            subscribeJobStream(jobId);

        } catch (err) {
            mainStatusText.innerText = "Upload / Process Error";
            subStatusText.innerText = err.message;
            logTerminal(`[ERR] ${err.message}`);
            
            setTimeout(() => {
                alert(`Error: ${err.message}\n\nPlease try again.`);
                configCard.style.display = "block";
                progressCard.style.display = "none";
            }, 1000);
        }
    });

    function logTerminal(msg) {
        const line = document.createElement("div");
        line.className = "terminal-line";
        line.innerText = msg;
        terminalOutput.appendChild(line);
        terminalOutput.scrollTop = terminalOutput.scrollHeight;
    }

    function subscribeJobStream(jobId) {
        if (activeEventSource) activeEventSource.close();

        activeEventSource = new EventSource(`/api/jobs/${jobId}/stream`);

        activeEventSource.onmessage = (e) => {
            const data = JSON.parse(e.data);
            const pct = Math.round(data.progress);
            progressBar.style.width = `${pct}%`;
            progressPercentLabel.innerText = `${pct}%`;
            subStatusText.innerText = data.message;
            logTerminal(`[STAGE] ${data.message}`);

            if (data.status === "completed") {
                activeEventSource.close();
                showCompleted(jobId, data);
            } else if (data.status === "failed") {
                activeEventSource.close();
                mainStatusText.innerText = "Pipeline Terminated";
                subStatusText.innerText = data.message;
            }
        };

        activeEventSource.onerror = () => {
            activeEventSource.close();
            // Polling fallback
            const poller = setInterval(async () => {
                try {
                    const res = await fetch(`/api/jobs/${jobId}`);
                    const data = await res.json();
                    progressBar.style.width = `${Math.round(data.progress)}%`;
                    progressPercentLabel.innerText = `${Math.round(data.progress)}%`;
                    subStatusText.innerText = data.message;

                    if (data.status === "completed") {
                        clearInterval(poller);
                        showCompleted(jobId, data);
                    } else if (data.status === "failed") {
                        clearInterval(poller);
                        mainStatusText.innerText = "Failed";
                    }
                } catch {
                    clearInterval(poller);
                }
            }, 1200);
        };
    }

    function showCompleted(jobId, data) {
        setTimeout(() => {
            processingView.style.display = "none";
            completedView.style.display = "block";

            const downloadUrl = `/api/download/${jobId}`;
            finalVideoPlayer.src = downloadUrl;
            dualCleanPlayer.src = downloadUrl;

            if (selectedFile) {
                rawVideoPlayer.src = URL.createObjectURL(selectedFile);
            }

            downloadSafeBtn.href = downloadUrl;
            let safeDownloadName = 'safe_video.mp4';
            if (currentInputMode === "youtube" && ytVideoData) {
                const cleanTitle = (ytVideoData.title || 'youtube_video').replace(/[^a-zA-Z0-9_-]/g, '_').slice(0, 30);
                safeDownloadName = `safe_${cleanTitle}.mp4`;
            } else if (selectedFile) {
                safeDownloadName = `safe_${selectedFile.name}`;
            }
            downloadSafeBtn.setAttribute("download", safeDownloadName);
        }, 500);
    }

    // 6. Player Tab Switcher (Single vs Dual)
    tabSinglePlayer.addEventListener("click", () => {
        tabSinglePlayer.classList.add("active");
        tabDualPlayer.classList.remove("active");
        singlePlayerBox.style.display = "block";
        dualPlayerBox.style.display = "none";
        rawVideoPlayer.pause();
        dualCleanPlayer.pause();
    });

    tabDualPlayer.addEventListener("click", () => {
        tabDualPlayer.classList.add("active");
        tabSinglePlayer.classList.remove("active");
        singlePlayerBox.style.display = "none";
        dualPlayerBox.style.display = "grid";
        finalVideoPlayer.pause();
    });

    // Sync dual playback
    dualCleanPlayer.addEventListener("play", () => rawVideoPlayer.play().catch(() => {}));
    dualCleanPlayer.addEventListener("pause", () => rawVideoPlayer.pause());
    dualCleanPlayer.addEventListener("seeked", () => {
        rawVideoPlayer.currentTime = dualCleanPlayer.currentTime;
    });

    // 7. Restart
    restartBtn.addEventListener("click", () => {
        progressCard.style.display = "none";
        configCard.style.display = "block";
        fileInput.value = "";
        selectedFile = null;
        dropPrompt.style.display = "block";
        selectedPreview.style.display = "none";
        sourceVideoPlayer.pause();
        sourceVideoPlayer.src = "";
        finalVideoPlayer.pause();
        finalVideoPlayer.src = "";
        
        // Reset YouTube
        ytVideoData = null;
        ytUrlInput.value = "";
        ytDetailsCard.style.display = "none";
        updateButtonLabel();
    });
});
