"""filter モジュールのスモークテスト。pytest があれば動く。"""

from __future__ import annotations

import numpy as np

from img_freq_extractor.filter import apply_cutoff, build_circular_mask


def test_mask_shape_and_range():
    mask = build_circular_mask((100, 80), cutoff_percent=50, mode="highpass")
    assert mask.shape == (100, 80)
    assert mask.dtype == np.float32
    assert mask.min() >= 0.0 and mask.max() <= 1.0


def test_highpass_lowpass_complementary():
    shape = (64, 64)
    hp = build_circular_mask(shape, 50, mode="highpass")
    lp = build_circular_mask(shape, 50, mode="lowpass")
    # 境界の単一ピクセルを除けば、ほぼ補完関係になる
    union = np.clip(hp + lp, 0, 1)
    assert union.mean() > 0.99


def test_apply_cutoff_preserves_shape_dtype():
    img = (np.random.rand(48, 64, 3) * 255).astype(np.uint8)
    out = apply_cutoff(img, cutoff_percent=60, mode="highpass")
    assert out.shape == img.shape
    assert out.dtype == np.uint8


def test_lowpass_preserves_mean():
    """ローパスでもオフセット（平均値）は実装上維持される。"""
    img = (np.random.rand(32, 32) * 200 + 20).astype(np.uint8)
    out = apply_cutoff(img, cutoff_percent=80, mode="lowpass")
    # 平均値は ±1 程度の範囲で保たれる（実装は mean を引いて戻すため）
    assert abs(int(out.mean()) - int(img.mean())) <= 2


def test_highpass_on_flat_keeps_dc():
    """フラット画像 + 高い cutoff の highpass:
    実装は事前に mean を引いてから FFT するため、フラット画像では
    結果が元の平均値のまま保たれる（境界アーチファクト軽減の設計）。"""
    img = np.full((32, 32), 128, dtype=np.uint8)
    out = apply_cutoff(img, cutoff_percent=10, mode="highpass")
    # フラットな入力は変化しない
    assert np.all(out == 128)


def test_highpass_removes_low_freq_on_gradient():
    """グラデーション画像にハイパスを掛けると低周波（緩やかな変化）が
    削られ、結果のコントラスト幅が元より狭くなる。"""
    grad = np.tile(np.linspace(20, 230, 64, dtype=np.uint8), (64, 1))
    out = apply_cutoff(grad, cutoff_percent=30, mode="highpass")
    # 元画像の振れ幅 (230-20=210) より、ハイパス後の振れ幅は十分小さい
    assert int(out.max()) - int(out.min()) < 150


def test_normalize_expands_dynamic_range_on_highpass():
    """normalize=True にすると highpass 出力のレンジが広がり、視認しやすくなる。"""
    rng = np.random.default_rng(42)
    img = rng.integers(180, 230, size=(64, 64, 3), dtype=np.uint8)
    # 既定 (normalize=False): 平均輝度付近に潰れる
    raw = apply_cutoff(img, cutoff_percent=50, mode="highpass")
    norm = apply_cutoff(img, cutoff_percent=50, mode="highpass", normalize=True)
    raw_range = int(raw.max()) - int(raw.min())
    norm_range = int(norm.max()) - int(norm.min())
    # 正規化版は素のレンジより明確に広い
    assert norm_range > raw_range + 50


def test_normalize_preserves_color_balance():
    """normalize の正規化は全チャネル共通スケールで色相を壊さないこと。
    特定チャネルに偏ったゲインを掛けないため、平均値の偏差は中央 (127.5) 付近に揃う。
    """
    rng = np.random.default_rng(0)
    img = rng.integers(100, 200, size=(48, 48, 3), dtype=np.uint8)
    out = apply_cutoff(img, cutoff_percent=50, mode="highpass", normalize=True)
    # 各チャネルの平均は中央 127.5 周辺に来る (フラット気味の入力でも崩れない)
    means = [float(out[..., ch].mean()) for ch in range(3)]
    for m in means:
        assert 110 < m < 145
    # チャネル間の平均差が小さい (色相が大きく崩れていない)
    assert max(means) - min(means) < 25


def test_normalize_does_not_affect_lowpass():
    """lowpass では normalize=True/False で結果が等しいこと（DC を含むため不要）。"""
    rng = np.random.default_rng(1)
    img = rng.integers(50, 200, size=(32, 32, 3), dtype=np.uint8)
    a = apply_cutoff(img, cutoff_percent=80, mode="lowpass", normalize=False)
    b = apply_cutoff(img, cutoff_percent=80, mode="lowpass", normalize=True)
    assert np.array_equal(a, b)


def test_color_image_filter_per_channel_not_all_white():
    """カラー画像のフィルタ結果が白一色 (255) に潰れない（バグリグレッション）。"""
    rng = np.random.default_rng(7)
    img = rng.integers(0, 256, size=(64, 64, 3), dtype=np.uint8)
    out = apply_cutoff(img, cutoff_percent=50, mode="highpass", normalize=True)
    assert out.shape == img.shape
    # 全画素が 255 ではない、かつ全画素が 0 でもない
    assert not np.all(out == 255)
    assert not np.all(out == 0)
    # チャネル間にバリエーションがある (グレースケール化していない)
    diff = np.abs(out[..., 0].astype(int) - out[..., 1].astype(int))
    assert diff.mean() > 1.0
