"""WAV音声の振幅解析によるリップシンク判定モジュール"""

import math
import wave
from pathlib import Path

import numpy as np


def analyze_mouth_states(
  wav_path: str | Path,
  fps: int,
  threshold: float = 0.15,
  min_open_frames: int = 2,
) -> np.ndarray:
  """WAVファイルから各フレームの口の開閉状態を判定する

  Args:
    wav_path: WAVファイルパス
    fps: 動画のフレームレート
    threshold: 口を開いたとみなす振幅の閾値（0.0-1.0、正規化済み）
    min_open_frames: 口を開いたままにする最低フレーム数（チャタリング防止）

  Returns:
    bool配列。True=口が開いている、False=口が閉じている。
    配列の長さ = ceil(duration * fps)
  """
  with wave.open(str(wav_path), "rb") as wf:
    n_channels = wf.getnchannels()
    sample_width = wf.getsampwidth()
    sample_rate = wf.getframerate()
    n_frames = wf.getnframes()
    raw_data = wf.readframes(n_frames)

  # PCMデータをfloat配列に変換
  if sample_width == 2:
    samples = np.frombuffer(raw_data, dtype=np.int16).astype(np.float32)
  elif sample_width == 4:
    samples = np.frombuffer(raw_data, dtype=np.int32).astype(np.float32)
  elif sample_width == 1:
    samples = np.frombuffer(raw_data, dtype=np.uint8).astype(np.float32) - 128
  else:
    samples = np.frombuffer(raw_data, dtype=np.int16).astype(np.float32)

  # ステレオの場合はモノラルに変換
  if n_channels > 1:
    samples = samples.reshape(-1, n_channels).mean(axis=1)

  # 最大振幅で正規化
  max_amp = np.abs(samples).max()
  if max_amp > 0:
    samples = samples / max_amp

  # フレーム単位でRMS振幅を計算
  duration = n_frames / sample_rate
  total_video_frames = math.ceil(duration * fps)
  samples_per_frame = sample_rate / fps

  rms_per_frame = np.zeros(total_video_frames, dtype=np.float32)
  for i in range(total_video_frames):
    start = int(i * samples_per_frame)
    end = int((i + 1) * samples_per_frame)
    end = min(end, len(samples))
    if start < end:
      frame_samples = samples[start:end]
      rms_per_frame[i] = np.sqrt(np.mean(frame_samples ** 2))

  # 閾値で口の開閉を判定
  mouth_open = rms_per_frame > threshold

  # チャタリング防止: 口を開いたら最低 min_open_frames フレーム維持
  if min_open_frames > 1:
    result = mouth_open.copy()
    i = 0
    while i < len(result):
      if result[i]:
        # 口が開いた → min_open_frames 分は開いたままにする
        end = min(i + min_open_frames, len(result))
        result[i:end] = True
        i = end
      else:
        i += 1
    mouth_open = result

  return mouth_open
