"""毎日の記念日を Wikipedia から取得して Resend でメール送信するスクリプト

使い方:
  # 環境変数を設定して実行（今日+7日先まで）
  RESEND_API_KEY=xxx EMAIL_TO=xxx EMAIL_FROM=xxx python scripts/daily_kinenbi.py

  # 日付を指定（テスト用）
  python scripts/daily_kinenbi.py --date 2026-02-12

  # 先読み日数を変更（0で当日のみ、デフォルト7）
  python scripts/daily_kinenbi.py --days-ahead 3
"""

import argparse
import os
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

# ローカル実行時は .env を読み込む
_env_path = Path(__file__).resolve().parent.parent / ".env"
if _env_path.exists():
  try:
    from dotenv import load_dotenv
    load_dotenv(_env_path)
  except ImportError:
    pass

JST = timezone(timedelta(hours=9))

WIKIPEDIA_API = "https://ja.wikipedia.org/w/api.php"


def fetch_kinenbi(month: int, day: int) -> list[str]:
  """Wikipedia 日本語版から指定日の記念日・年中行事を取得する"""
  page_title = f"{month}月{day}日"

  # MediaWiki API でページのウィキテキストを取得
  params = {
    "action": "parse",
    "page": page_title,
    "prop": "wikitext",
    "format": "json",
    "utf8": 1,
  }
  headers = {"User-Agent": "HebodanBot/1.0 (hebodan neta checker)"}
  resp = requests.get(WIKIPEDIA_API, params=params, headers=headers, timeout=30)
  resp.raise_for_status()
  data = resp.json()

  if "error" in data:
    print(f"Wikipedia API エラー: {data['error']}", file=sys.stderr)
    return []

  wikitext = data["parse"]["wikitext"]["*"]

  # 「記念日・年中行事」セクションを抽出
  # セクション見出しのパターン: == 記念日・年中行事 == or ==記念日・年中行事==
  section_pattern = re.compile(
    r"==\s*記念日・年中行事\s*==\n(.*?)(?=\n==[^=]|\Z)",
    re.DOTALL,
  )
  match = section_pattern.search(wikitext)
  if not match:
    # 別の見出しパターンも試す
    section_pattern2 = re.compile(
      r"==\s*記念日\s*==\n(.*?)(?=\n==[^=]|\Z)",
      re.DOTALL,
    )
    match = section_pattern2.search(wikitext)

  if not match:
    return []

  section_text = match.group(1)

  # 箇条書き行を抽出（* が記念日名、** が説明文 → 名前だけ取得）
  items = []
  for line in section_text.split("\n"):
    line = line.strip()
    # ** で始まる行は説明文なのでスキップ
    if line.startswith("**"):
      continue
    if line.startswith("*"):
      cleaned = _clean_wikitext(line.lstrip("* "))
      if cleaned and not cleaned.startswith(":"):
        items.append(cleaned)

  return items


def _clean_wikitext(text: str) -> str:
  """ウィキテキストのマークアップを除去してプレーンテキストにする"""
  # [[リンク|表示テキスト]] → 表示テキスト
  text = re.sub(r"\[\[[^|\]]*\|([^\]]+)\]\]", r"\1", text)
  # [[リンク]] → リンク
  text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)
  # {{仮リンク|テキスト|...}} → テキスト
  text = re.sub(r"\{\{仮リンク\|([^|]+)\|[^}]*\}\}", r"\1", text)
  # その他の {{...}} を除去
  text = re.sub(r"\{\{[^}]*\}\}", "", text)
  # '''太字''' → 太字
  text = re.sub(r"'''(.+?)'''", r"\1", text)
  # ''斜体'' → 斜体
  text = re.sub(r"''(.+?)''", r"\1", text)
  # <ref>...</ref> を除去
  text = re.sub(r"<ref[^>]*>.*?</ref>", "", text)
  text = re.sub(r"<ref[^>]*/?>", "", text)
  # その他の HTML タグ除去
  text = re.sub(r"<[^>]+>", "", text)
  # 外部リンク [URL テキスト] → テキスト
  text = re.sub(r"\[https?://\S+\s+([^\]]+)\]", r"\1", text)
  # 外部リンク [URL] → 除去
  text = re.sub(r"\[https?://\S+\]", "", text)
  # 空の括弧を除去（）
  text = re.sub(r"[（(]\s*[)）]", "", text)
  return text.strip()


def build_html(month: int, day: int, items: list[str]) -> str:
  """メール用 HTML を組み立てる（1日分）"""
  date_str = f"{month}月{day}日"
  items_html = "\n".join(f"<li>{item}</li>" for item in items)

  return f"""\
<html>
<body style="font-family: sans-serif; line-height: 1.8; color: #333;">
  <h2 style="color: #e67e22;">&#x1F4C5; {date_str}の記念日・年中行事</h2>
  <ul>
    {items_html}
  </ul>
  <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
  <p style="color: #999; font-size: 12px;">
    出典: <a href="https://ja.wikipedia.org/wiki/{month}月{day}日">Wikipedia - {date_str}</a><br>
    へぼ談チャンネルのネタ探し用に自動送信されています。
  </p>
</body>
</html>"""


WEEKDAY_JA = ["月", "火", "水", "木", "金", "土", "日"]


def build_html_multi(days_data: list[tuple[datetime, list[str]]]) -> str:
  """メール用 HTML を組み立てる（複数日分）

  Args:
    days_data: [(datetime, [記念日リスト]), ...] のリスト
  """
  sections = []
  sources = []

  for dt, items in days_data:
    m, d = dt.month, dt.day
    wd = WEEKDAY_JA[dt.weekday()]
    date_str = f"{m}月{d}日({wd})"

    if items:
      items_html = "\n".join(f"      <li>{item}</li>" for item in items)
      sections.append(f"""\
  <h3 style="color: #e67e22; border-left: 4px solid #e67e22; padding-left: 8px; margin-top: 24px;">
    &#x1F4C5; {date_str}
  </h3>
  <ul>
{items_html}
  </ul>""")
    else:
      sections.append(f"""\
  <h3 style="color: #ccc; border-left: 4px solid #ccc; padding-left: 8px; margin-top: 24px;">
    &#x1F4C5; {date_str}
  </h3>
  <p style="color: #999;">記念日が見つかりませんでした</p>""")

    sources.append(
      f'<a href="https://ja.wikipedia.org/wiki/{m}月{d}日">{date_str}</a>'
    )

  first_dt = days_data[0][0]
  last_dt = days_data[-1][0]
  title = f"{first_dt.month}/{first_dt.day}〜{last_dt.month}/{last_dt.day} の記念日・年中行事"

  return f"""\
<html>
<body style="font-family: sans-serif; line-height: 1.8; color: #333;">
  <h2 style="color: #2c3e50;">&#x1F4CB; {title}</h2>
  <p style="color: #888; font-size: 13px;">予約投稿の計画用に1週間分まとめてお届け</p>
{"".join(sections)}
  <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
  <p style="color: #999; font-size: 12px;">
    出典: {" | ".join(sources)}<br>
    へぼ談チャンネルのネタ探し用に自動送信されています。
  </p>
</body>
</html>"""


def send_email(subject: str, html_body: str):
  """Resend API でメールを送信する"""
  api_key = os.environ.get("RESEND_API_KEY")
  email_to = os.environ.get("EMAIL_TO")
  email_from = os.environ.get("EMAIL_FROM")

  if not all([api_key, email_to, email_from]):
    print("環境変数が不足しています: RESEND_API_KEY, EMAIL_TO, EMAIL_FROM", file=sys.stderr)
    sys.exit(1)

  resp = requests.post(
    "https://api.resend.com/emails",
    headers={
      "Authorization": f"Bearer {api_key}",
      "Content-Type": "application/json",
    },
    json={
      "from": f"へぼ談ネタ帳 <{email_from}>",
      "to": [email_to],
      "subject": subject,
      "html": html_body,
    },
    timeout=30,
  )

  if resp.status_code == 200:
    print(f"メール送信成功: {subject}")
  else:
    print(f"メール送信失敗 ({resp.status_code}): {resp.text}", file=sys.stderr)
    sys.exit(1)


def main():
  parser = argparse.ArgumentParser(description="記念日メール送信")
  parser.add_argument(
    "--date", type=str, default=None,
    help="開始日（YYYY-MM-DD形式、省略時は本日JST）",
  )
  parser.add_argument(
    "--days-ahead", type=int, default=7,
    help="先読み日数（0で当日のみ、デフォルト7）",
  )
  parser.add_argument(
    "--dry-run", action="store_true",
    help="メール送信せず内容を表示するだけ",
  )
  args = parser.parse_args()

  if args.date:
    start = datetime.strptime(args.date, "%Y-%m-%d").replace(tzinfo=JST)
  else:
    start = datetime.now(JST)

  num_days = args.days_ahead + 1  # 当日を含む

  # 1日だけの場合は従来の動作
  if num_days == 1:
    month, day = start.month, start.day
    print(f"対象日: {month}月{day}日")

    items = fetch_kinenbi(month, day)
    if not items:
      print("記念日が見つかりませんでした")
      return

    print(f"記念日 {len(items)} 件取得")
    subject = f"【へぼ談ネタ帳】{month}月{day}日の記念日"
    html_body = build_html(month, day, items)

    if args.dry_run:
      print(f"\n件名: {subject}")
      print("---")
      for item in items:
        print(f"  - {item}")
      return

    send_email(subject, html_body)
    return

  # 複数日: 当日 + days_ahead 日分を取得
  days_data: list[tuple[datetime, list[str]]] = []
  total_items = 0

  for i in range(num_days):
    dt = start + timedelta(days=i)
    m, d = dt.month, dt.day
    wd = WEEKDAY_JA[dt.weekday()]
    print(f"取得中: {m}月{d}日({wd})...", end=" ")

    items = fetch_kinenbi(m, d)
    days_data.append((dt, items))
    total_items += len(items)
    print(f"{len(items)}件")

  print(f"\n合計: {num_days}日分、{total_items}件の記念日を取得")

  # メール組み立て
  first_dt = days_data[0][0]
  last_dt = days_data[-1][0]
  subject = f"【へぼ談ネタ帳】{first_dt.month}/{first_dt.day}〜{last_dt.month}/{last_dt.day}の記念日"
  html_body = build_html_multi(days_data)

  if args.dry_run:
    print(f"\n件名: {subject}")
    print("---")
    for dt, items in days_data:
      wd = WEEKDAY_JA[dt.weekday()]
      print(f"\n■ {dt.month}月{dt.day}日({wd})")
      if items:
        for item in items:
          print(f"  - {item}")
      else:
        print("  （なし）")
    return

  # 送信
  send_email(subject, html_body)


if __name__ == "__main__":
  main()
