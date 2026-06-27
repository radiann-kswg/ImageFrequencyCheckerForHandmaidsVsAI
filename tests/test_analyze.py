"""analyze モジュールのテスト。"""

from __future__ import annotations

import numpy as np

from img_freq_extractor.analyze import (
    binarize_image,
    compute_information_map,
    jet_colormap,
    local_contrast_map,
    overlay_information_map,
    to_luminance,
)


def test_to_luminance_grayscale_passthrough():
    img = np.arange(16, dtype=np.uint8).reshape(4, 4)
    out = to_luminance(img)
    assert out.shape == (4, 4)
    assert out.dtype == np.float32
    assert np.allclose(out, img.astype(np.float32))


def test_to_luminance_rgb_weights():
    # 純赤・純緑・純青のスポット
    img = np.zeros((1, 3, 3), dtype=np.uint8)
    img[0, 0] = [255, 0, 0]
    img[0, 1] = [0, 255, 0]
    img[0, 2] = [0, 0, 255]
    lum = to_luminance(img)
    # BT.601 重み
    assert abs(lum[0, 0] - 0.299 * 255) < 1e-3
    assert abs(lum[0, 1] - 0.587 * 255) < 1e-3
    assert abs(lum[0, 2] - 0.114 * 255) < 1e-3


def test_local_contrast_flat_is_zero():
    img = np.full((32, 32), 128, dtype=np.uint8)
    out = local_contrast_map(img, window=8)
    assert out.shape == (32, 32)
    assert np.all(out < 1e-3)


def test_local_contrast_higher_on_textured():
    # 平坦領域 + ノイジー領域
    flat = np.full((32, 64), 128, dtype=np.uint8)
    rng = np.random.default_rng(0)
    noisy = rng.integers(0, 255, size=(32, 64), dtype=np.uint8)
    img = np.concatenate([flat, noisy], axis=1)  # shape (32, 128)
    out = local_contrast_map(img, window=8)
    # 平坦領域 (左 1/4) はノイジー領域 (右 3/8) より低い
    left_mean = out[:, :32].mean()
    right_mean = out[:, -32:].mean()
    assert right_mean > left_mean * 3


def test_jet_colormap_range_and_endpoints():
    v = np.array([[0.0, 0.5, 1.0]], dtype=np.float32)
    rgb = jet_colormap(v)
    assert rgb.shape == (1, 3, 3)
    assert rgb.dtype == np.uint8
    # 値域
    assert rgb.min() >= 0 and rgb.max() <= 255
    # 0 (青) は B 成分が他より高い
    assert rgb[0, 0, 2] > rgb[0, 0, 0]
    # 1 (赤) は R 成分が他より高い
    assert rgb[0, 2, 0] > rgb[0, 2, 2]


def test_compute_information_map_shape():
    img = (np.random.rand(40, 50, 3) * 255).astype(np.uint8)
    heatmap, normalized = compute_information_map(img, metric="local_contrast", window=8)
    assert heatmap.shape == (40, 50, 3)
    assert normalized.shape == (40, 50)
    assert normalized.min() >= 0.0 and normalized.max() <= 1.0


def test_overlay_information_map_preserves_shape():
    img = (np.random.rand(20, 30, 3) * 255).astype(np.uint8)
    overlay, heatmap = overlay_information_map(img, metric="luminance", alpha=0.4)
    assert overlay.shape == (20, 30, 3)
    assert heatmap.shape == (20, 30, 3)
    assert overlay.dtype == np.uint8


# ── 二値化 (binarize_image) ──────────────────────────────────────────


def test_binarize_outputs_only_0_or_255():
    rng = np.random.default_rng(0)
    img = rng.integers(0, 256, size=(32, 48, 3), dtype=np.uint8)
    out = binarize_image(img, method="otsu")
    assert out.shape == (32, 48)
    assert out.dtype == np.uint8
    unique = np.unique(out)
    assert set(unique.tolist()).issubset({0, 255})


def test_binarize_fixed_threshold_separates_known_pattern():
    img = np.zeros((4, 4), dtype=np.uint8)
    img[:, 2:] = 200  # 右半分が明るい
    out = binarize_image(img, method="fixed", threshold=100)
    # 閾値 100 で分割: 左半 (0) → 0、右半 (200) → 255
    assert np.all(out[:, :2] == 0)
    assert np.all(out[:, 2:] == 255)


def test_binarize_invert_swaps_black_white():
    img = np.zeros((4, 4), dtype=np.uint8)
    img[:, 2:] = 200
    normal = binarize_image(img, method="fixed", threshold=100, invert=False)
    inv = binarize_image(img, method="fixed", threshold=100, invert=True)
    assert np.array_equal(normal, 255 - inv)


def test_binarize_otsu_threshold_is_between_two_clusters():
    """2 つのクラスタを持つ画像で大津の閾値がクラスタ間に来る。"""
    img = np.full((50, 50), 60, dtype=np.uint8)
    img[:, 25:] = 190
    out = binarize_image(img, method="otsu")
    # 暗い方はすべて 0, 明るい方はすべて 255
    assert np.all(out[:, :25] == 0)
    assert np.all(out[:, 25:] == 255)


def test_binarize_rgb_input_supported():
    img = np.zeros((4, 4, 3), dtype=np.uint8)
    img[:, 2:] = [200, 200, 200]
    out = binarize_image(img, method="fixed", threshold=100)
    assert out.shape == (4, 4)
    assert np.all(out[:, :2] == 0)
    assert np.all(out[:, 2:] == 255)


def test_binarize_invalid_method_raises():
    import pytest

    img = np.zeros((4, 4), dtype=np.uint8)
    with pytest.raises(ValueError):
        binarize_image(img, method="unknown")  # type: ignore[arg-type]


def test_binarize_fixed_threshold_out_of_range_raises():
    import pytest

    img = np.zeros((4, 4), dtype=np.uint8)
    with pytest.raises(ValueError):
        binarize_image(img, method="fixed", threshold=300)
