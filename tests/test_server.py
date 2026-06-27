"""server モジュールのスモークテスト。

実 HTTP サーバをスレッドで起動して、最低限の経路を確認する。
重い E2E は行わず、`/api/health` と `/api/process` の正常系・主要異常系のみ。
"""

from __future__ import annotations

import io
import json
import socket
import threading
import time
import urllib.error
import urllib.request
import uuid

import numpy as np
import pytest
from PIL import Image

from img_freq_extractor.server import build_server


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture()
def server():
    port = _free_port()
    httpd = build_server(host="127.0.0.1", port=port)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    # サーバ起動を待つ
    for _ in range(50):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=1):
                break
        except urllib.error.URLError:
            time.sleep(0.02)
    yield port
    httpd.shutdown()
    httpd.server_close()
    thread.join(timeout=2)


def _png_bytes(width: int = 32, height: int = 32) -> bytes:
    arr = (np.random.rand(height, width, 3) * 255).astype(np.uint8)
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format="PNG")
    return buf.getvalue()


def _multipart(fields: dict[str, str], files: dict[str, tuple[str, bytes, str]]) -> tuple[bytes, str]:
    """シンプルな multipart/form-data 生成。"""
    boundary = f"----testboundary{uuid.uuid4().hex}"
    lines: list[bytes] = []
    for name, value in fields.items():
        lines.append(f"--{boundary}".encode())
        lines.append(f'Content-Disposition: form-data; name="{name}"'.encode())
        lines.append(b"")
        lines.append(value.encode("utf-8"))
    for name, (filename, content, ctype) in files.items():
        lines.append(f"--{boundary}".encode())
        lines.append(
            f'Content-Disposition: form-data; name="{name}"; filename="{filename}"'.encode()
        )
        lines.append(f"Content-Type: {ctype}".encode())
        lines.append(b"")
        lines.append(content)
    lines.append(f"--{boundary}--".encode())
    lines.append(b"")
    body = b"\r\n".join(lines)
    return body, f"multipart/form-data; boundary={boundary}"


def test_health(server):
    with urllib.request.urlopen(f"http://127.0.0.1:{server}/api/health") as r:
        assert r.status == 200
        data = json.loads(r.read().decode("utf-8"))
        assert data["status"] == "ok"
        assert "version" in data


def test_static_index(server):
    with urllib.request.urlopen(f"http://127.0.0.1:{server}/") as r:
        assert r.status == 200
        body = r.read().decode("utf-8")
        # 日本語タイトルが含まれていること（旧名 ImgFreqExtractor からの改名検証）
        assert "対生成AI判別用 画像周波数分布解析ツール" in body


def test_process_image_roundtrip(server):
    body, ctype = _multipart(
        fields={"cutoffs": "50, 70", "mode": "highpass"},
        files={"image": ("sample.png", _png_bytes(64, 48), "image/png")},
    )
    req = urllib.request.Request(
        f"http://127.0.0.1:{server}/api/process",
        data=body,
        headers={"Content-Type": ctype},
        method="POST",
    )
    with urllib.request.urlopen(req) as r:
        assert r.status == 200
        payload = json.loads(r.read().decode("utf-8"))

    assert payload["mode"] == "highpass"
    assert payload["cutoffs"] == [50.0, 70.0]
    assert payload["input"]["width"] == 64
    assert payload["input"]["height"] == 48
    assert payload["input"]["data_url"].startswith("data:image/png;base64,")
    assert len(payload["filtered"]) == 2
    for f in payload["filtered"]:
        assert f["data_url"].startswith("data:image/png;base64,")
    assert payload["comparison"]["data_url"].startswith("data:image/png;base64,")


def test_process_missing_image(server):
    body, ctype = _multipart(fields={"cutoffs": "50"}, files={})
    req = urllib.request.Request(
        f"http://127.0.0.1:{server}/api/process",
        data=body,
        headers={"Content-Type": ctype},
        method="POST",
    )
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        urllib.request.urlopen(req)
    assert exc_info.value.code == 400


def test_process_invalid_cutoffs(server):
    body, ctype = _multipart(
        fields={"cutoffs": "abc"},
        files={"image": ("a.png", _png_bytes(16, 16), "image/png")},
    )
    req = urllib.request.Request(
        f"http://127.0.0.1:{server}/api/process",
        data=body,
        headers={"Content-Type": ctype},
        method="POST",
    )
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        urllib.request.urlopen(req)
    assert exc_info.value.code == 400
