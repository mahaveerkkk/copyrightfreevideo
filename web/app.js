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
    let pendingHookData = null;

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

    // Master 3-Studio Tabs & Containers
    const btnStudioMovie = document.getElementById("btnStudioMovie");
    const btnStudioDownloader = document.getElementById("btnStudioDownloader");
    const btnStudioHook = document.getElementById("btnStudioHook");
    const btnStudioLofi = document.getElementById("btnStudioLofi");
    const studioDownloaderCard = document.getElementById("studioDownloaderCard");
    const studioHookCard = document.getElementById("studioHookCard");
    const studioLofiCard = document.getElementById("studioLofiCard");

    // Studio 4: Video Downloader Elements
    const dlUrlInput = document.getElementById("dlUrlInput");
    const btnDlPaste = document.getElementById("btnDlPaste");
    const btnDlFetch = document.getElementById("btnDlFetch");
    const dlSpinner = document.getElementById("dlSpinner");
    const dlBtnText = document.getElementById("dlBtnText");
    const dlResultContainer = document.getElementById("dlResultContainer");
    const dlThumbImg = document.getElementById("dlThumbImg");
    const dlTitleText = document.getElementById("dlTitleText");
    const dlAuthorText = document.getElementById("dlAuthorText");
    const dlDurationBadge = document.getElementById("dlDurationBadge");
    const dlQualityGrid = document.getElementById("dlQualityGrid");
    const dlStatusBox = document.getElementById("dlStatusBox");
    const dlStatusMsg = document.getElementById("dlStatusMsg");

    // Studio 2: Hook Finder Elements
    const hookYtUrlInput = document.getElementById("hookYtUrlInput");
    const btnFindHooks = document.getElementById("btnFindHooks");
    const hookSpinner = document.getElementById("hookSpinner");
    const hookBtnText = document.getElementById("hookBtnText");
    const hookResultsContainer = document.getElementById("hookResultsContainer");
    const hookCardsList = document.getElementById("hookCardsList");

    // Studio 3: LoFi Elements
    const lofiYtUrlInput = document.getElementById("lofiYtUrlInput");
    const btnGenerateLofi = document.getElementById("btnGenerateLofi");
    let selectedLofiStyle = "slowed_reverb";

    document.querySelectorAll(".lofi-style-card").forEach(card => {
        card.addEventListener("click", () => {
            document.querySelectorAll(".lofi-style-card").forEach(c => c.classList.remove("active"));
            card.classList.add("active");
            selectedLofiStyle = card.dataset.style;
        });
    });

    // Switch between the Master Studios
    function switchMasterStudio(target) {
        if (btnStudioMovie) btnStudioMovie.classList.toggle("active", target === "movie");
        if (btnStudioDownloader) btnStudioDownloader.classList.toggle("active", target === "downloader");
        if (btnStudioHook) btnStudioHook.classList.toggle("active", target === "hook");
        if (btnStudioLofi) btnStudioLofi.classList.toggle("active", target === "lofi");

        if (configCard) configCard.style.display = target === "movie" ? "block" : "none";
        if (studioDownloaderCard) studioDownloaderCard.style.display = target === "downloader" ? "block" : "none";
        if (studioHookCard) studioHookCard.style.display = target === "hook" ? "block" : "none";
        if (studioLofiCard) studioLofiCard.style.display = target === "lofi" ? "block" : "none";
    }

    if (btnStudioMovie) btnStudioMovie.addEventListener("click", () => switchMasterStudio("movie"));
    if (btnStudioDownloader) btnStudioDownloader.addEventListener("click", () => switchMasterStudio("downloader"));
    if (btnStudioHook) btnStudioHook.addEventListener("click", () => switchMasterStudio("hook"));
    if (btnStudioLofi) btnStudioLofi.addEventListener("click", () => switchMasterStudio("lofi"));

    // Studio 2 & 3 Input Mode Tabs & Phone Upload Handlers
    const tabHookYt = document.getElementById("tabHookYt");
    const tabHookUpload = document.getElementById("tabHookUpload");
    const hookYtBox = document.getElementById("hookYtBox");
    const hookDropZone = document.getElementById("hookDropZone");
    const hookFileInput = document.getElementById("hookFileInput");
    const btnSelectHookFile = document.getElementById("btnSelectHookFile");

    tabHookYt.addEventListener("click", () => {
        tabHookYt.classList.add("active");
        tabHookUpload.classList.remove("active");
        hookYtBox.style.display = "flex";
        hookDropZone.style.display = "none";
    });

    tabHookUpload.addEventListener("click", () => {
        tabHookUpload.classList.add("active");
        tabHookYt.classList.remove("active");
        hookYtBox.style.display = "none";
        hookDropZone.style.display = "block";
    });

    btnSelectHookFile.addEventListener("click", () => hookFileInput.click());
    hookFileInput.addEventListener("change", (e) => {
        if (e.target.files.length > 0) {
            const f = e.target.files[0];
            switchMasterStudio("movie");
            tabUploadMode.click();
            handleSelectedFile(f);
        }
    });

    const tabLofiYt = document.getElementById("tabLofiYt");
    const tabLofiUpload = document.getElementById("tabLofiUpload");
    const lofiYtBox = document.getElementById("lofiYtBox");
    const lofiDropZone = document.getElementById("lofiDropZone");
    const lofiFileInput = document.getElementById("lofiFileInput");
    const btnSelectLofiFile = document.getElementById("btnSelectLofiFile");
    const lofiFileNameLabel = document.getElementById("lofiFileNameLabel");
    let selectedLofiFile = null;

    tabLofiYt.addEventListener("click", () => {
        tabLofiYt.classList.add("active");
        tabLofiUpload.classList.remove("active");
        lofiYtBox.style.display = "flex";
        lofiDropZone.style.display = "none";
        selectedLofiFile = null;
    });

    tabLofiUpload.addEventListener("click", () => {
        tabLofiUpload.classList.add("active");
        tabLofiYt.classList.remove("active");
        lofiYtBox.style.display = "none";
        lofiDropZone.style.display = "block";
    });

    btnSelectLofiFile.addEventListener("click", () => lofiFileInput.click());
    lofiFileInput.addEventListener("change", (e) => {
        if (e.target.files.length > 0) {
            selectedLofiFile = e.target.files[0];
            lofiFileNameLabel.innerText = `Selected: ${selectedLofiFile.name}`;
        }
    });

    // Helper: Safely apply timestamps to trimmer
    function applyHookTimestamps(startSec, endSec) {
        trimRange.start = startSec;
        trimRange.end = endSec;
        trimStartInput.value = secondsToMMSS(startSec);
        trimEndInput.value = secondsToMMSS(endSec);
        sliderStart.value = startSec;
        sliderEnd.value = endSec;
        updateClipDurationBadge();
        logTerminal(`[HOOK] Auto-locked Trimmer to: ${secondsToMMSS(startSec)} ➔ ${secondsToMMSS(endSec)}`);
    }

    // Studio 2: Find Hooks Action
    btnFindHooks.addEventListener("click", async () => {
        const url = hookYtUrlInput.value.trim();
        if (!url) {
            alert("Please paste a YouTube video or podcast URL");
            return;
        }

        hookSpinner.style.display = "inline-block";
        hookBtnText.innerText = "Analyzing Dialogue & Energy...";
        btnFindHooks.disabled = true;

        try {
            const form = new FormData();
            form.append("url", url);
            const res = await fetch("/api/youtube/find-hooks", {
                method: "POST",
                body: form
            });

            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || "Failed to find viral hooks");
            }

            const data = await res.json();
            const hooks = data.hooks || [];

            hookCardsList.innerHTML = "";
            hooks.forEach((h, idx) => {
                const card = document.createElement("div");
                card.className = "hook-card";
                card.innerHTML = `
                    <div class="hook-info-left">
                        <div class="hook-card-title">${h.title}</div>
                        <div class="hook-card-meta">
                            <span>⏱️ ${h.start_str} ➔ ${h.end_str} (${h.duration_sec}s)</span>
                            <span class="hook-score-badge">🔥 Score: ${h.score}%</span>
                        </div>
                    </div>
                    <button type="button" class="btn-use-hook">Use in Movie Shield</button>
                `;

                // When user clicks "Use in Movie Shield", transfer to Studio 1 Trimmer!
                card.querySelector(".btn-use-hook").addEventListener("click", () => {
                    // Lock hook timestamps for fetch callback
                    pendingHookData = {
                        start: h.start,
                        end: h.end,
                        startStr: h.start_str,
                        endStr: h.end_str
                    };

                    switchMasterStudio("movie");
                    currentInputMode = "youtube";
                    tabYoutubeMode.click();
                    ytUrlInput.value = url;
                    fetchYtBtn.click();
                });

                hookCardsList.appendChild(card);
            });

            hookResultsContainer.style.display = "block";

        } catch (err) {
            alert(`Hook Finder Error: ${err.message}`);
        } finally {
            hookSpinner.style.display = "none";
            hookBtnText.innerText = "🎯 Find Viral Hooks";
            btnFindHooks.disabled = false;
        }
    });

    // Studio 3: Generate Lo-Fi Action
    btnGenerateLofi.addEventListener("click", async () => {
        const isUploadMode = tabLofiUpload.classList.contains("active");
        const url = lofiYtUrlInput.value.trim();

        if (isUploadMode && !selectedLofiFile) {
            alert("Please select an audio file from your phone");
            return;
        } else if (!isUploadMode && !url) {
            alert("Please paste a YouTube song URL");
            return;
        }

        configCard.style.display = "none";
        studioLofiCard.style.display = "none";
        progressCard.style.display = "block";
        processingView.style.display = "block";
        completedView.style.display = "none";

        progressBar.style.width = "0%";
        progressPercentLabel.innerText = "0%";
        terminalOutput.innerHTML = "";

        try {
            const targetLabel = isUploadMode ? selectedLofiFile.name : url;
            logTerminal(`[INIT] Audio Scrambler: ${targetLabel}`);
            logTerminal(`[STYLE] Generating ${selectedLofiStyle.replace('_', ' ')} audio matrix...`);

            const form = new FormData();
            if (isUploadMode && selectedLofiFile) {
                form.append("file", selectedLofiFile);
            } else {
                form.append("url", url);
            }
            form.append("style", selectedLofiStyle);
            form.append("speed", "0.88");
            form.append("reverb_level", "0.5");

            const res = await fetch("/api/music/lofi", {
                method: "POST",
                body: form
            });

            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || "Lo-Fi generation failed");
            }

            const data = await res.json();
            subscribeJobStream(data.job_id);

        } catch (err) {
            alert(`Music Error: ${err.message}`);
            switchMasterStudio("lofi");
            progressCard.style.display = "none";
        }
    });

    // ================= STUDIO 4: VIDEO DOWNLOADER HANDLERS =================
    if (btnDlPaste && dlUrlInput) {
        btnDlPaste.addEventListener("click", async () => {
            try {
                if (navigator.clipboard && navigator.clipboard.readText) {
                    const text = await navigator.clipboard.readText();
                    if (text && text.trim()) {
                        dlUrlInput.value = text.trim();
                        dlUrlInput.focus();
                    }
                } else {
                    dlUrlInput.focus();
                }
            } catch (err) {
                dlUrlInput.focus();
            }
        });
    }

    if (btnDlFetch && dlUrlInput) {
        btnDlFetch.addEventListener("click", async () => {
            const url = dlUrlInput.value.trim();
            if (!url) {
                alert("Please paste a valid YouTube or video link first!");
                dlUrlInput.focus();
                return;
            }

            dlBtnText.innerText = "Fetching Video...";
            dlSpinner.style.display = "inline-block";
            btnDlFetch.disabled = true;
            if (dlStatusBox) dlStatusBox.style.display = "none";
            if (dlResultContainer) dlResultContainer.style.display = "none";

            try {
                const formData = new FormData();
                formData.append("url", url);

                const res = await fetch("/api/downloader/info", {
                    method: "POST",
                    body: formData
                });

                if (!res.ok) {
                    const err = await res.json();
                    throw new Error(err.detail || "Could not fetch video info");
                }

                const json = await res.json();
                const videoData = json.data;

                // Update Preview Card
                if (dlThumbImg) dlThumbImg.src = videoData.thumbnail || "";
                if (dlTitleText) dlTitleText.innerText = videoData.title || "Video";
                if (dlAuthorText) dlAuthorText.innerText = videoData.channel || "Source";
                if (dlDurationBadge) dlDurationBadge.innerText = `⏱️ ${videoData.duration_str || "Direct"}`;

                // Render Quality Cards
                if (dlQualityGrid) {
                    dlQualityGrid.innerHTML = "";
                    (videoData.formats || []).forEach(fmt => {
                        const card = document.createElement("div");
                        card.className = "dl-card";
                        card.innerHTML = `
                            <div class="dl-card-header">
                                <div class="dl-card-title-group">
                                    <span class="dl-card-icon">${fmt.icon || '🎬'}</span>
                                    <div>
                                        <div class="dl-card-title">${fmt.label}</div>
                                        <div style="font-size: 0.7rem; color: var(--text-muted);">${fmt.ext.toUpperCase()} format</div>
                                    </div>
                                </div>
                                <span class="dl-card-badge">${fmt.badge}</span>
                            </div>
                            <button type="button" class="dl-btn-action" data-quality="${fmt.quality}">
                                <span>⬇️</span>
                                <span>Download to Device</span>
                            </button>
                        `;

                        const dlBtn = card.querySelector(".dl-btn-action");
                        dlBtn.addEventListener("click", () => {
                            triggerVideoDownload(url, fmt.quality, fmt.label, dlBtn);
                        });

                        dlQualityGrid.appendChild(card);
                    });
                }

                if (dlResultContainer) dlResultContainer.style.display = "block";

            } catch (err) {
                alert(`Error: ${err.message}`);
            } finally {
                dlBtnText.innerText = "🔍 Get Download Links";
                dlSpinner.style.display = "none";
                btnDlFetch.disabled = false;
            }
        });
    }

    function triggerVideoDownload(url, quality, label, buttonEl) {
        if (!buttonEl) return;
        const origHtml = buttonEl.innerHTML;
        buttonEl.classList.add("downloading");
        buttonEl.innerHTML = `<span>⏳</span> <span>Connecting stream...</span>`;
        buttonEl.disabled = true;

        if (dlStatusBox && dlStatusMsg) {
            dlStatusBox.style.display = "flex";
            dlStatusMsg.innerText = `🚀 Stream connecting for ${label}... Your browser will start saving the file shortly!`;
        }

        // Trigger direct file download
        const downloadUrl = `/api/downloader/download?url=${encodeURIComponent(url)}&quality=${encodeURIComponent(quality)}`;
        const tempLink = document.createElement("a");
        tempLink.href = downloadUrl;
        tempLink.setAttribute("download", "");
        document.body.appendChild(tempLink);
        tempLink.click();
        document.body.removeChild(tempLink);

        // Reset button after 4 seconds
        setTimeout(() => {
            buttonEl.classList.remove("downloading");
            buttonEl.innerHTML = `<span>✅</span> <span>Downloaded!</span>`;
            setTimeout(() => {
                buttonEl.innerHTML = origHtml;
                buttonEl.disabled = false;
                if (dlStatusBox) dlStatusBox.style.display = "none";
            }, 3000);
        }, 4000);
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

    // Fetch YouTube Video / Direct Movie Info
    fetchYtBtn.addEventListener("click", async () => {
        const url = ytUrlInput.value.trim();
        if (!url) {
            alert("Please paste a YouTube link or direct movie download URL (MP4, MKV)");
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

            // Initialize Trimmer (If video is long, default to a smart 45-60s clip range for speed)
            const totalSec = Math.max(5, Math.round(data.duration));
            sliderStart.max = totalSec;
            sliderEnd.max = totalSec;

            if (pendingHookData) {
                applyHookTimestamps(pendingHookData.start, pendingHookData.end);
                pendingHookData = null;
            } else {
                const initialEnd = totalSec > 90 ? Math.min(totalSec, 45) : totalSec;
                trimRange.start = 0;
                trimRange.end = initialEnd;
                sliderStart.value = 0;
                sliderEnd.value = initialEnd;
                trimStartInput.value = "00:00";
                trimEndInput.value = secondsToMMSS(initialEnd);
                updateClipDurationBadge();
                updateSplitHint();
            }

            ytDetailsCard.style.display = "block";
            updateSplitHint();

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
        updateSplitHint();
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
        updateSplitHint();
    });

    trimStartInput.addEventListener("change", () => {
        let sec = mmssToSeconds(trimStartInput.value);
        sec = Math.min(sec, trimRange.end - 1);
        trimRange.start = Math.max(0, sec);
        sliderStart.value = trimRange.start;
        trimStartInput.value = secondsToMMSS(trimRange.start);
        updateClipDurationBadge();
        updateSplitHint();
    });

    trimEndInput.addEventListener("change", () => {
        let sec = mmssToSeconds(trimEndInput.value);
        const maxSec = parseFloat(sliderEnd.max);
        sec = Math.min(maxSec, Math.max(trimRange.start + 1, sec));
        trimRange.end = sec;
        sliderEnd.value = trimRange.end;
        trimEndInput.value = secondsToMMSS(trimRange.end);
        updateClipDurationBadge();
        updateSplitHint();
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
        updateSplitHint();
    });

    // Multi-Part Auto-Splitter Controls
    let activeSplitMinutes = 0;
    const splitCalcHint = document.getElementById("splitCalcHint");
    const splitPills = document.querySelectorAll(".split-pill");

    function updateSplitHint() {
        if (!splitCalcHint) return;
        const totalDuration = Math.max(0, trimRange.end - trimRange.start);
        if (activeSplitMinutes > 0 && totalDuration > 0) {
            const splitSec = activeSplitMinutes * 60;
            const partsCount = Math.ceil(totalDuration / splitSec);
            if (partsCount > 1) {
                splitCalcHint.style.display = "block";
                splitCalcHint.innerHTML = `💡 <strong>${partsCount} continuous parts</strong> will be auto-generated in the background queue (${activeSplitMinutes} mins each). Each part will be instantly downloadable as it finishes!`;
            } else {
                splitCalcHint.style.display = "block";
                splitCalcHint.innerHTML = `💡 Selected range (${secondsToMMSS(totalDuration)}) fits within 1 part. Will process as single video.`;
            }
        } else {
            splitCalcHint.style.display = "none";
        }
    }

    splitPills.forEach(pill => {
        pill.addEventListener("click", () => {
            splitPills.forEach(p => p.classList.remove("active"));
            pill.classList.add("active");
            activeSplitMinutes = parseInt(pill.dataset.split, 10) || 0;
            updateSplitHint();
        });
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

        // Show Video Preview & Check Duration
        const objectUrl = URL.createObjectURL(file);
        sourceVideoPlayer.src = objectUrl;
        dropPrompt.style.display = "none";
        selectedPreview.style.display = "flex";

        sourceVideoPlayer.onloadedmetadata = () => {
            const durationSec = sourceVideoPlayer.duration;
            const mins = Math.round(durationSec / 60);
            if (durationSec > 600) { // More than 10 minutes
                alert(`⚠️ Note: Uploaded video is ${mins} minutes long.\n\nServer 1GB RAM safety ke liye: Lambi videos ka 1 se 5 minute ka clip convert karna recommended hai, ya YouTube Trimmer use karein.`);
            }
        };

        updateButtonLabel();
    }

    // 2.5 One-Tap Defense Arsenal Interactive Toggles
    const toolDynamicCamCard = document.getElementById("toolDynamicCamCard");
    const toolColorToneCard = document.getElementById("toolColorToneCard");
    const toolDialogueCard = document.getElementById("toolDialogueCard");
    const toolAudioCard = document.getElementById("toolAudioCard");
    const toolSmartCutsCard = document.getElementById("toolSmartCutsCard");
    const toolPoisonMeshCard = document.getElementById("toolPoisonMeshCard");
    const toolFormantCard = document.getElementById("toolFormantCard");
    const toolMirrorCard = document.getElementById("toolMirrorCard");
    const toolBorderCard = document.getElementById("toolBorderCard");
    const bgmMoodSelect = document.getElementById("bgmMoodSelect");

    const arsenalState = {
        dynamic_camera: true,  // Core Cinema Motion: Random 5-11% zooms & cuts every 5-8s
        color_tone: true,      // Core Procedural Color: Random cinematic color grade & grain
        isolate_dialogue: true,// Core Dialogue: Mutes original BGM, preserves clean voice
        audio_pitch: true,     // Core Acoustic Scramble: Pitch +0.35st, speed 1.02x, notch EQ
        smart_cuts: true,      // AI Smart Cuts: 0.15s invisible cuts every 5.5s to destroy 10s match
        poison_mesh: true,     // Transparent Dynamic Poison Mesh: 1.8% noise to scramble pHash
        formant_natural: true, // Formant Voice Naturalizer: Keeps voice rich & prevents chipmunk
        mirror_flip: false,    // Optional: Kept OFF to prevent unnatural backward video
        border_frame: false    // Optional: 2% clean black border
    };

    function setupArsenalToggle(card, key) {
        if (!card) return;
        card.addEventListener("click", () => {
            arsenalState[key] = !arsenalState[key];
            card.classList.toggle("active", arsenalState[key]);
            const statusEl = card.querySelector(".arsenal-status");
            if (statusEl) {
                statusEl.innerText = arsenalState[key] ? "ACTIVE" : "OPTIONAL";
                statusEl.className = `arsenal-status ${arsenalState[key] ? "on" : "off"}`;
            }
        });
    }

    setupArsenalToggle(toolDynamicCamCard, "dynamic_camera");
    setupArsenalToggle(toolColorToneCard, "color_tone");
    setupArsenalToggle(toolDialogueCard, "isolate_dialogue");
    setupArsenalToggle(toolAudioCard, "audio_pitch");
    setupArsenalToggle(toolSmartCutsCard, "smart_cuts");
    setupArsenalToggle(toolPoisonMeshCard, "poison_mesh");
    setupArsenalToggle(toolFormantCard, "formant_natural");
    setupArsenalToggle(toolMirrorCard, "mirror_flip");
    setupArsenalToggle(toolBorderCard, "border_frame");

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
                border_frame: arsenalState.border_frame,
                dynamic_camera: arsenalState.dynamic_camera,
                color_mood: arsenalState.color_tone ? (bgmMoodSelect ? bgmMoodSelect.value : "auto") : "none",
                isolate_dialogue: arsenalState.isolate_dialogue,
                smart_cuts: arsenalState.smart_cuts,
                poison_mesh: arsenalState.poison_mesh
            },
            audio: {
                speed_ramp: arsenalState.audio_pitch,
                pitch_semitones: arsenalState.audio_pitch ? 0.35 : 0.0,
                stereo_widen: arsenalState.audio_pitch,
                smart_cuts: arsenalState.smart_cuts,
                formant_natural: arsenalState.formant_natural
            },
            ai_options: {
                vocal_swap: arsenalState.isolate_dialogue || vocalSwapToggle.checked,
                split_screen: splitScreenToggle.checked,
                bgm_type: bgmMoodSelect ? bgmMoodSelect.value : "auto"
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
            headers: getAuthHeaders(),
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
                        border_frame: arsenalState.border_frame,
                        dynamic_camera: arsenalState.dynamic_camera,
                        color_mood: arsenalState.color_tone ? (bgmMoodSelect ? bgmMoodSelect.value : "auto") : "none",
                        isolate_dialogue: arsenalState.isolate_dialogue,
                        smart_cuts: arsenalState.smart_cuts,
                        poison_mesh: arsenalState.poison_mesh
                    },
                    audio: {
                        speed_ramp: arsenalState.audio_pitch,
                        pitch_semitones: arsenalState.audio_pitch ? 0.35 : 0.0,
                        stereo_widen: arsenalState.audio_pitch,
                        smart_cuts: arsenalState.smart_cuts,
                        formant_natural: arsenalState.formant_natural
                    },
                    ai_options: {
                        vocal_swap: arsenalState.isolate_dialogue || vocalSwapToggle.checked,
                        split_screen: splitScreenToggle.checked,
                        bgm_type: bgmMoodSelect ? bgmMoodSelect.value : "auto"
                    }
                };

                const ytForm = new FormData();
                ytForm.append("url", ytVideoData.url);
                ytForm.append("start_sec", trimRange.start);
                ytForm.append("end_sec", trimRange.end);
                ytForm.append("preset", selectedPreset);
                ytForm.append("mode", activeMode);
                ytForm.append("video_title", ytVideoData.title || "");
                ytForm.append("custom_settings", JSON.stringify(customSettings));
                ytForm.append("split_minutes", activeSplitMinutes);

                const ytRes = await fetch("/api/youtube/process", {
                    method: "POST",
                    headers: getAuthHeaders(),
                    body: ytForm
                });

                if (!ytRes.ok) {
                    const err = await ytRes.json();
                    throw new Error(err.detail || "YouTube transformation failed");
                }

                const jobData = await ytRes.json();
                jobId = jobData.job_id;
                if (jobData.batch_id && jobData.parts_count) {
                    logTerminal(`[MULTI-PART] Auto-split into ${jobData.parts_count} parts (Batch: ${jobData.batch_id.slice(0,8)})`);
                }

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
        localStorage.setItem("cr_active_job_id", jobId);

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
                if (typeof refreshMyRendersCount === "function") refreshMyRendersCount();
            } else if (data.status === "failed") {
                activeEventSource.close();
                mainStatusText.innerText = "Pipeline Terminated";
                subStatusText.innerText = data.message;
                const failRow = document.getElementById("failureActionRow");
                if (failRow) failRow.style.display = "block";
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
                        if (typeof refreshMyRendersCount === "function") refreshMyRendersCount();
                    } else if (data.status === "failed") {
                        clearInterval(poller);
                        mainStatusText.innerText = "Failed";
                        const failRow = document.getElementById("failureActionRow");
                        if (failRow) failRow.style.display = "block";
                    }
                } catch {
                    clearInterval(poller);
                }
            }, 1200);
        };
    }

    const btnRetryFailed = document.getElementById("btnRetryFailed");
    if (btnRetryFailed) {
        btnRetryFailed.addEventListener("click", () => {
            const failRow = document.getElementById("failureActionRow");
            if (failRow) failRow.style.display = "none";
            progressCard.style.display = "none";
            configCard.style.display = "block";
            localStorage.removeItem("cr_active_job_id");
        });
    }

    const btnCancelActiveJob = document.getElementById("btnCancelActiveJob");
    if (btnCancelActiveJob) {
        btnCancelActiveJob.addEventListener("click", async () => {
            const activeId = localStorage.getItem("cr_active_job_id");
            if (!activeId) {
                progressCard.style.display = "none";
                configCard.style.display = "block";
                return;
            }
            if (!confirm("Are you sure you want to cancel this render? CPU/RAM and disk will be freed immediately.")) return;

            btnCancelActiveJob.disabled = true;
            btnCancelActiveJob.innerText = "Cancelling...";

            try {
                if (activeEventSource) activeEventSource.close();
                const res = await fetch(`/api/jobs/${activeId}/cancel`, {
                    method: "POST",
                    headers: getAuthHeaders()
                });
                const data = await res.json();
                logTerminal(`[CANCELLED] ${data.message || 'Render cancelled.'}`);
            } catch (err) {
                console.error("Error cancelling job", err);
            } finally {
                localStorage.removeItem("cr_active_job_id");
                btnCancelActiveJob.disabled = false;
                btnCancelActiveJob.innerText = "🛑 Cancel Render";
                progressCard.style.display = "none";
                configCard.style.display = "block";
                if (typeof refreshMyRendersCount === "function") refreshMyRendersCount();
            }
        });
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
                const nameWithoutExt = selectedFile.name.substring(0, selectedFile.name.lastIndexOf('.')) || selectedFile.name;
                safeDownloadName = `safe_${nameWithoutExt.replace(/[^a-zA-Z0-9_-]/g, '_')}.mp4`;
            }
            downloadSafeBtn.download = safeDownloadName;

            logTerminal(`[DONE] Video ready for publishing!`);
        }, 600);
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
        localStorage.removeItem("cr_active_job_id");
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

    // ================= AUTH & PERSISTENT SESSION RECOVERY =================
    const btnOpenAuth = document.getElementById("btnOpenAuth");
    const authModal = document.getElementById("authModal");
    const btnCloseAuth = document.getElementById("btnCloseAuth");
    const tabAuthLogin = document.getElementById("tabAuthLogin");
    const tabAuthRegister = document.getElementById("tabAuthRegister");
    const authForm = document.getElementById("authForm");
    const authUsername = document.getElementById("authUsername");
    const authPassword = document.getElementById("authPassword");
    const authError = document.getElementById("authError");
    const btnAuthSubmit = document.getElementById("btnAuthSubmit");
    const authModalTitle = document.getElementById("authModalTitle");

    const userChip = document.getElementById("userChip");
    const userNameLabel = document.getElementById("userNameLabel");
    const btnLogout = document.getElementById("btnLogout");
    const btnOpenMyRenders = document.getElementById("btnOpenMyRenders");
    const renderCountBadge = document.getElementById("renderCountBadge");

    const rendersModal = document.getElementById("rendersModal");
    const btnCloseRenders = document.getElementById("btnCloseRenders");
    const rendersListContainer = document.getElementById("rendersListContainer");
    const btnRefreshRenders = document.getElementById("btnRefreshRenders");

    let authMode = "login"; // 'login' or 'register'
    let currentUser = null;

    function getAuthHeaders() {
        const token = localStorage.getItem("cr_token");
        return token ? { "Authorization": `Bearer ${token}` } : {};
    }

    async function checkCurrentUser() {
        try {
            const res = await fetch("/api/auth/me", {
                headers: getAuthHeaders()
            });
            const data = await res.json();
            if (data.authenticated && data.user) {
                currentUser = data.user;
                updateAuthUI(true, currentUser.username);
                refreshMyRendersCount();
            } else {
                currentUser = null;
                updateAuthUI(false);
            }
        } catch (e) {
            console.error("Auth check failed:", e);
        }
    }

    function updateAuthUI(isLoggedIn, username = "") {
        if (!btnOpenAuth) return;
        if (isLoggedIn) {
            btnOpenAuth.style.display = "none";
            if (userChip) userChip.style.display = "flex";
            if (btnOpenMyRenders) btnOpenMyRenders.style.display = "flex";
            if (userNameLabel) userNameLabel.innerText = `👤 ${username}`;
        } else {
            btnOpenAuth.style.display = "block";
            if (userChip) userChip.style.display = "none";
            if (btnOpenMyRenders) btnOpenMyRenders.style.display = "none";
        }
    }

    async function refreshMyRendersCount() {
        if (!currentUser) return;
        try {
            const res = await fetch("/api/my-renders", {
                headers: getAuthHeaders()
            });
            const data = await res.json();
            if (data.status === "ok" && data.jobs && renderCountBadge) {
                renderCountBadge.innerText = data.jobs.length;
            }
        } catch (e) {
            console.error("Renders count check failed:", e);
        }
    }

    if (btnOpenAuth) {
        btnOpenAuth.addEventListener("click", async () => {
            if (authModal) {
                authModal.style.display = "flex";
                if (authError) authError.style.display = "none";
                
                // Check if registration is locked (private single-user instance)
                try {
                    const statusRes = await fetch("/api/auth/status");
                    const statusData = await statusRes.json();
                    if (statusData.registration_allowed === false && tabAuthRegister) {
                        tabAuthRegister.style.display = "none";
                        authMode = "login";
                        tabAuthLogin.classList.add("active");
                        if (authModalTitle) authModalTitle.innerText = "CR-SHIELD Owner Login";
                        if (btnAuthSubmit) btnAuthSubmit.innerText = "Sign In as Owner";
                    } else if (tabAuthRegister) {
                        tabAuthRegister.style.display = "block";
                    }
                } catch (e) {
                    console.error("Auth status check failed:", e);
                }
            }
        });
    }

    // Auto-refresh when mobile phone screen turns on or user switches back to browser tab
    document.addEventListener("visibilitychange", () => {
        if (document.visibilityState === "visible") {
            refreshMyRendersCount();
            if (rendersModal && rendersModal.style.display === "flex") {
                loadMyRenders();
            }
        }
    });

    if (btnCloseAuth) {
        btnCloseAuth.addEventListener("click", () => {
            if (authModal) authModal.style.display = "none";
        });
    }

    if (tabAuthLogin) {
        tabAuthLogin.addEventListener("click", () => {
            authMode = "login";
            tabAuthLogin.classList.add("active");
            if (tabAuthRegister) tabAuthRegister.classList.remove("active");
            if (btnAuthSubmit) btnAuthSubmit.innerText = "Sign In to Studio";
            if (authModalTitle) authModalTitle.innerText = "Sign In to CR-SHIELD";
            if (authError) authError.style.display = "none";
        });
    }

    if (tabAuthRegister) {
        tabAuthRegister.addEventListener("click", () => {
            authMode = "register";
            tabAuthRegister.classList.add("active");
            if (tabAuthLogin) tabAuthLogin.classList.remove("active");
            if (btnAuthSubmit) btnAuthSubmit.innerText = "Create Account";
            if (authModalTitle) authModalTitle.innerText = "Create Your Account";
            if (authError) authError.style.display = "none";
        });
    }

    if (authForm) {
        authForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const uname = authUsername.value.trim();
            const pword = authPassword.value;
            if (!uname || !pword) return;

            btnAuthSubmit.innerText = "Please wait...";
            btnAuthSubmit.disabled = true;
            if (authError) authError.style.display = "none";

            try {
                const endpoint = authMode === "login" ? "/api/auth/login" : "/api/auth/register";
                const formData = new FormData();
                formData.append("username", uname);
                formData.append("password", pword);

                const res = await fetch(endpoint, {
                    method: "POST",
                    body: formData
                });

                const data = await res.json();
                if (!res.ok) {
                    throw new Error(data.detail || "Authentication failed");
                }

                if (data.token) {
                    localStorage.setItem("cr_token", data.token);
                }
                currentUser = data.user;
                updateAuthUI(true, currentUser.username);
                authModal.style.display = "none";
                authPassword.value = "";
                refreshMyRendersCount();
            } catch (err) {
                if (authError) {
                    authError.innerText = err.message;
                    authError.style.display = "block";
                }
            } finally {
                btnAuthSubmit.innerText = authMode === "login" ? "Sign In to Studio" : "Create Account";
                btnAuthSubmit.disabled = false;
            }
        });
    }

    if (btnLogout) {
        btnLogout.addEventListener("click", async () => {
            try {
                await fetch("/api/auth/logout", {
                    method: "POST",
                    headers: getAuthHeaders()
                });
            } catch {}
            localStorage.removeItem("cr_token");
            currentUser = null;
            updateAuthUI(false);
        });
    }

    if (btnOpenMyRenders) {
        btnOpenMyRenders.addEventListener("click", () => {
            if (rendersModal) rendersModal.style.display = "flex";
            loadMyRenders();
        });
    }

    if (btnCloseRenders) {
        btnCloseRenders.addEventListener("click", () => {
            if (rendersModal) rendersModal.style.display = "none";
        });
    }

    if (btnRefreshRenders) {
        btnRefreshRenders.addEventListener("click", loadMyRenders);
    }

    async function loadMyRenders() {
        if (!rendersListContainer) return;
        rendersListContainer.innerHTML = '<div class="renders-empty-state"><span class="empty-icon">⏳</span><p>Fetching your cloud renders...</p></div>';
        try {
            const res = await fetch("/api/my-renders", {
                headers: getAuthHeaders()
            });
            const data = await res.json();
            if (!res.ok || !data.jobs || data.jobs.length === 0) {
                rendersListContainer.innerHTML = '<div class="renders-empty-state"><span class="empty-icon">🎬</span><p>No renders found yet. Start a video or stream clip to save it here!</p></div>';
                if (renderCountBadge) renderCountBadge.innerText = "0";
                return;
            }

            if (renderCountBadge) renderCountBadge.innerText = data.jobs.length;
            rendersListContainer.innerHTML = "";

            data.jobs.forEach(job => {
                const card = document.createElement("div");
                card.className = "render-item-card";

                const isDone = job.status === "completed";
                const isProc = job.status === "processing";
                const badgeClass = job.status;

                let actionHtml = "";
                if (isDone) {
                    actionHtml = `
                        <a href="/api/download/${job.job_id}" class="btn-render-action btn-render-download" download>⬇️ Download MP4</a>
                        <button type="button" class="btn-render-action btn-render-live" onclick="window.previewSavedJob('${job.job_id}')">🎬 View Player</button>
                        <button type="button" class="btn-render-action btn-render-delete" onclick="window.deleteSavedJob('${job.job_id}')">🗑️ Delete</button>
                    `;
                } else if (isProc || job.status === "queued") {
                    const batchBtn = job.batch_id ? `<button type="button" class="btn-render-action btn-render-cancel" onclick="window.cancelBatch('${job.batch_id}')">🛑 Cancel All Parts</button>` : '';
                    actionHtml = `
                        <button type="button" class="btn-render-action btn-render-live" onclick="window.reconnectJob('${job.job_id}')">⚡ View Live</button>
                        <button type="button" class="btn-render-action btn-render-cancel" onclick="window.cancelJob('${job.job_id}')">🛑 Cancel</button>
                        ${batchBtn}
                    `;
                } else {
                    actionHtml = `
                        <button type="button" class="btn-render-action btn-render-delete" onclick="window.deleteSavedJob('${job.job_id}')">🗑️ Delete Record</button>
                    `;
                }

                card.innerHTML = `
                    <div class="render-item-header">
                        <span class="render-item-title">${escapeHtml(job.filename || 'Untitled Video')}</span>
                        <span class="render-badge-status ${badgeClass}">${job.status}</span>
                    </div>
                    <div class="render-meta-row">
                        <span>Preset: <strong>${job.preset}</strong> (${job.mode})</span>
                        <span>${job.progress ? Math.round(job.progress) + '%' : ''} • ${job.created_at ? job.created_at.slice(0, 16).replace('T', ' ') : ''}</span>
                    </div>
                    ${job.message ? `<div style="font-size:0.72rem; color:#94a3b8;">${escapeHtml(job.message)}</div>` : ''}
                    ${actionHtml ? `<div class="render-item-actions">${actionHtml}</div>` : ''}
                `;
                rendersListContainer.appendChild(card);
            });
        } catch (err) {
            rendersListContainer.innerHTML = `<div class="renders-empty-state" style="color:#fca5a5;"><p>Failed to load renders: ${err.message}</p></div>`;
        }
    }

    function escapeHtml(str) {
        return (str || '').replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
    }

    // Global window handlers for render actions
    window.previewSavedJob = (jobId) => {
        if (rendersModal) rendersModal.style.display = "none";
        configCard.style.display = "none";
        progressCard.style.display = "block";
        processingView.style.display = "none";
        completedView.style.display = "block";

        const downloadUrl = `/api/download/${jobId}`;
        finalVideoPlayer.src = downloadUrl;
        dualCleanPlayer.src = downloadUrl;
        downloadSafeBtn.href = downloadUrl;
        downloadSafeBtn.download = `safe_${jobId.slice(0,8)}.mp4`;
    };

    window.reconnectJob = (jobId) => {
        if (rendersModal) rendersModal.style.display = "none";
        configCard.style.display = "none";
        progressCard.style.display = "block";
        processingView.style.display = "block";
        completedView.style.display = "none";
        subscribeJobStream(jobId);
    };

    window.deleteSavedJob = async (jobId) => {
        if (!confirm("Are you sure you want to delete this video and free disk space?")) return;
        try {
            const res = await fetch(`/api/my-renders/${jobId}`, {
                method: "DELETE",
                headers: getAuthHeaders()
            });
            if (res.ok) {
                if (localStorage.getItem("cr_active_job_id") === jobId) {
                    localStorage.removeItem("cr_active_job_id");
                }
                loadMyRenders();
                refreshMyRendersCount();
            } else {
                const d = await res.json();
                alert(d.detail || "Failed to delete");
            }
        } catch (e) {
            alert("Error deleting job: " + e.message);
        }
    };

    window.cancelJob = async (jobId) => {
        if (!confirm("Are you sure you want to cancel this render?")) return;
        try {
            const res = await fetch(`/api/jobs/${jobId}/cancel`, {
                method: "POST",
                headers: getAuthHeaders()
            });
            const data = await res.json();
            if (localStorage.getItem("cr_active_job_id") === jobId) {
                localStorage.removeItem("cr_active_job_id");
                progressCard.style.display = "none";
                configCard.style.display = "block";
            }
            loadMyRenders();
            if (typeof refreshMyRendersCount === "function") refreshMyRendersCount();
        } catch (e) {
            alert("Error cancelling job: " + e.message);
        }
    };

    window.cancelBatch = async (batchId) => {
        if (!confirm("Are you sure you want to cancel ALL queued and active parts for this video?")) return;
        try {
            const res = await fetch(`/api/batches/${batchId}/cancel`, {
                method: "POST",
                headers: getAuthHeaders()
            });
            const data = await res.json();
            localStorage.removeItem("cr_active_job_id");
            progressCard.style.display = "none";
            configCard.style.display = "block";
            loadMyRenders();
            if (typeof refreshMyRendersCount === "function") refreshMyRendersCount();
        } catch (e) {
            alert("Error cancelling batch: " + e.message);
        }
    };

    // Auto-Resume Active Job on Page Load
    async function checkAndResumeActiveJob() {
        const savedJobId = localStorage.getItem("cr_active_job_id");
        if (!savedJobId) return;

        try {
            const res = await fetch(`/api/jobs/${savedJobId}`);
            if (!res.ok) {
                localStorage.removeItem("cr_active_job_id");
                return;
            }
            const data = await res.json();
            if (data.status === "processing" || data.status === "queued") {
                configCard.style.display = "none";
                progressCard.style.display = "block";
                processingView.style.display = "block";
                completedView.style.display = "none";
                progressBar.style.width = `${Math.round(data.progress)}%`;
                progressPercentLabel.innerText = `${Math.round(data.progress)}%`;
                mainStatusText.innerText = "Resuming Background Render...";
                subStatusText.innerText = data.message;
                subscribeJobStream(savedJobId);
            } else if (data.status === "completed") {
                configCard.style.display = "none";
                progressCard.style.display = "block";
                showCompleted(savedJobId, data);
            }
        } catch {
            localStorage.removeItem("cr_active_job_id");
        }
    }

    // Run auth & recovery on startup
    checkCurrentUser();
    checkAndResumeActiveJob();
});
