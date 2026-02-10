"""Hebodan データモデル定義"""

from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class DialogueLine:
  """台本の1行（セリフ）を表すデータモデル"""
  speaker: str
  text: str
  emotion: str = "normal"


@dataclass
class ScriptMeta:
  """台本のメタ情報"""
  theme: str
  title: str


@dataclass
class ScriptData:
  """LLMが生成する台本全体のデータモデル"""
  meta: ScriptMeta
  dialogue: list[DialogueLine]
  note_content: str
  x_post_content: str

  @classmethod
  def from_dict(cls, data: dict) -> ScriptData:
    """JSON辞書からScriptDataを生成する"""
    meta = ScriptMeta(
      theme=data["meta"]["theme"],
      title=data["meta"]["title"],
    )
    dialogue = [
      DialogueLine(
        speaker=line["speaker"],
        text=line["text"],
        emotion=line.get("emotion", "normal"),
      )
      for line in data["dialogue"]
    ]
    return cls(
      meta=meta,
      dialogue=dialogue,
      note_content=data["note_content"],
      x_post_content=data["x_post_content"],
    )
