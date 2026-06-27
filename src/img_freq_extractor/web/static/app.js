// 対生成AI判別用 画像周波数分布解析ツール — Web UI フロントエンド
// (ES Modules / バニラ JS)
//
// 役割:
//   1. フォーム入力を multipart/form-data として POST /api/process に送る。
//   2. レスポンスの data URL を X/Twitter 風カードに差し込む。
//   3. 入出力の各画像にダウンロードリンクを付与する。
//
// 外部 CDN / フレームワークは使用しない（参照サイトのスタックに合わせる）。

const $ = (sel) => document.querySelector(sel);

const els = {
	form: $("#filter-form"),
	imageInput: $("#image-input"),
	modeInput: $("#mode-input"),
	cutoffsInput: $("#cutoffs-input"),
	softEdgeInput: $("#soft-edge-input"),
	highCutoffField: $("#high-cutoff-field"),
	highCutoffInput: $("#high-cutoff-input"),
	normalizeInput: $("#normalize-input"),
	binarizeInput: $("#binarize-input"),
	binarizeInvertInput: $("#binarize-invert-input"),
	binarizeMethodInput: $("#binarize-method-input"),
	binarizeThresholdField: $("#binarize-threshold-field"),
	binarizeThresholdInput: $("#binarize-threshold-input"),
	infoMapInput: $("#info-map-input"),
	infoWindowInput: $("#info-window-input"),
	infoAlphaInput: $("#info-alpha-input"),
	runButton: $("#run-button"),
	resetButton: $("#reset-button"),
	status: $("#status"),
	resultSection: $("#result-section"),
	inputMeta: $("#input-meta"),
	inputTime: $("#input-time"),
	inputMedia: $("#input-media"),
	outputMeta: $("#output-meta"),
	outputTime: $("#output-time"),
	outputBody: $("#output-body"),
	outputMedia: $("#output-media"),
	comparisonMedia: $("#comparison-media"),
	infoCard: $("#info-card"),
	infoMeta: $("#info-meta"),
	infoTime: $("#info-time"),
	infoMapsContainer: $("#info-maps-container"),
};

// ── 補助 ───────────────────────────────────────────────────────────
function setStatus(text, kind = "") {
	els.status.textContent = text;
	els.status.className = "status" + (kind ? ` ${kind}` : "");
}

function fmtTime(d) {
	const pad = (n) => String(n).padStart(2, "0");
	return `${d.getFullYear()}/${pad(d.getMonth() + 1)}/${pad(d.getDate())} `
		+ `${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function safeFilename(name) {
	// 拡張子を強制 .png に。パス区切りを除去。
	const base = (name || "image").replace(/[\\/]+/g, "_").replace(/\.[^.]+$/, "");
	return `${base || "image"}.png`;
}

function makeMediaCell({ dataUrl, label, downloadName }) {
	const cell = document.createElement("div");
	cell.className = "cell";

	const img = document.createElement("img");
	img.src = dataUrl;
	img.alt = label || "";
	cell.appendChild(img);

	if (label) {
		const tag = document.createElement("span");
		tag.className = "media-label";
		tag.textContent = label;
		cell.appendChild(tag);
	}

	if (downloadName) {
		const a = document.createElement("a");
		a.className = "media-download";
		a.href = dataUrl;
		a.download = downloadName;
		a.textContent = "⬇ 保存";
		cell.appendChild(a);
	}
	return cell;
}

function renderInputCard(payload) {
	const { input } = payload;
	els.inputMeta.textContent =
		`@local · ${input.filename} · ${input.width}×${input.height}px`;
	els.inputTime.textContent = fmtTime(new Date());
	els.inputMedia.replaceChildren(
		makeMediaCell({
			dataUrl: input.data_url,
			label: "Original",
			downloadName: safeFilename(`${input.filename}_input`),
		})
	);
}

function renderOutputCard(payload) {
	const {
		mode,
		cutoffs,
		soft_edge_px,
		high_cutoff_percent,
		normalize,
		binarize,
		binarize_method,
		binarize_threshold,
		binarize_invert,
		filtered,
		input,
	} = payload;
	const bodyParts = [
		`mode = ${mode}`,
		`cutoffs = [${cutoffs.map((c) => Number(c).toString()).join(", ")}]`,
	];
	if (soft_edge_px) bodyParts.push(`soft_edge = ${soft_edge_px} px`);
	if (mode === "bandpass" && high_cutoff_percent != null) {
		bodyParts.push(`high_cutoff = ${high_cutoff_percent}%`);
	}
	bodyParts.push(`normalize = ${normalize ? "on" : "off"}`);
	if (binarize) {
		const thr =
			binarize_method === "fixed"
				? `fixed(${binarize_threshold ?? 127})`
				: "otsu";
		bodyParts.push(`binarize = ${thr}${binarize_invert ? " inverted" : ""}`);
	}
	els.outputBody.textContent = bodyParts.join(" / ");

	els.outputMeta.textContent =
		`@img_freq_extractor · ${filtered.length} frame${filtered.length === 1 ? "" : "s"}`;
	els.outputTime.textContent = fmtTime(new Date());

	// 1〜4 枚のグリッドクラスを切り替え
	els.outputMedia.className = "tweet-media grid";
	const n = Math.min(filtered.length, 4);
	if (n >= 2) els.outputMedia.classList.add(`n${n}`);

	// 5 枚以上の場合は最初の 4 枚のみグリッドに（X の挙動に近い）。
	// 残りも下に並べる。
	els.outputMedia.replaceChildren();
	const stemBase = (input.filename || "image").replace(/\.[^.]+$/, "");
	const fileSuffix = binarize ? "_bin" : "";
	filtered.forEach((f, idx) => {
		const cell = makeMediaCell({
			dataUrl: f.data_url,
			label: f.label,
			downloadName: `${stemBase}_${mode}_cutoff${Math.round(f.cutoff)}${fileSuffix}.png`,
		});
		els.outputMedia.appendChild(cell);
	});

	// 比較ストリップ
	const compImg = document.createElement("img");
	compImg.src = payload.comparison.data_url;
	compImg.alt = "comparison strip";
	els.comparisonMedia.replaceChildren(compImg);

	// 比較画像にもダウンロードリンク
	const wrap = document.createElement("div");
	wrap.style.marginTop = "8px";
	const a = document.createElement("a");
	a.href = payload.comparison.data_url;
	a.download = `${stemBase}_compare.png`;
	a.textContent = "⬇ 比較画像を保存";
	a.className = "media-download";
	a.style.position = "static";
	a.style.display = "inline-block";
	wrap.appendChild(a);
	els.comparisonMedia.appendChild(wrap);
}

function renderInfoMapsCard(payload) {
	const maps = payload.info_maps || [];
	if (maps.length === 0) {
		els.infoCard.hidden = true;
		return;
	}
	els.infoCard.hidden = false;
	els.infoMeta.textContent =
		`@info_map · window ${payload.info_window}px · alpha ${payload.info_alpha}`;
	els.infoTime.textContent = fmtTime(new Date());

	const stemBase = (payload.input.filename || "image").replace(/\.[^.]+$/, "");
	els.infoMapsContainer.replaceChildren();

	for (const m of maps) {
		const block = document.createElement("section");
		block.className = "info-map-block";

		const h3 = document.createElement("h3");
		h3.textContent = m.label;
		block.appendChild(h3);

		const pair = document.createElement("div");
		pair.className = "pair";

		const figOverlay = document.createElement("figure");
		const imgOverlay = document.createElement("img");
		imgOverlay.src = m.overlay_data_url;
		imgOverlay.alt = `${m.metric} overlay`;
		const capOverlay = document.createElement("figcaption");
		capOverlay.textContent = "Overlay";
		figOverlay.appendChild(imgOverlay);
		figOverlay.appendChild(capOverlay);
		pair.appendChild(figOverlay);

		const figHeat = document.createElement("figure");
		const imgHeat = document.createElement("img");
		imgHeat.src = m.heatmap_data_url;
		imgHeat.alt = `${m.metric} heatmap`;
		const capHeat = document.createElement("figcaption");
		capHeat.textContent = "Heatmap";
		figHeat.appendChild(imgHeat);
		figHeat.appendChild(capHeat);
		pair.appendChild(figHeat);

		block.appendChild(pair);

		const links = document.createElement("div");
		links.style.marginTop = "6px";
		links.style.display = "flex";
		links.style.gap = "8px";
		const dlOverlay = document.createElement("a");
		dlOverlay.href = m.overlay_data_url;
		dlOverlay.download = `${stemBase}_${m.metric}_overlay.png`;
		dlOverlay.textContent = "⬇ Overlay 保存";
		dlOverlay.className = "media-download";
		dlOverlay.style.position = "static";
		const dlHeat = document.createElement("a");
		dlHeat.href = m.heatmap_data_url;
		dlHeat.download = `${stemBase}_${m.metric}_heatmap.png`;
		dlHeat.textContent = "⬇ Heatmap 保存";
		dlHeat.className = "media-download";
		dlHeat.style.position = "static";
		links.appendChild(dlOverlay);
		links.appendChild(dlHeat);
		block.appendChild(links);

		els.infoMapsContainer.appendChild(block);
	}
}

// ── イベント ───────────────────────────────────────────────────────
els.modeInput.addEventListener("change", () => {
	els.highCutoffField.hidden = els.modeInput.value !== "bandpass";
});

function updateBinarizeThresholdVisibility() {
	const enabled =
		els.binarizeInput.checked && els.binarizeMethodInput.value === "fixed";
	els.binarizeThresholdField.hidden = !enabled;
}
els.binarizeInput.addEventListener("change", updateBinarizeThresholdVisibility);
els.binarizeMethodInput.addEventListener(
	"change",
	updateBinarizeThresholdVisibility,
);
updateBinarizeThresholdVisibility();

els.resetButton.addEventListener("click", () => {
	els.form.reset();
	els.highCutoffField.hidden = true;
	els.resultSection.hidden = true;
	els.infoCard.hidden = true;
	updateBinarizeThresholdVisibility();
	setStatus("");
});

els.form.addEventListener("submit", async (ev) => {
	ev.preventDefault();
	const file = els.imageInput.files?.[0];
	if (!file) {
		setStatus("画像を選択してください", "err");
		return;
	}

	const fd = new FormData();
	fd.append("image", file);
	fd.append("cutoffs", els.cutoffsInput.value);
	fd.append("mode", els.modeInput.value);
	fd.append("soft_edge", els.softEdgeInput.value || "0");
	if (els.modeInput.value === "bandpass" && els.highCutoffInput.value) {
		fd.append("high_cutoff", els.highCutoffInput.value);
	}
	fd.append("normalize", els.normalizeInput.checked ? "1" : "0");
	fd.append("binarize", els.binarizeInput.checked ? "1" : "0");
	fd.append("binarize_method", els.binarizeMethodInput.value);
	if (
		els.binarizeInput.checked &&
		els.binarizeMethodInput.value === "fixed" &&
		els.binarizeThresholdInput.value !== ""
	) {
		fd.append("binarize_threshold", els.binarizeThresholdInput.value);
	}
	fd.append("binarize_invert", els.binarizeInvertInput.checked ? "1" : "0");
	fd.append("info_map", els.infoMapInput.value);
	fd.append("info_window", els.infoWindowInput.value || "32");
	fd.append("info_alpha", els.infoAlphaInput.value || "0.5");

	els.runButton.disabled = true;
	setStatus("処理中…", "");
	const t0 = performance.now();
	try {
		const res = await fetch("/api/process", { method: "POST", body: fd });
		const payload = await res.json().catch(() => ({}));
		if (!res.ok) {
			throw new Error(payload.error || `HTTP ${res.status}`);
		}
		renderInputCard(payload);
		renderOutputCard(payload);
		renderInfoMapsCard(payload);
		els.resultSection.hidden = false;
		const ms = Math.round(performance.now() - t0);
		setStatus(`完了 (${ms} ms)`, "ok");
		els.resultSection.scrollIntoView({ behavior: "smooth", block: "start" });
	} catch (e) {
		setStatus(`エラー: ${e.message}`, "err");
	} finally {
		els.runButton.disabled = false;
	}
});

// ── 起動時ヘルスチェック ──────────────────────────────────────────
(async () => {
	try {
		const res = await fetch("/api/health");
		const data = await res.json();
		setStatus(`サーバ準備完了 (v${data.version})`, "ok");
	} catch {
		setStatus("サーバに接続できません", "err");
	}
})();
