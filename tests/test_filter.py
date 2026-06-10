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
