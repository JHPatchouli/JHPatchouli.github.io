#!/usr/bin/env python3
"""Rebuild the homepage and the GitHub profile README from public repos.

Reads repos.json (a GitHub /user/repos payload, one page or several pages
concatenated). Forks and the two profile repositories themselves are skipped.
A repository counts as active when it is not archived and was pushed within
ACTIVE_DAYS. Everything else goes to the archive list.
"""

import html
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
USER = "JHPatchouli"
ACTIVE_DAYS = 400
SKIP = {"JHPatchouli", "JHPatchouli.github.io"}
INDEX = ROOT / "index.html"
README = ROOT / "PROFILE.md"

BEGIN = "<!-- profile:begin -->"
END = "<!-- profile:end -->"
README_BEGIN = "<!-- profile:begin -->"
README_END = "<!-- profile:end -->"


def load_repos(path: Path) -> list[dict]:
    blob = path.read_bytes()
    encoding = "utf-16" if blob.startswith(b"\xff\xfe") else "utf-8-sig"
    raw = blob.decode(encoding).strip()
    pages = []
    decoder = json.JSONDecoder()
    index = 0
    while index < len(raw):
        while index < len(raw) and raw[index].isspace():
            index += 1
        if index >= len(raw):
            break
        page, index = decoder.raw_decode(raw, index)
        pages.extend(page)
    return pages


def short_desc(text: str) -> str:
    text = " ".join((text or "").split())
    if len(text) > 180:
        text = text[:180].rsplit(" ", 1)[0].rstrip("，,、") + "…"
    return text


def select(repos: list[dict]) -> tuple[list[dict], list[dict]]:
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=ACTIVE_DAYS)
    active, archive = [], []
    for repo in repos:
        if repo.get("fork") or repo["name"] in SKIP or repo.get("private"):
            continue
        pushed = datetime.fromisoformat(repo["pushed_at"].replace("Z", "+00:00"))
        item = {
            "name": repo["name"],
            "url": repo["html_url"],
            "desc": short_desc(repo.get("description") or ""),
            "pushed": pushed,
        }
        if repo.get("archived") or pushed < cutoff:
            archive.append(item)
        else:
            active.append(item)
    active.sort(key=lambda r: r["pushed"], reverse=True)
    archive.sort(key=lambda r: r["name"].lower())
    return active, archive


def main_html(active: list[dict]) -> str:
    rows = []
    for repo in active:
        desc = html.escape(repo["desc"] or repo["url"].removeprefix("https://"))
        rows.append(
            '    <a class="row" href="{url}">\n'
            "      <b>{name}</b>\n"
            "      <span>{desc}</span>\n"
            "    </a>".format(url=html.escape(repo["url"]), name=html.escape(repo["name"]), desc=desc)
        )
    if not rows:
        rows.append('    <span class="row"><b>—</b><span>暂无</span></span>')
    return "\n".join(rows)


def archive_html(archive: list[dict]) -> str:
    links = [
        '      <a href="{url}">{name}</a>'.format(
            url=html.escape(repo["url"]), name=html.escape(repo["name"])
        )
        for repo in archive
    ]
    return "\n".join(links)


def render_index(active: list[dict], archive: list[dict]) -> str:
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return INDEX_TEMPLATE.format(
        active=main_html(active),
        archive=archive_html(archive),
        generated=generated,
    )


INDEX_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="JHPatchouli — 硬件、嵌入式与网络工具。">
<meta name="baidu-site-verification" content="b9lOcChmbf">
<title>JHPatchouli</title>
<style>
:root {{
  --bg: #070b0e;
  --line: #1a3338;
  --text: #c7e6e4;
  --dim: #6e9496;
  --amber: #e0a15c;
  --cyan: #8fd4d2;
}}
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; height: 100%; }}
body {{
  min-height: 100%;
  display: grid;
  grid-template-rows: 1fr auto;
  background:
    radial-gradient(900px 480px at 0% 0%, rgba(40, 90, 96, 0.16), transparent 55%),
    var(--bg);
  color: var(--text);
  font: 14px/1.65 "Cascadia Mono", "Sarasa Mono SC", Consolas, "Microsoft YaHei", monospace;
}}
body::before {{
  content: "";
  position: fixed;
  inset: 0;
  pointer-events: none;
  background: repeating-linear-gradient(to bottom, transparent 0 3px, rgba(0, 0, 0, 0.16) 3px 4px);
  z-index: 3;
}}
a {{ color: inherit; text-decoration: none; }}
a:hover {{ color: var(--amber); }}
.shell {{ display: grid; grid-template-columns: 240px 1fr; min-height: 0; }}
aside {{
  padding: 28px 22px;
  border-right: 1px solid var(--line);
  background: rgba(8, 14, 18, 0.72);
}}
.tag {{ margin: 0 0 14px; color: var(--amber); font-size: 11px; letter-spacing: 0.14em; }}
aside h1 {{ margin: 0; font-size: 16px; font-weight: 500; color: var(--cyan); }}
aside .bio {{ margin: 12px 0 0; color: var(--dim); font-size: 13px; }}
aside nav {{ margin-top: 28px; display: grid; gap: 6px; }}
aside nav a::before {{ content: "> "; color: var(--dim); }}
main {{ padding: 28px 36px 48px; max-width: 72rem; }}
h2 {{
  margin: 28px 0 10px;
  color: var(--amber);
  font-size: 11px;
  font-weight: 500;
  letter-spacing: 0.16em;
}}
h2:first-child {{ margin-top: 0; }}
.row {{
  display: grid;
  grid-template-columns: 13rem minmax(0, 1fr);
  gap: 28px;
  padding: 7px 0;
  border-top: 1px solid rgba(26, 51, 56, 0.7);
}}
.row span {{ color: var(--dim); }}
.old {{ margin-top: 4px; }}
.old a {{ color: var(--dim); margin: 0 14px 6px 0; display: inline-block; }}
.old a:hover {{ color: var(--amber); }}
footer {{
  position: relative;
  z-index: 4;
  display: flex;
  justify-content: space-between;
  gap: 16px;
  padding: 8px 18px;
  border-top: 1px solid var(--line);
  background: #081014;
  color: var(--dim);
  font-size: 12px;
}}
footer b {{ color: var(--cyan); font-weight: 500; }}
@media (max-width: 720px) {{
  .shell {{ grid-template-columns: 1fr; }}
  aside {{ border-right: 0; border-bottom: 1px solid var(--line); }}
  main {{ padding: 22px 18px 40px; }}
  .row {{ grid-template-columns: 1fr; gap: 0; }}
  footer span:nth-child(2) {{ display: none; }}
}}
</style>
</head>
<body>
<div class="shell">
  <aside>
    <p class="tag">// PROFILE</p>
    <h1>JHPatchouli</h1>
    <p class="bio">硬件、嵌入式与网络工具。</p>
    <nav>
      <a href="https://git.mrhao.xyz/blog/">blog</a>
      <a href="https://github.com/JHPatchouli/clawbot-roleplay">clawbot</a>
      <a href="https://github.com/JHPatchouli">github</a>
    </nav>
  </aside>
  <main>
    <h2>ACTIVE</h2>
{active}

    <h2>ARCHIVE</h2>
    <div class="old">
{archive}
    </div>
  </main>
</div>
<footer>
  <span>node <b>git.mrhao.xyz</b></span>
  <span>user <b>jhpatchouli</b></span>
  <span id="clk">--:--:--</span>
</footer>
<script>
(function () {{
  var el = document.getElementById("clk");
  function tick() {{
    var d = new Date();
    el.textContent = [d.getHours(), d.getMinutes(), d.getSeconds()]
      .map(function (n) {{ return (n < 10 ? "0" : "") + n; }})
      .join(":");
  }}
  tick();
  setInterval(tick, 1000);
}})();
</script>
<!-- generated {generated} -->
</body>
</html>
"""


def render_readme(active: list[dict], archive: list[dict]) -> str:
    def table(rows: list[dict]) -> str:
        if not rows:
            return "_暂无_\n"
        lines = ["| 项目 | 内容 |", "|---|---|"]
        for repo in rows:
            lines.append(
                "| [{name}]({url}) | {desc} |".format(
                    name=repo["name"], url=repo["url"], desc=repo["desc"] or "—"
                )
            )
        return "\n".join(lines) + "\n"

    return (
        "硬件、嵌入式与网络工具。\n\n"
        "[站点](https://git.mrhao.xyz/) · "
        "[博客](https://git.mrhao.xyz/blog/) · "
        "[GitHub](https://github.com/JHPatchouli)\n\n"
        f"{README_BEGIN}\n"
        "## 正在维护\n\n"
        + table(active)
        + "\n## 不再维护\n\n"
        + table(archive)
        + f"{README_END}\n"
    )


def replace_between(text: str, begin: str, end: str, body: str) -> str:
    start = text.find(begin)
    stop = text.find(end)
    if start < 0 or stop < start:
        raise SystemExit("profile markers missing")
    return text[: start + len(begin)] + "\n" + body + text[stop:]


def main() -> int:
    src = Path(sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REPOS_JSON", "repos.json"))
    active, archive = select(load_repos(src))
    index = render_index(active, archive)
    readme = render_readme(active, archive)
    changed = []
    if not INDEX.exists() or INDEX.read_text(encoding="utf-8") != index:
        INDEX.write_text(index, encoding="utf-8", newline="\n")
        changed.append(INDEX.name)
    if not README.exists() or README.read_text(encoding="utf-8") != readme:
        README.write_text(readme, encoding="utf-8", newline="\n")
        changed.append(README.name)
    print("active", len(active), "archive", len(archive), "changed", ",".join(changed) or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
