"""PNG画像の背景を透過にするスクリプト

rembg (U2Net) を使った AI ベースの背景除去を行い、
アルファチャンネルに透過情報を焼き込む。
元画像は _backup/ にバックアップされる。
"""

import shutil
from pathlib import Path

import numpy as np
from PIL import Image
from rembg import remove

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets" / "images"
BACKUP_DIR = ASSETS_DIR / "_backup"

# 処理対象ディレクトリ
TARGET_DIRS = ["tsuno", "megane", "logo"]


def process_image(img_path: Path) -> None:
  """rembg で背景を除去して上書き保存する"""
  # バックアップがあれば常にバックアップから読み込む（再実行対応）
  backup_path = BACKUP_DIR / img_path.relative_to(ASSETS_DIR)
  source_path = backup_path if backup_path.exists() else img_path

  img = Image.open(source_path).convert("RGBA")

  # rembg で背景除去
  result = remove(img)

  # 透過ピクセルの割合を表示
  arr = np.array(result)
  opaque_pct = 100 * (arr[:, :, 3] > 128).sum() / arr[:, :, 3].size
  print(f"  OK: {img_path.name} ({opaque_pct:.1f}% opaque)")

  result.save(img_path, "PNG")


def main() -> None:
  # バックアップ作成
  BACKUP_DIR.mkdir(parents=True, exist_ok=True)

  for dir_name in TARGET_DIRS:
    src_dir = ASSETS_DIR / dir_name
    if not src_dir.is_dir():
      print(f"SKIP directory: {src_dir}")
      continue

    # バックアップ
    backup_dest = BACKUP_DIR / dir_name
    if not backup_dest.exists():
      shutil.copytree(src_dir, backup_dest)
      print(f"Backup: {src_dir} -> {backup_dest}")
    else:
      print(f"Backup exists: {backup_dest}")

    # 画像処理
    print(f"\nProcessing {dir_name}/:")
    for png in sorted(src_dir.glob("*.png")):
      process_image(png)

  # ルートのレガシー画像もバックアップ・処理
  for legacy in ["ririn.png", "tsukuyomi.png"]:
    legacy_path = ASSETS_DIR / legacy
    if legacy_path.exists():
      backup_path = BACKUP_DIR / legacy
      if not backup_path.exists():
        shutil.copy2(legacy_path, backup_path)
        print(f"\nBackup: {legacy}")
      print(f"\nProcessing {legacy}:")
      process_image(legacy_path)


if __name__ == "__main__":
  main()
