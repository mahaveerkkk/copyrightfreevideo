document.addEventListener("DOMContentLoaded", async () => {
    const fileInput = document.getElementById("fileInput");
    const dropZone = document.getElementById("dropZone");
    const fileChip = document.getElementById("fileChip");
    const fileName = document.getElementById("fileName");
    const fileSize = document.getElementById("fileSize");
    const presetGrid = document.getElementById("presetGrid");
    const processBtn = document.getElementById("processBtn");
    const btnActionText = document.getElementById("btnActionText");

    const idleState = document.getElementById("idleState");
    const processingState = document.getElementById("processingState");
    const completedState = document.getElementById("completedState");

    const progressBarFill = document.getElementById("progressBarFill");
    const progressPct = document.getElementById("progressPct");
    const stageMessage = document.getElementById("stageMessage");
    const terminalLog = document.getElementById("terminalLog");

    const previewPlayer = document.getElementById("previewPlayer");
    const downloadBtn = document.getElementById("downloadBtn");
    const resetBtn = document.getElementById("resetBtn");
    const auditTimer = document.getElementById("auditTimer");
    const modeExecuted = document.getElementById("modeExecuted");
    const acousticStatus = document.getElementById("acousticStatus");

    // Mode Tabs & AI Box
    const tabTurbo = document.getElementById("tabTurbo");
    const tabDeep = document.getElementById("tabDeep");
    const aiDeepBox = document.getElementById("aiDeepBox");
    const vocalSwapCheck = document.getElementById("vocalSwapCheck");
    const splitScreenCheck = document.getElementById("splitScreenCheck");
    const bgmSelect = document.getElementById("bgmSelect");

    // Customizer elements
    const customizerToggle = document.getElementById("customizerToggle");
    const customizerBody = document.getElementById("customizerBody");
    const toggleArrow = document.getElementById("toggleArrow");

    const zoomSlider = document.getElementById("zoomSlider");
    const zoomVal = document.getElementById("zoomVal");
    const tiltSlider = document.getElementById("tiltSlider");
    const tiltVal = document.getElementById("tiltVal");
    const grainSlider = document.getElementById("grainSlider");
    const grainVal = document.getElementById("grainVal");
    const vignetteCheck = document.getElementById("vignetteCheck");
    const sharpenCheck = document.getElementById("sharpenCheck");

    const pitchSlider = document.getElementById("pitchSlider");
    const pitchVal = document.getElementById("pitchVal");
    const tempoSlider = document.getElementById("tempoSlider");
    const tempoVal = document.getElementById("tempoVal");
    const widenCheck = document.getElementById("widenCheck");
    const notchCheck = document.getElementById("notchCheck");
    const securityBadge = document.getElementById("securityBadge");

    let selectedFile = null;
    let selectedPresetId = "stealth_deep";
    let activeMode = "turbo";
    let presetsCache = {};
    let activeEventSource = null;

    // Mode Tab Switching
    tabTurbo.addEventListener("click", () => {
        tabTurbo.classList.add("active");
        tabDeep.classList.remove("active");
        activeMode = "turbo";
        aiDeepBox.style.display = "none";
        btnActionText.innerText = "Initiate Turbo Transformation (5s)";
        securityBadge.innerText = "98% SHIELDED";
    });

    tabDeep.addEventListener("click", () => {
        tabDeep.classList.add("active");
        tabTurbo.classList.remove("active");
        activeMode = "ai_deep";
        aiDeepBox.style.display = "block";
        btnActionText.innerText = "Initiate AI Deep Studio Transformation";
        securityBadge.innerText = "100% MAXIMUM IMMUNITY";
    });

    // Toggle Customizer Accordion
    customizerToggle.addEventListener("click", () => {
        const isHidden = customizerBody.style.display === "none";
        customizerBody.style.display = isHidden ? "block" : "none";
        toggleArrow.innerText = isHidden ? "▲" : "▼";
    });

    // Slider Listeners
    zoomSlider.addEventListener("input", (e) => zoomVal.innerText = `${parseFloat(e.target.value).toFixed(3)}x`);
    tiltSlider.addEventListener("input", (e) => tiltVal.innerText = `${parseFloat(e.target.value).toFixed(2)}°`);
    grainSlider.addEventListener("input", (e) => grainVal.innerText = `${parseFloat(e.target.value).toFixed(1)}%`);
    pitchSlider.addEventListener("input", (e) => {
        const val = parseFloat(e.target.value);
        pitchVal.innerText = `${val >= 0 ? '+' : ''}${val.toFixed(2)} st`;
    });
    tempoSlider.addEventListener("input", (e) => tempoVal.innerText = `${parseFloat(e.target.value).toFixed(3)}x`);

    function syncCustomizerWithPreset(preset) {
        if (!preset) return;
        const v = preset.video || {};
        const a = preset.audio || {};

        zoomSlider.value = v.zoom || 1.045;
        zoomVal.innerText = `${parseFloat(zoomSlider.value).toFixed(3)}x`;

        tiltSlider.value = v.rotate_deg || 0.45;
        tiltVal.innerText = `${parseFloat(tiltSlider.value).toFixed(2)}°`;

        grainSlider.value = v.noise_grain || 2.2;
        grainVal.innerText = `${parseFloat(grainSlider.value).toFixed(1)}%`;

        vignetteCheck.checked = v.vignette !== false;
        sharpenCheck.checked = v.sharpen !== false;

        pitchSlider.value = a.pitch_semitones || 0.50;
        pitchVal.innerText = `+${parseFloat(pitchSlider.value).toFixed(2)} st`;

        tempoSlider.value = a.tempo || 1.030;
        tempoVal.innerText = `${parseFloat(tempoSlider.value).toFixed(3)}x`;

        widenCheck.checked = a.stereo_widen !== false;
        notchCheck.checked = a.notch_filter !== false;
    }

    // 1. Fetch & Render Presets
    try {
        const res = await fetch("/api/presets");
        const presets = await res.json();
        presetGrid.innerHTML = "";

        presets.forEach(p => {
            presetsCache[p.id] = p;
            const card = document.createElement("div");
            card.className = `preset-card ${p.id === selectedPresetId ? "active" : ""}`;
            card.dataset.id = p.id;
            card.innerHTML = `
                <span class="preset-badge">${p.badge}</span>
                <div class="preset-name">${p.name}</div>
                <div class="preset-desc">${p.description}</div>
            `;
            card.addEventListener("click", () => {
                document.querySelectorAll(".preset-card").forEach(c => c.classList.remove("active"));
                card.classList.add("active");
                selectedPresetId = p.id;
                syncCustomizerWithPreset(p);
            });
            presetGrid.appendChild(card);
        });

        if (presetsCache[selectedPresetId]) {
            syncCustomizerWithPreset(presetsCache[selectedPresetId]);
        }
    } catch (err) {
        console.error("Failed to load presets", err);
    }

    // 2. Drop Zone & File Selection
    dropZone.addEventListener("click", () => fileInput.click());

    fileInput.addEventListener("change", (e) => {
        if (e.target.files.length > 0) {
            handleFile(e.target.files[0]);
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
            handleFile(e.dataTransfer.files[0]);
        }
    });

    function handleFile(file) {
        selectedFile = file;
        fileName.innerText = file.name;
        const sizeMb = (file.size / (1024 * 1024)).toFixed(2);
        fileSize.innerText = `${sizeMb} MB`;
        fileChip.style.display = "inline-flex";
        processBtn.disabled = false;
    }

    // 3. Start Transformation Process
    processBtn.addEventListener("click", async () => {
        if (!selectedFile) return;

        processBtn.disabled = true;
        idleState.style.display = "none";
        completedState.style.display = "none";
        processingState.style.display = "flex";

        progressBarFill.style.width = "5%";
        progressPct.innerText = "5%";
        stageMessage.innerText = `Uploading source video for ${activeMode === "turbo" ? 'Turbo DSP' : 'AI Deep Studio'}...`;
        terminalLog.innerHTML = `<div class="log-line">[UPLOAD] Sending ${selectedFile.name} (Mode: ${activeMode})...</div>`;

        const customSettings = {
            video: {
                zoom: parseFloat(zoomSlider.value),
                rotate_deg: parseFloat(tiltSlider.value),
                noise_grain: parseFloat(grainSlider.value),
                vignette: vignetteCheck.checked,
                sharpen: sharpenCheck.checked
            },
            audio: {
                pitch_semitones: parseFloat(pitchSlider.value),
                tempo: parseFloat(tempoSlider.value),
                stereo_widen: widenCheck.checked,
                notch_filter: notchCheck.checked
            },
            ai_options: {
                vocal_swap: vocalSwapCheck.checked,
                split_screen: splitScreenCheck.checked,
                bgm_type: bgmSelect.value
            }
        };

        const formData = new FormData();
        formData.append("file", selectedFile);
        formData.append("preset", selectedPresetId);
        formData.append("mode", activeMode);
        formData.append("custom_settings", JSON.stringify(customSettings));

        try {
            const uploadRes = await fetch("/api/upload", {
                method: "POST",
                body: formData
            });

            if (!uploadRes.ok) {
                const err = await uploadRes.json();
                throw new Error(err.detail || "Upload failed");
            }

            const data = await uploadRes.json();
            const jobId = data.job_id;
            addLog(`[JOB] Enqueued Task ID: ${jobId}`);

            subscribeToJobStream(jobId);

        } catch (err) {
            stageMessage.innerText = `Error: ${err.message}`;
            addLog(`[ERR] ${err.message}`);
            processBtn.disabled = false;
        }
    });

    function addLog(text) {
        const line = document.createElement("div");
        line.className = "log-line";
        line.innerText = text;
        terminalLog.appendChild(line);
        terminalLog.scrollTop = terminalLog.scrollHeight;
    }

    function subscribeToJobStream(jobId) {
        if (activeEventSource) {
            activeEventSource.close();
        }

        activeEventSource = new EventSource(`/api/jobs/${jobId}/stream`);

        activeEventSource.onmessage = (e) => {
            const data = JSON.parse(e.data);
            const pct = Math.round(data.progress);
            progressBarFill.style.width = `${pct}%`;
            progressPct.innerText = `${pct}%`;
            stageMessage.innerText = data.message;
            addLog(`[STAGE] ${data.message}`);

            if (data.status === "completed") {
                activeEventSource.close();
                showCompleted(jobId, data);
            } else if (data.status === "failed") {
                activeEventSource.close();
                stageMessage.innerText = `Failed: ${data.message}`;
                addLog(`[FAILED] Pipeline terminated with error.`);
                processBtn.disabled = false;
            }
        };

        activeEventSource.onerror = () => {
            activeEventSource.close();
            pollJob(jobId);
        };
    }

    async function pollJob(jobId) {
        const interval = setInterval(async () => {
            try {
                const res = await fetch(`/api/jobs/${jobId}`);
                const data = await res.json();
                progressBarFill.style.width = `${Math.round(data.progress)}%`;
                progressPct.innerText = `${Math.round(data.progress)}%`;
                stageMessage.innerText = data.message;

                if (data.status === "completed") {
                    clearInterval(interval);
                    showCompleted(jobId, data);
                } else if (data.status === "failed") {
                    clearInterval(interval);
                    processBtn.disabled = false;
                }
            } catch (err) {
                clearInterval(interval);
            }
        }, 1000);
    }

    function showCompleted(jobId, data) {
        setTimeout(() => {
            processingState.style.display = "none";
            completedState.style.display = "flex";

            const streamUrl = `/api/download/${jobId}`;
            previewPlayer.src = streamUrl;
            downloadBtn.href = streamUrl;
            downloadBtn.setAttribute("download", `safe_${selectedFile.name}`);

            modeExecuted.innerText = (activeMode === "turbo" ? "Turbo DSP" : "AI Deep Studio");
            acousticStatus.innerText = (activeMode === "turbo" ? "Phase Shifted" : "BGM Replaced");

            if (data.elapsed) {
                auditTimer.innerText = `${data.elapsed}s`;
            }
        }, 600);
    }

    // 4. Reset
    resetBtn.addEventListener("click", () => {
        completedState.style.display = "none";
        processingState.style.display = "none";
        idleState.style.display = "flex";
        fileInput.value = "";
        selectedFile = null;
        fileChip.style.display = "none";
        processBtn.disabled = true;
        previewPlayer.pause();
        previewPlayer.src = "";
    });
});
