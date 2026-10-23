"""stand.fm の最新回を index.html のラジオ欄（radio-data）に反映する。

RSS から最新回のタイトルとURLを取り、<!--RADIO:START-->〜<!--RADIO:END--> の
JSON だけを書き換える。最新回が変わっていなければ何もしない。
"""
import datetime
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET

CHANNEL_ID = "690b845dbc35285f62fcc8bd"
FEED_URL = f"https://stand.fm/rss/{CHANNEL_ID}"
INDEX = "index.html"
EPISODE_RE = re.compile(r"https://stand\.fm/episodes/[0-9a-f]+")
BLOCK_RE = re.compile(
    r'(<!--RADIO:START-->\s*<script type="application/json" id="radio-data">)(.*?)(</script>\s*<!--RADIO:END-->)',
    re.S,
)


def fetch_latest():
    req = urllib.request.Request(FEED_URL, headers={"User-Agent": "Mozilla/5.0 (megane-connect radio updater)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        root = ET.fromstring(r.read())
    item = root.find("./channel/item")
    if item is None:
        sys.exit("RSS に放送回が見つかりません")
    title = (item.findtext("title") or "").strip()
    url = ""
    for text in (item.findtext("link"), item.findtext("guid")):
        m = EPISODE_RE.search(text or "")
        if m:
            url = m.group(0)
            break
    if not title or not url:
        sys.exit(f"タイトルかURLが取れません: title={title!r} url={url!r}")
    return title, url


def clean_title(title):
    # " は「」に（開き・閉じを交互に）、< > & は取り除く
    parts = title.split('"')
    out = parts[0]
    for i, p in enumerate(parts[1:]):
        out += ("「" if i % 2 == 0 else "」") + p
    return re.sub(r"[<>&]", "", out)


def main():
    title, url = fetch_latest()
    with open(INDEX, encoding="utf-8") as f:
        html = f.read()
    blocks = BLOCK_RE.findall(html)
    if len(blocks) != 1:
        sys.exit(f"radio-data の場所が1つに特定できません（{len(blocks)}個）")
    current = json.loads(blocks[0][1])
    if current.get("url") == url:
        print(f"更新なし: {title}")
        return
    today = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).date().isoformat()
    data = json.dumps({"title": clean_title(title), "url": url, "date": today}, ensure_ascii=False, separators=(",", ":"))
    html = BLOCK_RE.sub(lambda m: m.group(1) + data + m.group(3), html)
    with open(INDEX, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"更新: {title} {url}")


if __name__ == "__main__":
    main()
