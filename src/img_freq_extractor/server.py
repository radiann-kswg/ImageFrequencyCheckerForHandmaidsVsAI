"""ローカル Web UI 用の簡易 HTTP サーバ。

設計方針:
    - 標準ライブラリ `http.server` のみで完結（重い依存を増やさない）。
    - 既存の `compose.process_image()` / `filter.apply_cutoff()` を呼ぶだけの
      薄いブリッジ。アルゴリズム本体には触れない。
    - 私的利用前提のため `127.0.0.1` バインドを既定にする
      （外部ネットワークからの到達を防ぐ）。
    - SNS からの画像自動取得は実装しない（手動アップロードのみ）。

エンドポイント:
    GET  /                          → `web/static/index.html`
    GET  /static/<path>             → `web/static/` 配下を配信
    GET  /api/health                → JSON `{"status": "ok", "version": ...}`
    POST /api/process               → multipart/form-data:
                                        image: 画像ファイル (必須)
                                        cutoffs: "50,60,70" 形式 (任意)
                                        mode: "highpass"|"lowpass"|"bandpass"
                                        soft_edge: float (任意)
                                        high_cutoff: float (bandpass 用, 任意)
                                        normalize: "1"|"0" (任意, 既定 "1")
                                        binarize: "1"|"0" (任意, 既定 "0")
                                        binarize_method: "otsu"|"fixed" (任意, 既定 "otsu")
                                        binarize_threshold: 0..255 (任意, fixed 用)
                                        binarize_invert: "1"|"0" (任意, 既定 "0")
                                        info_map: "none"|"luminance"|"local_contrast"|"both"
                                                  (任意, 既定 "both")
                                        info_window: int (任意, 既定 32)
                                        info_alpha: float (任意, 既定 0.5)
                                      → JSON: 入力/各カットオフ/比較画像/
                                              情報量マップを Base64 (data URL) で返却
"""

from __future__ import annotations

import base64
import io
import json
import logging
import re
from dataclasses import dataclass, field
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from . import __version__
from .analyze import BinarizeMethod, InfoMetric, binarize_image, overlay_information_map
from .compose import make_comparison_strip
from .filter import FilterMode, apply_cutoff

logger = logging.getLogger(__name__)

# 静的ファイル配信のルート (パッケージ内 web/static)
_STATIC_ROOT = Path(__file__).parent / "web" / "static"

# アップロード上限 (バイト)。私的利用前提でも DoS 対策として上限を設ける。
MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 MiB

# 配信可能な拡張子と Content-Type
_STATIC_CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
    ".webmanifest": "application/manifest+json",
}

_ALLOWED_MODES: tuple[FilterMode, ...] = ("highpass", "lowpass", "bandpass")
_ALLOWED_INFO_MAPS: tuple[str, ...] = ("none", "luminance", "local_contrast", "both")
_ALLOWED_BINARIZE_METHODS: tuple[BinarizeMethod, ...] = ("otsu", "fixed")


def _parse_bool(raw: str | None, default: bool) -> bool:
    """\"1\"/\"true\"/\"yes\"/\"on\" を True、 \"0\"/\"false\"/\"no\"/\"off\" を False。"""
    if raw is None:
        return default
    s = raw.strip().lower()
    if s in ("1", "true", "yes", "on"):
        return True
    if s in ("0", "false", "no", "off", ""):
        return False
    raise ValueError(f"bool として解釈できません: {raw!r}")


# ── multipart/form-data の最小パーサ ─────────────────────────────────────
# Python 3.13+ で `cgi` モジュールが削除されたため、必要な部分だけ自前で実装。
# 仕様参照: RFC 7578。

_CD_NAME_RE = re.compile(rb'name="([^"]*)"')
_CD_FILENAME_RE = re.compile(rb'filename="([^"]*)"')


@dataclass
class _MultipartPart:
    name: str
    filename: str | None
    content_type: str
    data: bytes


@dataclass
class _MultipartForm:
    """`cgi.FieldStorage` のサブセット互換 API。"""

    parts: dict[str, _MultipartPart] = field(default_factory=dict)

    def __contains__(self, name: str) -> bool:
        return name in self.parts

    def get_first(self, name: str) -> str | None:
        p = self.parts.get(name)
        if p is None:
            return None
        try:
            return p.data.decode("utf-8")
        except UnicodeDecodeError:
            return None

    def get_file(self, name: str) -> _MultipartPart | None:
        return self.parts.get(name)


def _extract_boundary(content_type: str) -> bytes:
    """`multipart/form-data; boundary=xxx` から boundary を取り出す。"""
    for token in content_type.split(";"):
        token = token.strip()
        if token.lower().startswith("boundary="):
            value = token[len("boundary="):].strip().strip('"')
            if not value:
                raise ValueError("空の boundary")
            return value.encode("ascii")
    raise ValueError("Content-Type に boundary が含まれていません")


def _parse_multipart(body: bytes, content_type: str) -> _MultipartForm:
    """multipart/form-data の本体を最小限パースする。"""
    boundary = _extract_boundary(content_type)
    delim = b"--" + boundary
    close_delim = delim + b"--"

    # 分割。末尾の close delimiter まで読み取る。
    # 先頭にプリアンブルがあり得るのでそのまま split しても問題ない。
    segments = body.split(delim)
    form = _MultipartForm()

    for seg in segments:
        # close delimiter の場合
        if seg.startswith(b"--"):
            break
        # 先頭の CRLF を除去 (本体の区切り CRLF)
        if seg.startswith(b"\r\n"):
            seg = seg[2:]
        elif seg.startswith(b"\n"):
            seg = seg[1:]
        if not seg:
            continue
        # 終端の CRLF を除去
        if seg.endswith(b"\r\n"):
            seg = seg[:-2]
        elif seg.endswith(b"\n"):
            seg = seg[:-1]

        # ヘッダーと本文を分離
        header_end = seg.find(b"\r\n\r\n")
        sep_len = 4
        if header_end < 0:
            header_end = seg.find(b"\n\n")
            sep_len = 2
        if header_end < 0:
            # ヘッダーのみのパートは無視
            continue
        header_blob = seg[:header_end]
        data = seg[header_end + sep_len:]

        # ヘッダー解析
        name: str | None = None
        filename: str | None = None
        content_type_part = "application/octet-stream"
        for header_line in header_blob.split(b"\r\n" if sep_len == 4 else b"\n"):
            if not header_line:
                continue
            lower = header_line.lower()
            if lower.startswith(b"content-disposition:"):
                m_name = _CD_NAME_RE.search(header_line)
                if m_name:
                    name = m_name.group(1).decode("utf-8", errors="replace")
                m_file = _CD_FILENAME_RE.search(header_line)
                if m_file:
                    filename = m_file.group(1).decode("utf-8", errors="replace")
            elif lower.startswith(b"content-type:"):
                content_type_part = header_line.split(b":", 1)[1].strip().decode(
                    "ascii", errors="replace"
                )

        if name is None:
            continue
        form.parts[name] = _MultipartPart(
            name=name,
            filename=filename,
            content_type=content_type_part,
            data=data,
        )

    return form


def _encode_png_data_url(arr: np.ndarray) -> str:
    """ndarray を PNG エンコードして data URL に変換。"""
    if arr.ndim == 2:
        im = Image.fromarray(arr, mode="L")
    elif arr.shape[2] == 4:
        im = Image.fromarray(arr, mode="RGBA")
    else:
        im = Image.fromarray(arr, mode="RGB")
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    encoded = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _load_uploaded_image(field_value: bytes) -> np.ndarray:
    """アップロードされたバイト列を ndarray に読み込む。"""
    with Image.open(io.BytesIO(field_value)) as im:
        if im.mode in ("RGB", "L", "RGBA"):
            return np.asarray(im).copy()
        return np.asarray(im.convert("RGB")).copy()


def _parse_cutoffs(raw: str | None) -> list[float]:
    """\"50,60,70\" や \"50 60 70\" を [50.0, 60.0, 70.0] にする。"""
    if not raw:
        return [50.0, 60.0, 70.0]
    parts = [p for p in re.split(r"[\s,]+", raw.strip()) if p]
    try:
        values = [float(p) for p in parts]
    except ValueError as e:
        raise ValueError(f"cutoffs に数値以外が含まれています: {raw!r}") from e
    if not values:
        raise ValueError("cutoffs が空です")
    for v in values:
        if not 0 < v <= 100:
            raise ValueError(f"cutoffs は (0, 100] の範囲にしてください: {v}")
    return values


def _process_request(form: _MultipartForm) -> dict[str, Any]:
    """POST /api/process の本体ロジック。"""
    file_part = form.get_file("image")
    if file_part is None or not file_part.filename:
        raise ValueError("'image' フィールド（画像ファイル）が必要です")

    raw_bytes = file_part.data
    if len(raw_bytes) == 0:
        raise ValueError("アップロード画像が空です")
    if len(raw_bytes) > MAX_UPLOAD_BYTES:
        raise ValueError(
            f"アップロード画像が大きすぎます ({len(raw_bytes)} bytes > "
            f"{MAX_UPLOAD_BYTES} bytes)"
        )

    cutoffs = _parse_cutoffs(form.get_first("cutoffs"))
    mode_raw = (form.get_first("mode") or "highpass").strip().lower()
    if mode_raw not in _ALLOWED_MODES:
        raise ValueError(f"未知のモード: {mode_raw}")
    mode: FilterMode = mode_raw  # type: ignore[assignment]

    soft_edge_raw = form.get_first("soft_edge")
    soft_edge_px = float(soft_edge_raw) if soft_edge_raw else 0.0
    if soft_edge_px < 0:
        raise ValueError("soft_edge は 0 以上にしてください")

    high_cutoff_raw = form.get_first("high_cutoff")
    high_cutoff_percent: float | None = (
        float(high_cutoff_raw) if high_cutoff_raw else None
    )

    normalize = _parse_bool(form.get_first("normalize"), default=True)

    info_map_raw = (form.get_first("info_map") or "both").strip().lower()
    if info_map_raw not in _ALLOWED_INFO_MAPS:
        raise ValueError(f"未知の info_map: {info_map_raw}")

    info_window_raw = form.get_first("info_window")
    info_window = int(info_window_raw) if info_window_raw else 32
    if info_window < 2:
        raise ValueError("info_window は 2 以上にしてください")

    info_alpha_raw = form.get_first("info_alpha")
    info_alpha = float(info_alpha_raw) if info_alpha_raw else 0.5
    if not 0.0 <= info_alpha <= 1.0:
        raise ValueError("info_alpha は 0..1 の範囲にしてください")

    binarize_flag = _parse_bool(form.get_first("binarize"), default=False)
    binarize_method_raw = (form.get_first("binarize_method") or "otsu").strip().lower()
    if binarize_method_raw not in _ALLOWED_BINARIZE_METHODS:
        raise ValueError(f"未知の binarize_method: {binarize_method_raw}")
    binarize_method: BinarizeMethod = binarize_method_raw  # type: ignore[assignment]

    binarize_threshold_raw = form.get_first("binarize_threshold")
    binarize_threshold: float | None = (
        float(binarize_threshold_raw) if binarize_threshold_raw else None
    )
    if binarize_threshold is not None and not 0.0 <= binarize_threshold <= 255.0:
        raise ValueError("binarize_threshold は 0..255 の範囲にしてください")

    binarize_invert = _parse_bool(form.get_first("binarize_invert"), default=False)

    img = _load_uploaded_image(raw_bytes)

    filtered_arrays: list[np.ndarray] = []
    filtered_payload: list[dict[str, Any]] = []
    for cutoff in cutoffs:
        out_arr = apply_cutoff(
            img,
            cutoff_percent=cutoff,
            mode=mode,
            high_cutoff_percent=high_cutoff_percent,
            soft_edge_px=soft_edge_px,
            normalize=normalize,
        )
        if binarize_flag:
            out_arr = binarize_image(
                out_arr,
                method=binarize_method,
                threshold=binarize_threshold,
                invert=binarize_invert,
            )
        filtered_arrays.append(out_arr)
        label_suffix = " · binarized" if binarize_flag else ""
        filtered_payload.append({
            "cutoff": cutoff,
            "label": f"{mode} cutoff {int(cutoff)}%{label_suffix}",
            "data_url": _encode_png_data_url(out_arr),
        })

    strip = make_comparison_strip(
        img, filtered_arrays, labels=[f"{int(c)}" for c in cutoffs]
    )

    # 情報量マップ (Zenn 記事の軽量版実装)
    info_maps_payload: list[dict[str, Any]] = []
    metrics_to_run: list[InfoMetric] = []
    if info_map_raw == "luminance":
        metrics_to_run = ["luminance"]
    elif info_map_raw == "local_contrast":
        metrics_to_run = ["local_contrast"]
    elif info_map_raw == "both":
        metrics_to_run = ["luminance", "local_contrast"]
    for metric in metrics_to_run:
        overlay, heatmap = overlay_information_map(
            img, metric=metric, window=info_window, alpha=info_alpha
        )
        info_maps_payload.append({
            "metric": metric,
            "label": {
                "luminance": "Luminance（明度マップ）",
                "local_contrast": f"Local Contrast（窓 {info_window}px の輝度標準偏差）",
            }[metric],
            "overlay_data_url": _encode_png_data_url(overlay),
            "heatmap_data_url": _encode_png_data_url(heatmap),
        })

    return {
        "mode": mode,
        "cutoffs": cutoffs,
        "soft_edge_px": soft_edge_px,
        "high_cutoff_percent": high_cutoff_percent,
        "normalize": normalize,
        "binarize": binarize_flag,
        "binarize_method": binarize_method,
        "binarize_threshold": binarize_threshold,
        "binarize_invert": binarize_invert,
        "info_map": info_map_raw,
        "info_window": info_window,
        "info_alpha": info_alpha,
        "input": {
            "filename": file_part.filename,
            "width": int(img.shape[1]),
            "height": int(img.shape[0]),
            "data_url": _encode_png_data_url(img),
        },
        "filtered": filtered_payload,
        "comparison": {
            "label": "comparison strip",
            "data_url": _encode_png_data_url(strip),
        },
        "info_maps": info_maps_payload,
    }


class _Handler(BaseHTTPRequestHandler):
    # HTTP `Server` ヘッダ用の ASCII 識別子。表示名は日本語 ("対生成AI判別用 画像周波数分布解析ツール")。
    server_version = f"ImgFreqAnalyzer/{__version__}"

    # ---- 共通ユーティリティ ------------------------------------------------

    def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_error_json(self, status: HTTPStatus, message: str) -> None:
        self._send_json(status, {"error": message})

    def _send_static(self, rel_path: str) -> None:
        # パストラバーサル防止: STATIC_ROOT 配下に解決される場合のみ許可。
        rel_clean = rel_path.lstrip("/")
        target = (_STATIC_ROOT / rel_clean).resolve()
        try:
            target.relative_to(_STATIC_ROOT.resolve())
        except ValueError:
            self._send_error_json(HTTPStatus.FORBIDDEN, "禁止されたパスです")
            return
        if not target.is_file():
            self._send_error_json(HTTPStatus.NOT_FOUND, "ファイルが見つかりません")
            return

        content_type = _STATIC_CONTENT_TYPES.get(
            target.suffix.lower(), "application/octet-stream"
        )
        data = target.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        # 既定の標準エラー出力ではなく logging に流す。
        logger.info("%s - %s", self.address_string(), format % args)

    # ---- GET --------------------------------------------------------------

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html"):
            self._send_static("index.html")
            return
        if path == "/api/health":
            self._send_json(
                HTTPStatus.OK,
                {"status": "ok", "version": __version__},
            )
            return
        if path.startswith("/static/"):
            self._send_static(path[len("/static/"):])
            return
        # ルート直下の静的ファイル（style.css / app.js 等）にも対応
        if "/" not in path.lstrip("/"):
            self._send_static(path.lstrip("/"))
            return
        self._send_error_json(HTTPStatus.NOT_FOUND, "未知のパスです")

    # ---- POST -------------------------------------------------------------

    def do_POST(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        if path != "/api/process":
            self._send_error_json(HTTPStatus.NOT_FOUND, "未知のパスです")
            return

        content_length = int(self.headers.get("Content-Length") or 0)
        if content_length <= 0:
            self._send_error_json(HTTPStatus.BAD_REQUEST, "空のリクエストです")
            return
        if content_length > MAX_UPLOAD_BYTES:
            self._send_error_json(
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                f"リクエストが大きすぎます (>{MAX_UPLOAD_BYTES} bytes)",
            )
            return

        ctype = self.headers.get("Content-Type", "")
        if not ctype.lower().startswith("multipart/form-data"):
            self._send_error_json(
                HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
                "multipart/form-data が必要です",
            )
            return

        try:
            body = self.rfile.read(content_length)
        except OSError as e:
            self._send_error_json(HTTPStatus.BAD_REQUEST, f"リクエスト読み込み失敗: {e}")
            return

        try:
            form = _parse_multipart(body, ctype)
        except ValueError as e:
            self._send_error_json(HTTPStatus.BAD_REQUEST, f"フォーム解析失敗: {e}")
            return

        try:
            payload = _process_request(form)
        except ValueError as e:
            self._send_error_json(HTTPStatus.BAD_REQUEST, str(e))
            return
        except OSError as e:
            self._send_error_json(HTTPStatus.BAD_REQUEST, f"画像読み込み失敗: {e}")
            return
        except Exception as e:  # 想定外: 500 にして詳細はログのみ。
            logger.exception("unexpected error in /api/process")
            self._send_error_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                f"内部エラー: {type(e).__name__}",
            )
            return

        self._send_json(HTTPStatus.OK, payload)


def build_server(host: str = "127.0.0.1", port: int = 4165) -> ThreadingHTTPServer:
    """テスト・組み込み起動用のファクトリ。"""
    return ThreadingHTTPServer((host, port), _Handler)


def serve(host: str = "127.0.0.1", port: int = 4165) -> int:
    """フォアグラウンドでサーバを起動する。Ctrl+C で停止。

    Returns:
        終了コード (0 = 正常終了)。
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    if not _STATIC_ROOT.is_dir():
        logger.error("静的ファイルディレクトリが見つかりません: %s", _STATIC_ROOT)
        return 1

    httpd = build_server(host=host, port=port)
    url = f"http://{host}:{port}/"
    logger.info("対生成AI判別用 画像周波数分布解析ツール Web UI を起動: %s", url)
    logger.info("停止: Ctrl+C")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("停止要求を受信。シャットダウン中...")
    finally:
        httpd.server_close()
    return 0
