"""ヘボ談オープニングSE（効果音）を生成するスクリプト

使い方:
  .venv/bin/python scripts/generate_opening_se.py

assets/audio/se/opening.wav に保存します。
ピポパポン♪ な上行アルペジオのヘボいジングルを合成します。
"""

import struct
import sys
import wave
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = PROJECT_ROOT / "assets" / "audio" / "se" / "opening.wav"

SAMPLE_RATE = 44100


def generate_note(
  freq: float,
  duration: float,
  decay: float = 3.0,
  vibrato_hz: float = 0.0,
  vibrato_depth: float = 0.0,
) -> np.ndarray:
  """サイン波の単音を生成する（指数減衰エンベロープ付き）"""
  t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)

  # ビブラート（周波数変調）
  if vibrato_hz > 0:
    freq_mod = freq + vibrato_depth * np.sin(2 * np.pi * vibrato_hz * t)
    phase = 2 * np.pi * np.cumsum(freq_mod) / SAMPLE_RATE
  else:
    phase = 2 * np.pi * freq * t

  # サイン波 × 指数減衰
  wave_data = np.sin(phase) * np.exp(-decay * t)

  # アタック（10ms のフェードイン）
  attack_samples = int(SAMPLE_RATE * 0.01)
  if attack_samples > 0 and attack_samples < len(wave_data):
    attack = np.linspace(0, 1, attack_samples)
    wave_data[:attack_samples] *= attack

  return wave_data


def generate_opening_se() -> np.ndarray:
  """ピポパポン♪ ジングルを合成する"""
  notes = [
    # (周波数, 開始時間, 長さ, 減衰, ビブラートHz, ビブラート深さ)
    (523.25, 0.00, 0.35, 4.0, 0, 0),       # C5
    (659.25, 0.35, 0.35, 4.0, 0, 0),       # E5
    (783.99, 0.70, 0.35, 4.0, 0, 0),       # G5
    (1046.50, 1.05, 1.45, 1.5, 6, 5),      # C6（長め＋ビブラート）
  ]

  total_duration = 2.5
  total_samples = int(SAMPLE_RATE * total_duration)
  output = np.zeros(total_samples, dtype=np.float64)

  for freq, start, dur, decay, vib_hz, vib_depth in notes:
    note = generate_note(freq, dur, decay, vib_hz, vib_depth)
    start_idx = int(SAMPLE_RATE * start)
    end_idx = start_idx + len(note)
    if end_idx > total_samples:
      note = note[:total_samples - start_idx]
      end_idx = total_samples
    output[start_idx:end_idx] += note

  # 簡易リバーブ（50ms 遅延、0.3倍）
  delay_samples = int(SAMPLE_RATE * 0.05)
  reverb = np.zeros_like(output)
  reverb[delay_samples:] = output[:-delay_samples] * 0.3
  output += reverb

  # 正規化（80%ピーク）
  max_amp = np.abs(output).max()
  if max_amp > 0:
    output = output / max_amp * 0.8

  return output


def main():
  print("ヘボ談オープニングSE生成中...")

  se_data = generate_opening_se()

  # 16bit PCM に変換
  pcm_data = (se_data * 32767).astype(np.int16)

  # WAV 書き出し
  OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
  with wave.open(str(OUTPUT_PATH), "wb") as wf:
    wf.setnchannels(1)
    wf.setsampwidth(2)  # 16bit
    wf.setframerate(SAMPLE_RATE)
    wf.writeframes(pcm_data.tobytes())

  duration = len(se_data) / SAMPLE_RATE
  print(f"完了: {OUTPUT_PATH}")
  print(f"  長さ: {duration:.2f}秒")
  print(f"  サンプルレート: {SAMPLE_RATE}Hz")
  print(f"  形式: 16bit PCM モノラル")


if __name__ == "__main__":
  main()
