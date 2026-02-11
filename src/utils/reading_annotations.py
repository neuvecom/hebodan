"""読み仮名アノテーション処理ユーティリティ

台本テキスト中の `漢字<よみがな>` 形式のアノテーションを処理する。
- TTS用: 漢字部分を読み仮名に置換（例: 大賢者<だいけんじゃ> → だいけんじゃ）
- 表示用: アノテーション部分を除去（例: 大賢者<だいけんじゃ> → 大賢者）
- 辞書: reading_dict.txt から一括置換（TTS専用）

表示専用テキスト `[[テキスト]]` の処理:
- TTS用: [[...]] を丸ごと除去（読み上げない）
- 表示用: [[ と ]] を除去し、中身のテキストだけ残す
"""

import logging
import re
from pathlib import Path

# 辞書エントリ解析用（ひらがな含む: 楽して<らくして> 等に対応）
_READING_PATTERN = re.compile(r'([一-龯々ヶa-zA-Zａ-ｚＡ-Ｚ\u3040-\u309F\u30A0-\u30FF]+)<([^<>]+)>')

# インライン変換用（ひらがな除外: 助詞を跨いで過剰マッチしないようにする）
_INLINE_PATTERN = re.compile(r'([一-龯々ヶa-zA-Zａ-ｚＡ-Ｚ\u30A0-\u30FF]+)<([^<>]+)>')

# 表示専用テキスト [[...]] のパターン
_DISPLAY_ONLY_PATTERN = re.compile(r'\[\[(.+?)\]\]')


def convert_reading_annotations(text: str) -> str:
    """TTS用: アノテーション付きテキストを読み仮名に置換する

    漢字・カタカナ・英字のみマッチし、ひらがな（助詞等）を跨がない。
    例: "飲み水やお湯は何<なん>とかなる" → "飲み水やお湯はなんとかなる"
    """
    return _INLINE_PATTERN.sub(r'\2', text)


def remove_reading_annotations(text: str) -> str:
    """表示用: アノテーション（<...>部分）を除去する

    例: "大賢者<だいけんじゃ>が現れた" → "大賢者が現れた"
    """
    return re.sub(r'<[^<>]+>', '', text)


def strip_display_only(text: str) -> str:
    """TTS用: [[...]] を丸ごと除去する（読み上げない）

    例: "サーモヒーター[[（凍結防止帯）]]つけるか" → "サーモヒーターつけるか"
    """
    return _DISPLAY_ONLY_PATTERN.sub('', text)


def unwrap_display_only(text: str) -> str:
    """表示用: [[ と ]] を除去し、中身のテキストだけ残す

    例: "サーモヒーター[[（凍結防止帯）]]つけるか" → "サーモヒーター（凍結防止帯）つけるか"
    """
    return _DISPLAY_ONLY_PATTERN.sub(r'\1', text)


logger = logging.getLogger(__name__)


def load_reading_dict(path: Path) -> dict[str, str]:
    """読み辞書ファイルを読み込む

    ファイル形式: 1行に1エントリ、「単語<よみ>」形式
    # で始まる行と空行はスキップ

    Args:
      path: 辞書ファイルパス

    Returns:
      {単語: よみ} の辞書。ファイルがなければ空辞書
    """
    if not path.exists():
        return {}

    reading_dict: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = _READING_PATTERN.search(line)
        if match:
            reading_dict[match.group(1)] = match.group(2)
        else:
            logger.warning("読み辞書: 解析できない行をスキップ: %s", line)

    if reading_dict:
        logger.info("読み辞書: %d 件読み込み (%s)", len(reading_dict), path.name)
    return reading_dict


def apply_reading_dict(text: str, reading_dict: dict[str, str]) -> str:
    """辞書に基づいて単語を読みに置換する（TTS用）

    長い単語から優先的にマッチさせる。

    Args:
      text: 置換対象テキスト（インラインアノテーション変換済み）
      reading_dict: {単語: よみ} の辞書

    Returns:
      辞書適用後のテキスト
    """
    if not reading_dict:
        return text
    # 長い単語から置換して部分一致の誤爆を防ぐ
    for word in sorted(reading_dict, key=len, reverse=True):
        text = text.replace(word, reading_dict[word])
    return text
