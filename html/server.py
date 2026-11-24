#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from pathlib import Path
from flask import Flask, abort, send_file, Response, request, redirect, session
from datetime import datetime
import mimetypes
import sqlite3
import json
import html
import config as cfg
from io import BytesIO
import render_daily_photo as rdp

ROOT_DIR = Path(__file__).resolve().parent

# --- config ---
DOWNLOAD_KEY = str(getattr(cfg, "DOWNLOAD_KEY", "") or "").strip()
if not DOWNLOAD_KEY:
    raise SystemExit("config.py 里没有配置 DOWNLOAD_KEY")

DB_PATH = Path(str(getattr(cfg, "DB_PATH", "./photos.db") or "./photos.db")).expanduser()
if not DB_PATH.is_absolute():
    DB_PATH = (ROOT_DIR / DB_PATH).resolve()

IMAGE_DIR = Path(str(getattr(cfg, "IMAGE_DIR", "") or "")).expanduser()
if not IMAGE_DIR.is_absolute():
    IMAGE_DIR = (ROOT_DIR / IMAGE_DIR).resolve()

BIN_OUTPUT_DIR = Path(str(getattr(cfg, "BIN_OUTPUT_DIR", "./output") or "./output")).expanduser()
if not BIN_OUTPUT_DIR.is_absolute():
    BIN_OUTPUT_DIR = (ROOT_DIR / BIN_OUTPUT_DIR).resolve()
BIN_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

FLASK_HOST = str(getattr(cfg, "FLASK_HOST", "0.0.0.0") or "0.0.0.0")
FLASK_PORT = int(getattr(cfg, "FLASK_PORT", 8765) or 8765)

# 是否开启照片库 WebUI（跑通后建议关闭，只保留 ESP32 下载接口）
ENABLE_REVIEW_WEBUI = bool(getattr(cfg, "ENABLE_REVIEW_WEBUI", True))

DAILY_PHOTO_QUANTITY = int(getattr(cfg, "DAILY_PHOTO_QUANTITY", 5) or 5)
if DAILY_PHOTO_QUANTITY < 1:
    DAILY_PHOTO_QUANTITY = 1


# review 分页：每页 100 张
REVIEW_PAGE_SIZE = 100

# /review 日期筛选的可用 MM-DD 列表缓存（避免每次都扫全库）
_MD_CACHE: dict[str, object] = {"md_list": [], "built_at": 0.0}
_MD_CACHE_TTL_SEC = 300.0  # 5 分钟

def _load_all_md_list() -> list[str]:
    """从全库提取所有存在的 MM-DD（去重、排序）。用于前端“随机一天”。"""
    if not DB_PATH.exists():
        return []

    # 简单 TTL 缓存
    import time
    now = time.time()
    try:
        built_at = float(_MD_CACHE.get("built_at") or 0.0)
    except Exception:
        built_at = 0.0
    if (now - built_at) < _MD_CACHE_TTL_SEC:
        cached = _MD_CACHE.get("md_list")
        if isinstance(cached, list):
            return [str(x) for x in cached]

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    rows = c.execute("SELECT exif_json FROM photo_scores").fetchall()
    conn.close()

    s: set[str] = set()
    for (exif_json,) in rows:
        d = extract_date_from_exif(exif_json)
        if d and len(d) >= 10:
            md = d[5:10]
            if len(md) == 5 and md[2] == "-":
                s.add(md)

    md_list = sorted(s)
    _MD_CACHE["md_list"] = md_list
    _MD_CACHE["built_at"] = now
    return md_list

app = Flask(__name__)
app.secret_key = 'inktime_secret_key_2024'  # 会话密钥

# 登录配置
LOGIN_USERNAME = 'sit'
LOGIN_PASSWORD = 'sit'

def _require_webui_enabled() -> None:
    if not ENABLE_REVIEW_WEBUI:
        abort(404)

def _require_login() -> None:
    """检查用户是否已登录"""
    if session.get('logged_in') != True:
        return redirect('/login')

def build_login_html(error_message: str = "") -> str:
    """构建登录页面"""
    error_html = f'<div class="error">{html.escape(error_message)}</div>' if error_message else ''
    
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <title>InkTime - 登录</title>
  <style>
    :root {{
      --bg: #0b0c10;
      --panel: rgba(255,255,255,0.06);
      --card: rgba(255,255,255,0.10);
      --text: rgba(255,255,255,0.92);
      --muted: rgba(255,255,255,0.62);
      --line: rgba(255,255,255,0.14);
      --accent: #8ab4ff;
      --accent2: #9cffd6;
      --shadow: 0 18px 60px rgba(0,0,0,0.45);
      --radius: 14px;
    }}
    body {{
      margin: 0;
      padding: 0;
      font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", system-ui, sans-serif;
      background: radial-gradient(1200px 800px at 20% 0%, rgba(138,180,255,0.18), transparent 45%),
                  radial-gradient(900px 700px at 90% 20%, rgba(156,255,214,0.14), transparent 55%),
                  linear-gradient(180deg, #07080b 0%, #0b0c10 40%, #0b0c10 100%);
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
    }}
    .login-container {{
      width: 100%;
      max-width: 420px;
      padding: 24px;
    }}
    .logo {{
      text-align: center;
      margin-bottom: 32px;
    }}
    .logo h1 {{
      font-size: 28px;
      margin: 0;
      letter-spacing: 0.5px;
      color: var(--text);
    }}
    .logo p {{
      font-size: 13px;
      color: var(--muted);
      margin: 6px 0 0;
    }}
    .card {{
      background: linear-gradient(180deg, var(--card) 0%, rgba(255,255,255,0.08) 100%);
      border: 1px solid rgba(255,255,255,0.14);
      border-radius: var(--radius);
      padding: 28px;
      box-shadow: var(--shadow);
      backdrop-filter: blur(10px);
    }}
    .error {{
      background: rgba(239, 68, 68, 0.15);
      border: 1px solid rgba(239, 68, 68, 0.35);
      border-radius: 10px;
      padding: 10px 14px;
      font-size: 13px;
      color: #ff6b6b;
      margin-bottom: 16px;
      text-align: center;
    }}
    .form-group {{
      margin-bottom: 18px;
    }}
    .form-group label {{
      display: block;
      font-size: 13px;
      color: var(--muted);
      margin-bottom: 8px;
    }}
    .form-group input {{
      width: 100%;
      padding: 12px 14px;
      font-size: 15px;
      color: var(--text);
      background: rgba(255,255,255,0.08);
      border: 1px solid rgba(255,255,255,0.16);
      border-radius: 10px;
      outline: none;
      box-sizing: border-box;
      transition: border-color 0.15s ease, box-shadow 0.15s ease;
    }}
    .form-group input:focus {{
      border-color: rgba(138, 180, 255, 0.7);
      box-shadow: 0 0 0 3px rgba(138, 180, 255, 0.16);
    }}
    .form-group input::placeholder {{
      color: rgba(255,255,255,0.4);
    }}
    .btn {{
      width: 100%;
      padding: 13px;
      font-size: 15px;
      font-weight: 600;
      cursor: pointer;
      color: #0b0c10;
      background: linear-gradient(135deg, var(--accent) 0%, var(--accent2) 100%);
      border: none;
      border-radius: 10px;
      transition: transform 0.08s ease, box-shadow 0.15s ease;
    }}
    .btn:hover {{
      transform: translateY(-1px);
      box-shadow: 0 8px 24px rgba(138, 180, 255, 0.4);
    }}
    .btn:active {{
      transform: translateY(0);
    }}
    .hint {{
      text-align: center;
      font-size: 12px;
      color: var(--muted);
      margin-top: 20px;
    }}
    .hint code {{
      background: rgba(255,255,255,0.1);
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 11px;
    }}
  </style>
</head>
<body>
  <div class="login-container">
    <div class="logo">
      <h1>InkTime</h1>
      <p>墨水屏照片记忆</p>
    </div>
    <div class="card">
      {error_html}
      <form method="post" action="/login">
        <div class="form-group">
          <label for="username">用户名</label>
          <input type="text" id="username" name="username" placeholder="请输入用户名" required>
        </div>
        <div class="form-group">
          <label for="password">密码</label>
          <input type="password" id="password" name="password" placeholder="请输入密码" required>
        </div>
        <button type="submit" class="btn">登 录</button>
      </form>
    </div>
    <div class="hint">
      用户名和密码均为 <code>sit</code>
    </div>
  </div>
</body>
</html>
"""


def _safe_join(base: Path, rel: str) -> Path:
    """防目录穿越：只允许 base 下的相对路径"""
    p = (base / rel).resolve()
    if not str(p).startswith(str(base.resolve())):
        raise ValueError("path traversal blocked")
    return p


def _send_static_file(p: Path) -> Response:
    if not p.exists() or not p.is_file():
        abort(404)

    if p.suffix.lower() == ".bin":
        return send_file(p, mimetype="application/octet-stream", as_attachment=False)

    mt, _ = mimetypes.guess_type(str(p))
    if mt:
        return send_file(p, mimetype=mt, as_attachment=False)
    return send_file(p, as_attachment=False)


def _make_image_url(path_str: str) -> str:
    """
    把数据库里的本地图片路径转换成 HTTP 可访问的 /images/... 路径。
    要求图片在 IMAGE_DIR 目录下；不在则返回空，避免 file:// 污染与 canvas 跨域。
    """
    try:
        p = Path(path_str).expanduser().resolve()
        rel = p.relative_to(IMAGE_DIR.resolve())
        return "/images/" + str(rel).replace("\\", "/")
    except Exception:
        return ""


# --------------------------
# DB helpers
# --------------------------


def load_rows(page: int = 1, page_size: int = REVIEW_PAGE_SIZE, md: str = "", sort: str = "memory"):
    """分页读取 review 数据。支持按 MM-DD 过滤与排序。返回 (rows, total_count)."""
    if not DB_PATH.exists():
        raise SystemExit(f"找不到数据库文件: {DB_PATH}")

    if page < 1:
        page = 1
    if page_size < 1:
        page_size = REVIEW_PAGE_SIZE

    offset = (page - 1) * page_size

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 从 exif_json 里提取 datetime，再拼 MM-DD
    # 期望格式："YYYY:MM:DD HH:MM:SS"（extract_date_from_exif 也按这个假设）
    dt_expr = "json_extract(exif_json, '$.datetime')"
    md_expr = f"(substr({dt_expr}, 6, 2) || '-' || substr({dt_expr}, 9, 2))"

    where_sql = ""
    params: list[object] = []

    md = (md or "").strip()
    if md and len(md) == 5 and md[2] == "-":
        where_sql = f"WHERE {dt_expr} IS NOT NULL AND {md_expr} = ?"
        params.append(md)

    # total_count 也要跟随过滤
    if where_sql:
        total_count = c.execute(f"SELECT COUNT(1) FROM photo_scores {where_sql}", params).fetchone()[0]
    else:
        total_count = c.execute("SELECT COUNT(1) FROM photo_scores").fetchone()[0]

    # 排序
    sort = (sort or "memory").strip()
    if sort == "beauty":
        order_sql = "ORDER BY COALESCE(beauty_score, -1) DESC, COALESCE(memory_score, -1) DESC, path"
    elif sort == "time_new":
        # 直接按 datetime 字符串排序（固定格式下可按字典序比较）；NULL 放最后
        order_sql = f"ORDER BY ({dt_expr} IS NULL) ASC, {dt_expr} DESC, path"
    elif sort == "time_old":
        order_sql = f"ORDER BY ({dt_expr} IS NULL) ASC, {dt_expr} ASC, path"
    else:
        # 默认 memory
        order_sql = "ORDER BY COALESCE(memory_score, -1) DESC, COALESCE(beauty_score, -1) DESC, path"

    base_sql = f"""
        SELECT path,
               caption,
               type,
               memory_score,
               beauty_score,
               reason,
               exif_json,
               width,
               height,
               orientation,
               used_at,
               side_caption
        FROM photo_scores
        {where_sql}
        {order_sql}
        LIMIT ? OFFSET ?
    """

    q_params = list(params) + [page_size, offset]
    rows = c.execute(base_sql, q_params).fetchall()

    conn.close()
    return rows, int(total_count)


def load_sim_rows():
    if not DB_PATH.exists():
        raise SystemExit(f"找不到数据库文件: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    rows = c.execute(
        """
        SELECT path,
               caption,
               type,
               memory_score,
               beauty_score,
               reason,
               side_caption,
               exif_json,
               width,
               height,
               orientation,
               used_at,
               exif_gps_lat,
               exif_gps_lon,
               exif_city
        FROM photo_scores
        """
    ).fetchall()

    conn.close()
    return rows


# 新增：只加载指定日期集合的照片，加速 /sim
def load_sim_rows_for_dates(dates: list[str]):
    """只加载指定日期（YYYY-MM-DD）集合内的照片，用于 /sim 加速。"""
    if not dates:
        return []
    if not DB_PATH.exists():
        raise SystemExit(f"找不到数据库文件: {DB_PATH}")

    # 过滤掉不合法日期字符串，避免 SQL 注入（虽然我们用参数化，但也别喂垃圾）
    safe_dates = []
    for d in dates:
        d = (d or "").strip()
        if len(d) == 10 and d[4] == "-" and d[7] == "-":
            safe_dates.append(d)
    if not safe_dates:
        return []

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    dt_expr = "json_extract(exif_json, '$.datetime')"
    # exif datetime 形如 YYYY:MM:DD HH:MM:SS，取前 10 位并把 : 替换成 - -> YYYY-MM-DD
    date_expr = f"replace(substr({dt_expr}, 1, 10), ':', '-')"

    placeholders = ",".join(["?"] * len(safe_dates))
    sql = f"""
        SELECT path,
               caption,
               type,
               memory_score,
               beauty_score,
               reason,
               side_caption,
               exif_json,
               width,
               height,
               orientation,
               used_at,
               exif_gps_lat,
               exif_gps_lon,
               exif_city
        FROM photo_scores
        WHERE {dt_expr} IS NOT NULL
          AND {date_expr} IN ({placeholders})
    """

    rows = c.execute(sql, tuple(safe_dates)).fetchall()
    conn.close()
    return rows

def get_photo_meta_by_path(abs_path: str):
    """
    从 DB 找到渲染需要的字段：date/side/lat/lon/city。
    abs_path 必须是数据库里 photo_scores.path 的原值（通常是绝对路径）。
    """
    if not DB_PATH.exists():
        return None

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    row = c.execute(
        """
        SELECT path,
               exif_json,
               side_caption,
               memory_score,
               exif_gps_lat,
               exif_gps_lon,
               exif_city
        FROM photo_scores
        WHERE path = ?
        LIMIT 1
        """,
        (abs_path,),
    ).fetchone()
    conn.close()

    if not row:
        return None

    path, exif_json, side_caption, memory_score, gps_lat, gps_lon, exif_city = row
    date_str = extract_date_from_exif(exif_json)
    if not date_str:
        try:
            p = Path(path)
            if p.exists():
                mtime = p.stat().st_mtime
                date_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
        except Exception:
            pass

    return {
        "path": str(path),
        "date": date_str,
        "side": side_caption or "",
        "memory": float(memory_score) if memory_score is not None else None,
        "lat": gps_lat,
        "lon": gps_lon,
        "city": exif_city or "",
    }

def summarize_exif(exif_json: str | None) -> str:
    if not exif_json:
        return ""

    try:
        data = json.loads(exif_json)
    except Exception:
        return ""

    dtv = data.get("datetime")
    make = data.get("make")
    model = data.get("model")
    iso = data.get("iso")
    exp = data.get("exposure_time")
    fnum = data.get("f_number")
    fl = data.get("focal_length")
    lat = data.get("gps_lat")
    lon = data.get("gps_lon")

    parts = []
    if dtv:
        parts.append(f"时间: {dtv}")
    if make or model:
        cam = f"{make or ''} {model or ''}".strip()
        if cam:
            parts.append(f"设备: {cam}")
    exp_parts = []
    if iso:
        exp_parts.append(f"ISO {iso}")
    if exp:
        exp_parts.append(f"快门 {exp}")
    if fnum:
        exp_parts.append(f"光圈 {fnum}")
    if fl:
        exp_parts.append(f"焦距 {fl}")
    if exp_parts:
        parts.append(" / ".join(exp_parts))
    if lat is not None and lon is not None:
        try:
            parts.append(f"GPS: {float(lat):.5f}, {float(lon):.5f}")
        except Exception:
            parts.append(f"GPS: {lat}, {lon}")

    return "；".join(str(p) for p in parts if p)


def extract_date_from_exif(exif_json: str | None) -> str:
    if not exif_json:
        return ""
    try:
        data = json.loads(exif_json)
    except Exception:
        return ""
    dtv = data.get("datetime")
    if not dtv:
        return ""
    try:
        date_part = str(dtv).split()[0]  # "2018:03:18"
        parts = date_part.replace(":", "-").split("-")
        if len(parts) >= 3:
            return f"{parts[0]}-{parts[1]}-{parts[2]}"
    except Exception:
        return ""
    return ""


# --------------------------
# HTML builders
# --------------------------

def build_html(rows, page: int, page_size: int, total_count: int):
    items_html = []

    for path, caption, ptype, m_score, b_score, reason, exif_json, width, height, orientation, used_at, side_caption in rows:
        safe_caption = html.escape(caption or "").replace("\n", "<br>")
        safe_side = html.escape(side_caption or "").replace("\n", "<br>")
        safe_type = html.escape(ptype or "")
        safe_reason = html.escape(reason or "")
        exif_summary = summarize_exif(exif_json)
        safe_exif = html.escape(exif_summary or "")

        date_str = extract_date_from_exif(exif_json)
        safe_date = html.escape(date_str or "")

        md_str = ""
        if date_str and len(date_str) >= 10:
            md_str = date_str[5:10]
        safe_md = html.escape(md_str or "")

        res_str = ""
        if width and height:
            try:
                res_str = f"{int(width)} x {int(height)}"
            except Exception:
                res_str = f"{width} x {height}"
        orient_str = orientation or ""
        used_str = used_at or ""

        img_uri = _make_image_url(str(path))
        if not img_uri:
            continue

        score_html = ""
        if m_score is not None or b_score is not None:
            parts = []
            if m_score is not None:
                parts.append(f"回忆度: {m_score:.1f}")
            if b_score is not None:
                parts.append(f"美观度: {b_score:.1f}")
            score_line = " / ".join(parts)
            score_html = f'<div class="score">{score_line}</div>'

        type_html = f'<div class="type">类型: {safe_type}</div>' if safe_type else ""
        exif_html = f'<div class="exif">{safe_exif}</div>' if safe_exif else ""
        reason_html = f'<div class="reason">理由: {safe_reason}</div>' if safe_reason else ""

        items_html.append(f"""
        <div class="item"
             data-date="{safe_date}"
             data-md="{safe_md}"
             data-memory="{m_score if m_score is not None else ''}"
             data-beauty="{b_score if b_score is not None else ''}">
            <div class="img-wrap">
                <a class="img-link" href="/sim?img={html.escape(img_uri)}" title="打开该照片的模拟器" onclick="window.stop();">
                    <img src="{img_uri}" loading="lazy">
                </a>
            </div>
            {f'<div class="side-under">{safe_side}</div>' if safe_side else ''}
            <div class="meta">
                <div class="path">{html.escape(str(path))}</div>
                {type_html}
                {score_html}
                {reason_html}
                {exif_html}
                <div class="extra">
                    {f"拍摄日期: {safe_date}" if safe_date else ""}
                    {(" · 分辨率: " + html.escape(res_str)) if res_str else ""}
                    {(" · 方向: " + html.escape(orient_str)) if orient_str else ""}
                    {(" · 已上屏: " + html.escape(used_str)) if used_str else ""}
                </div>
                <div class="caption">{safe_caption}</div>
            </div>
        </div>
        """)

    items_str = "\n".join(items_html)
    total_pages = (total_count + page_size - 1) // page_size

    # 从请求参数回填（用于显示）
    md_q = (request.args.get("md", "") or "").strip()
    sort_q = (request.args.get("sort", "") or "memory").strip() or "memory"
    md_hint = f" · 筛选日期 {html.escape(md_q)}" if (md_q and len(md_q) == 5) else ""

    html_str = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <title>InkTime照片数据库</title>
  <style>
    :root{{
      --bg: #0b0c10;
      --panel: rgba(255,255,255,0.06);
      --card: rgba(255,255,255,0.10);
      --card2: rgba(255,255,255,0.08);
      --text: rgba(255,255,255,0.92);
      --muted: rgba(255,255,255,0.62);
      --muted2: rgba(255,255,255,0.48);
      --line: rgba(255,255,255,0.14);
      --accent: #8ab4ff;
      --accent2:#9cffd6;
      --shadow: 0 18px 60px rgba(0,0,0,0.45);
      --shadow2: 0 10px 28px rgba(0,0,0,0.35);
      --radius: 14px;
    }}
    body{{
      margin:0;
      padding:0;
      font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", system-ui, sans-serif;
      background: radial-gradient(1200px 800px at 20% 0%, rgba(138,180,255,0.18), transparent 45%),
                  radial-gradient(900px 700px at 90% 20%, rgba(156,255,214,0.14), transparent 55%),
                  linear-gradient(180deg, #07080b 0%, #0b0c10 40%, #0b0c10 100%);
      color: var(--text);
    }}
    .container{{
      max-width: 1320px;
      margin: 26px auto 60px;
      padding: 0 18px;
    }}
    h1{{
      font-size: 22px;
      margin: 0 0 8px;
      letter-spacing: 0.2px;
    }}
    .subtitle{{
      font-size: 13px;
      color: var(--muted);
      margin: 0 0 14px;
      line-height: 1.35;
    }}

    .controls{{
      display:flex;
      flex-wrap:wrap;
      gap: 10px;
      align-items:center;
      margin: 12px 0 14px;
      font-size: 13px;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      padding: 10px 12px;
      box-shadow: var(--shadow2);
      backdrop-filter: blur(10px);
    }}
    .controls label{{
      display:inline-flex;
      align-items:center;
      gap: 8px;
      color: var(--muted);
      white-space: nowrap;
    }}
    .controls select{{
      padding: 7px 10px;
      font-size: 13px;
      color: var(--text);
      background: rgba(255,255,255,0.08);
      border: 1px solid rgba(255,255,255,0.16);
      border-radius: 10px;
      outline: none;
    }}
    .controls select:focus{{
      border-color: rgba(138,180,255,0.7);
      box-shadow: 0 0 0 3px rgba(138,180,255,0.16);
    }}
    .controls button{{
      padding: 7px 12px;
      font-size: 13px;
      cursor: pointer;
      color: var(--text);
      background: rgba(255,255,255,0.10);
      border: 1px solid rgba(255,255,255,0.16);
      border-radius: 10px;
      transition: transform .08s ease, background .15s ease, border-color .15s ease, opacity .15s ease;
    }}
    .controls button:hover{{
      background: rgba(255,255,255,0.14);
      border-color: rgba(255,255,255,0.26);
    }}
    .controls button:active{{
      transform: translateY(1px);
    }}
    .controls button:disabled{{
      opacity: 0.45;
      cursor: not-allowed;
    }}
    .controls.pager{{
      background: rgba(255,255,255,0.05);
    }}

    .status{{
      font-size: 12px;
      color: var(--muted);
      margin: 8px 0 12px;
    }}

    .grid{{
      display:grid;
      grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
      gap: 16px;
    }}
    .item{{
      background: linear-gradient(180deg, var(--card) 0%, var(--card2) 100%);
      border: 1px solid rgba(255,255,255,0.14);
      border-radius: var(--radius);
      overflow: hidden;
      box-shadow: var(--shadow2);
      display:flex;
      flex-direction:column;
      transition: transform .12s ease, border-color .15s ease, box-shadow .15s ease;
    }}
    .item:hover{{
      transform: translateY(-2px);
      border-color: rgba(138,180,255,0.38);
      box-shadow: var(--shadow);
    }}

    .img-wrap{{
      width:100%;
      background: rgba(0,0,0,0.55);
      display:flex;
      align-items:center;
      justify-content:center;
      max-height: 260px;
      overflow:hidden;
    }}
    .img-wrap img{{
      width:100%;
      height:auto;
      display:block;
      object-fit: cover;
      filter: saturate(1.04) contrast(1.02);
    }}
    .img-link{{ display:block; width:100%; }}
    .img-link:link, .img-link:visited{{ text-decoration:none; }}

    .side-under{{
      padding: 10px 12px 0;
      font-size: 12px;
      color: var(--text);
      line-height: 1.45;
      word-break: break-word;
      opacity: 0.92;
    }}

    .meta{{
      padding: 10px 12px 12px;
      font-size: 13px;
      color: var(--text);
    }}
    .path{{
      font-size: 11px;
      color: var(--muted2);
      margin-bottom: 6px;
      word-break: break-all;
    }}
    .type{{
      font-size: 12px;
      color: var(--muted);
      margin-bottom: 4px;
    }}
    .score{{
      font-size: 13px;
      font-weight: 650;
      margin-bottom: 6px;
      color: var(--accent2);
    }}
    .reason{{
      font-size: 12px;
      color: var(--muted);
      margin-bottom: 6px;
      line-height: 1.45;
    }}
    .exif{{
      font-size: 11px;
      color: var(--muted2);
      margin-bottom: 8px;
      line-height: 1.45;
    }}
    .extra{{
      font-size: 11px;
      color: var(--muted2);
      margin-bottom: 8px;
      line-height: 1.45;
    }}
    .caption{{
      margin-top: 6px;
      font-size: 13px;
      line-height: 1.55;
      color: var(--text);
    }}

    @media (max-width: 560px){{
      .container{{ padding: 0 14px; }}
      .grid{{ grid-template-columns: 1fr; }}
      .controls{{ gap: 8px; }}
    }}
  </style>
</head>
<body>
  <div class="container">
    <h1>InkTime照片数据库</h1>
    <div class="subtitle">
      数据库：{html.escape(str(DB_PATH))}{md_hint} · 当前页 {page} · 本页 {len(rows)} 张 · 总计 {total_count} 张（每页 {page_size} 张）
    </div>

    <div class="controls">
      <label>
        月份：
        <select id="monthFilter">
          <option value="">全部</option>
          <option value="01">1 月</option><option value="02">2 月</option><option value="03">3 月</option>
          <option value="04">4 月</option><option value="05">5 月</option><option value="06">6 月</option>
          <option value="07">7 月</option><option value="08">8 月</option><option value="09">9 月</option>
          <option value="10">10 月</option><option value="11">11 月</option><option value="12">12 月</option>
        </select>
      </label>
      <label>
        日期：
        <select id="dayFilter">
          <option value="">全部</option>
          {''.join([f'<option value="{i:02d}">{i} 日</option>' for i in range(1, 32)])}
        </select>
      </label>
      <label>
        排序：
        <select id="sortBy">
          <option value="memory">按回忆度</option>
          <option value="beauty">按美观度</option>
          <option value="time_new">按时间（新→旧）</option>
          <option value="time_old">按时间（旧→新）</option>
        </select>
      </label>
      <button type="button" id="randomDateBtn">随机一天</button>
      <button type="button" id="homeBtn">回到首页</button>
    </div>

    <div class="controls pager" style="justify-content: space-between;">
      <div>
        <button type="button" id="prevPageBtn">上一页</button>
        <button type="button" id="nextPageBtn">下一页</button>
      </div>
      <div class="subtitle" style="margin:0;">第 <span id="pageNum">{page}</span> 页 / 共 <span id="pageTotal">{total_pages}</span> 页</div>
    </div>

    <div class="status" id="statusLine"></div>

    <div class="grid">
      {items_str}
    </div>

    <div class="controls pager" style="justify-content: space-between; margin-top: 18px;">
      <div>
        <button type="button" id="prevPageBtnBottom">上一页</button>
        <button type="button" id="nextPageBtnBottom">下一页</button>
      </div>
      <div class="subtitle" style="margin:0;">第 <span>{page}</span> 页 / 共 <span>{total_pages}</span> 页</div>
    </div>
  </div>

  <script>
    document.addEventListener('DOMContentLoaded', function () {{
      const monthSelect = document.getElementById('monthFilter');
      const daySelect = document.getElementById('dayFilter');
      const sortSelect = document.getElementById('sortBy');
      const statusLine = document.getElementById('statusLine');
      const randomBtn = document.getElementById('randomDateBtn');
      const homeBtn = document.getElementById('homeBtn');

      const currentPage = {page};
      const totalPages = {total_pages};
      const prevBtn = document.getElementById('prevPageBtn');
      const nextBtn = document.getElementById('nextPageBtn');
      const prevBtnBottom = document.getElementById('prevPageBtnBottom');
      const nextBtnBottom = document.getElementById('nextPageBtnBottom');

      // 任何跳转前先中断当前页面的图片/资源加载，避免请求排队导致“点击无响应”
      function navigateTo(urlStr) {{
        try {{
          window.stop();
        }} catch (e) {{
          // ignore
        }}
        window.location.href = urlStr;
      }}

      function getParams() {{
        const url = new URL(window.location.href);
        const md = (url.searchParams.get('md') || '').trim();
        const sort = (url.searchParams.get('sort') || '').trim() || 'memory';
        const page = parseInt(url.searchParams.get('page') || '1', 10) || 1;
        return {{ url, md, sort, page }};
      }}

      function setSelectsFromUrl() {{
        const p = getParams();
        // sort
        if (sortSelect) sortSelect.value = p.sort;
        // md -> month/day
        if (p.md && p.md.length === 5 && p.md.indexOf('-') === 2) {{
          const parts = p.md.split('-');
          if (parts.length === 2) {{
            if (monthSelect) monthSelect.value = parts[0];
            if (daySelect) daySelect.value = parts[1];
          }}
          if (statusLine) statusLine.textContent = '当前筛选：' + p.md + '（全库）';
        }} else {{
          if (monthSelect) monthSelect.value = '';
          if (daySelect) daySelect.value = '';
          if (statusLine) statusLine.textContent = '';
        }}
      }}

      function buildReviewUrl(md, sort, page) {{
        const url = new URL(window.location.href);
        url.pathname = '/review';
        if (md && md.length === 5 && md.indexOf('-') === 2) url.searchParams.set('md', md);
        else url.searchParams.delete('md');
        if (sort) url.searchParams.set('sort', sort);
        else url.searchParams.delete('sort');
        url.searchParams.set('page', String(page || 1));
        return url.toString();
      }}

      function goPage(p) {{
        const params = getParams();
        navigateTo(buildReviewUrl(params.md, params.sort, p));
      }}

      function goHome() {{
        const params = getParams();
        navigateTo(buildReviewUrl('', params.sort || 'memory', 1));
      }}

      async function pickRandomDate() {{
        // 从后端拿“真实存在的日期集合”，前端随机一个，然后让后端按 md 过滤
        try {{
          // 先停止当前页面的图片加载，释放连接
          try {{ window.stop(); }} catch (e) {{}}
          const resp = await fetch('/api/md_list');
          if (!resp.ok) throw new Error('HTTP ' + resp.status);
          const data = await resp.json();
          const arr = Array.isArray(data) ? data : (Array.isArray(data.md_list) ? data.md_list : []);
          if (!arr.length) {{
            if (statusLine) statusLine.textContent = '全库没有任何可用日期（exif datetime 缺失）。';
            return;
          }}
          const idx = Math.floor(Math.random() * arr.length);
          const md = String(arr[idx] || '').trim();
          const params = getParams();
          navigateTo(buildReviewUrl(md, params.sort || 'memory', 1));
        }} catch (e) {{
          if (statusLine) statusLine.textContent = '随机失败：' + e;
        }}
      }}

      function onMonthDayChange() {{
        const mVal = (monthSelect && monthSelect.value) ? monthSelect.value : '';
        const dVal = (daySelect && daySelect.value) ? daySelect.value : '';
        const sortBy = (sortSelect && sortSelect.value) ? sortSelect.value : 'memory';

        if (!mVal && !dVal) {{
          navigateTo(buildReviewUrl('', sortBy, 1));
          return;
        }}
        if (mVal && dVal) {{
          const md = mVal + '-' + dVal;
          navigateTo(buildReviewUrl(md, sortBy, 1));
          return;
        }}
        // 只选了一个，不跳转，避免生成无意义的 md
      }}

      function onSortChange() {{
        const params = getParams();
        const sortBy = (sortSelect && sortSelect.value) ? sortSelect.value : 'memory';
        navigateTo(buildReviewUrl(params.md, sortBy, 1));
      }}

      // 分页按钮
      if (prevBtn) {{
        prevBtn.disabled = currentPage <= 1;
        prevBtn.addEventListener('click', () => goPage(Math.max(1, currentPage - 1)));
      }}
      if (nextBtn) {{
        nextBtn.disabled = currentPage >= totalPages;
        nextBtn.addEventListener('click', () => goPage(Math.min(totalPages, currentPage + 1)));
      }}
      if (prevBtnBottom) {{
        prevBtnBottom.disabled = currentPage <= 1;
        prevBtnBottom.addEventListener('click', () => goPage(Math.max(1, currentPage - 1)));
      }}
      if (nextBtnBottom) {{
        nextBtnBottom.disabled = currentPage >= totalPages;
        nextBtnBottom.addEventListener('click', () => goPage(Math.min(totalPages, currentPage + 1)));
      }}

      if (monthSelect) monthSelect.addEventListener('change', onMonthDayChange);
      if (daySelect) daySelect.addEventListener('change', onMonthDayChange);
      if (sortSelect) sortSelect.addEventListener('change', onSortChange);
      if (randomBtn) randomBtn.addEventListener('click', pickRandomDate);
      if (homeBtn) homeBtn.addEventListener('click', goHome);

      // 兜底：用户在图片疯狂加载时点击任何链接/按钮，先 stop()，避免导航请求排队
      document.addEventListener('click', function (ev) {{
        const t = ev.target;
        if (!t) return;
        const a = t.closest ? t.closest('a') : null;
        const btn = t.closest ? t.closest('button') : null;
        // 只要是链接或按钮点击，就先中断当前加载
        if (a || btn) {{
          try {{ window.stop(); }} catch (e) {{}}
        }}
      }}, true);

      setSelectsFromUrl();
    }});
  </script>
</body>
</html>
"""
    return html_str


def build_simulator_html(sim_rows, selected_img: str = ""):
    # 空数据时不要做任何无意义的循环，避免前端 JS 大对象
    if not sim_rows:
        sim_rows = []
    items = []

    def _parse_tags(ptype_val) -> list[str]:
        """把 DB 的 type 字段解析成 tag 数组。
        兼容三种常见存储：
        - JSON 数组：   ["人物","日常"]
        - 伪数组文本：  [人物, 日常] / [人物，日常]
        - 普通字符串：  人物,日常 / 人物
        注意：这里是容错解析，目的是不让 /sim 因坏数据 500。
        """
        if ptype_val is None:
            return []
        s = str(ptype_val).strip()
        if not s:
            return []

        # 1) 先尝试严格 JSON
        if s.startswith("[") and s.endswith("]"):
            try:
                arr = json.loads(s)
                if isinstance(arr, list):
                    out = []
                    for x in arr:
                        t = str(x).strip()
                        if t:
                            out.append(t)
                    return out
            except Exception:
                # JSON 不合法：继续走容错
                pass

        # 2) 容错：去掉最外层 [] 以及引号，然后按逗号/中文逗号切
        if s.startswith("[") and s.endswith("]"):
            s = s[1:-1].strip()

        # 去掉可能出现的引号
        s = s.replace('"', '').replace("'", "")

        parts = [p.strip() for p in s.replace('，', ',').split(',')]
        out = [p for p in parts if p]
        return out
    for (
        path,
        caption,
        ptype,
        memory_score,
        beauty_score,
        reason,
        side_caption,
        exif_json,
        width,
        height,
        orientation,
        used_at,
        gps_lat,
        gps_lon,
        exif_city,
    ) in sim_rows:
        date_str = extract_date_from_exif(exif_json)
        if not date_str:
            try:
                p = Path(path)
                if p.exists():
                    mtime = p.stat().st_mtime
                    date_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
            except Exception:
                date_str = "2000-01-01"
        img_uri = _make_image_url(str(path))
        if not img_uri:
            continue

        # tags: 保证为数组，优先解析 JSON/容错
        type_value = _parse_tags(ptype)

        items.append({
            "path": img_uri,
            "date": date_str,
            "memory": float(memory_score) if memory_score is not None else None,
            "beauty": float(beauty_score) if beauty_score is not None else None,
            "city": exif_city or "",
            "lat": gps_lat,
            "lon": gps_lon,
            "side": side_caption or "",
            "caption": caption or "",
            "type": type_value,
            "reason": reason or "",
            "exif_json": exif_json or "",
            "exif_summary": summarize_exif(exif_json) if exif_json else "",
            "width": width if width is not None else "",
            "height": height if height is not None else "",
            "orientation": orientation or "",
            "used_at": used_at or "",
        })

    data_json = json.dumps(items, ensure_ascii=False).replace("</", "<\\/") if items else "[]"
    selected_json = json.dumps(selected_img or "", ensure_ascii=False).replace("</", "<\\/")

    html_str = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <title>墨水屏渲染效果预览</title>
  <style>
    :root {{
      --bg: #0b0c10;
      --panel: rgba(255,255,255,0.06);
      --line: rgba(255,255,255,0.14);
      --text: rgba(255,255,255,0.92);
      --muted: rgba(255,255,255,0.62);
      --muted2: rgba(255,255,255,0.48);
      --accent: #8ab4ff;
      --accent2: #9cffd6;
      --shadow: 0 18px 60px rgba(0,0,0,0.45);
      --shadow2: 0 10px 28px rgba(0,0,0,0.35);
      --radius: 14px;
    }}
    body {{
      margin:0; padding:0;
      font-family:-apple-system,BlinkMacSystemFont,system-ui,sans-serif;
      background: radial-gradient(1200px 800px at 20% 0%, rgba(138,180,255,0.18), transparent 45%),
                  radial-gradient(900px 700px at 90% 20%, rgba(156,255,214,0.14), transparent 55%),
                  linear-gradient(180deg, #07080b 0%, #0b0c10 40%, #0b0c10 100%);
      color: var(--text);
    }}
    .container {{
      max-width: 1120px;
      margin: 22px auto 42px;
      padding: 0 16px;
    }}
    a.back {{
      display:inline-block;
      margin-bottom: 10px;
      color: var(--accent);
      text-decoration: none;
    }}
    h1 {{
      font-size: 22px;
      margin: 0 0 8px;
      letter-spacing: 0.2px;
    }}
    .subtitle {{
      font-size: 13px;
      color: var(--muted);
      margin-bottom: 14px;
      line-height: 1.45;
    }}
    .controls {{
      display:flex;
      align-items:center;
      gap: 10px;
      margin-bottom: 14px;
      font-size: 13px;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      padding: 10px 12px;
      box-shadow: var(--shadow2);
      backdrop-filter: blur(10px);
    }}
    .controls button {{
      padding: 7px 12px;
      font-size: 13px;
      cursor: pointer;
      color: var(--text);
      background: rgba(255,255,255,0.10);
      border: 1px solid rgba(255,255,255,0.16);
      border-radius: 10px;
      transition: transform .08s ease, background .15s ease, border-color .15s ease, opacity .15s ease;
    }}
    .controls button:hover {{
      background: rgba(255,255,255,0.14);
      border-color: rgba(255,255,255,0.26);
    }}
    .controls button:active {{
      transform: translateY(1px);
    }}

    .status {{
      font-size: 12px;
      color: var(--muted);
      margin: 6px 0 10px;
      min-height: 16px;
    }}

    .preview-wrap {{
      display:flex;
      flex-wrap:wrap;
      gap: 16px;
      align-items: flex-start;
    }}
    .canvas-box {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      padding: 10px;
      box-shadow: var(--shadow2);
      backdrop-filter: blur(10px);
    }}
    .canvas-box h2 {{
      font-size: 13px;
      margin: 0 0 8px;
      color: rgba(255,255,255,0.78);
    }}
    #previewCanvas {{
      display:block;
      background:#fff;
      border: 1px solid rgba(255,255,255,0.18);
      border-radius: 10px;
    }}

    .meta-box {{
      flex: 1;
      min-width: 320px;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      padding: 12px;
      box-shadow: var(--shadow2);
      backdrop-filter: blur(10px);
      font-size: 16px;
      line-height: 1.75;
    }}
    .meta-title {{
      font-size: 13px;
      color: rgba(255,255,255,0.78);
      margin: 0 0 10px;
    }}
    .kpi {{
      display:grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
      margin-bottom: 12px;
      padding-bottom: 10px;
      border-bottom: 1px solid rgba(255,255,255,0.10);
    }}
    .kpi .cell {{
      background: rgba(255,255,255,0.06);
      border: 1px solid rgba(255,255,255,0.10);
      border-radius: 12px;
      padding: 10px;
    }}
    .kpi .label {{
      font-size: 11px;
      color: var(--muted2);
      margin-bottom: 4px;
    }}
    .kpi .value {{
      font-size: 16px;
      font-weight: 700;
      color: var(--text);
      line-height: 1.2;
      word-break: break-word;
    }}
    .kpi .value.accent {{
      color: var(--accent2);
    }}

    .field {{
      display:flex;
      gap: 10px;
      margin-bottom: 8px;
      line-height: 1.45;
      font-size: 12px;
    }}
    .field .label {{
      width: 92px;
      flex: 0 0 92px;
      color: var(--muted2);
    }}
    .field .value {{
      flex: 1;
      color: var(--text);
      word-break: break-word;
    }}
    .mono {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
      font-size: 11px;
      color: rgba(255,255,255,0.80);
      white-space: pre-wrap;
      word-break: break-word;
      background: rgba(0,0,0,0.22);
      border: 1px solid rgba(255,255,255,0.10);
      border-radius: 12px;
      padding: 10px;
    }}

    .section {{
      padding-top: 10px;
      margin-top: 10px;
      border-top: 1px solid rgba(255,255,255,0.10);
    }}
    .section:first-of-type {{
      padding-top: 0;
      margin-top: 0;
      border-top: none;
    }}
    .section-title {{
      display:flex;
      align-items:center;
      justify-content: space-between;
      gap: 10px;
      font-size: 12px;
      color: rgba(255,255,255,0.78);
      margin: 0 0 8px;
      letter-spacing: .2px;
    }}

    .chips {{
      display:flex;
      flex-wrap:wrap;
      gap: 8px;
      margin: 12px 0 14px;
    }}
    .chip {{
      display:inline-flex;
      align-items:center;
      gap: 6px;
      padding: 6px 10px;
      border-radius: 999px;
      font-size: 12px;
      line-height: 1;
      border: 1px solid rgba(255,255,255,0.18);
      background: rgba(255,255,255,0.07);
      color: rgba(255,255,255,0.92);
      user-select: none;
    }}
    .chip-dot {{
      width: 8px;
      height: 8px;
      border-radius: 999px;
      background: rgba(255,255,255,0.7);
      flex: 0 0 8px;
    }}

    .big-text {{
      font-size: 13px;
      line-height: 1.55;
      color: rgba(255,255,255,0.92);
      padding: 10px 12px;
      background: rgba(255,255,255,0.06);
      border: 1px solid rgba(255,255,255,0.10);
      border-radius: 12px;
      word-break: break-word;
      white-space: pre-wrap;
    }}

    details.fold {{
      background: rgba(255,255,255,0.04);
      border: 1px solid rgba(255,255,255,0.10);
      border-radius: 12px;
      padding: 10px 12px;
      margin-top: 18px;
      font-size: 14px;
    }}
    details.fold > summary {{
      cursor: pointer;
      list-style: none;
      outline: none;
      color: rgba(255,255,255,0.86);
      font-size: 12px;
      display:flex;
      align-items:center;
      justify-content: space-between;
      gap: 10px;
    }}
    details.fold > summary::-webkit-details-marker {{ display: none; }}
    .fold-hint {{
      color: rgba(255,255,255,0.55);
      font-size: 11px;
    }}

    .kv-grid {{
      display:grid;
      grid-template-columns: 92px 1fr;
      gap: 8px 10px;
      margin-top: 10px;
      font-size: 12px;
      line-height: 1.45;
    }}
    .kv-k {{
      color: rgba(255,255,255,0.52);
    }}
    .kv-v {{
      color: rgba(255,255,255,0.92);
      word-break: break-word;
    }}

    .hero-text {{
      font-size: 26px;
      line-height: 1.7;
      font-weight: 650;
      margin-bottom: 18px;
      color: rgba(255,255,255,0.98);
      word-break: break-word;
      white-space: pre-wrap;
    }}

    .action-buttons {{
      display: flex;
      gap: 10px;
      margin-top: 16px;
      padding-top: 16px;
      border-top: 1px solid rgba(255,255,255,0.10);
    }}
    .action-buttons button {{
      flex: 1;
      padding: 10px 14px;
      font-size: 13px;
      font-weight: 600;
      border-radius: 10px;
      border: none;
      cursor: pointer;
      transition: transform 0.08s ease, box-shadow 0.15s ease, opacity 0.15s ease;
    }}
    .btn-primary {{
      background: linear-gradient(135deg, #8ab4ff 0%, #9cffd6 100%);
      color: #0b0c10;
    }}
    .btn-primary:hover {{
      transform: translateY(-1px);
      box-shadow: 0 6px 20px rgba(138, 180, 255, 0.4);
    }}
    .btn-secondary {{
      background: rgba(255,255,255,0.12);
      color: rgba(255,255,255,0.92);
      border: 1px solid rgba(255,255,255,0.20);
    }}
    .btn-secondary:hover {{
      background: rgba(255,255,255,0.16);
      transform: translateY(-1px);
    }}
    .action-buttons button:disabled {{
      opacity: 0.5;
      cursor: not-allowed;
      transform: none;
    }}

    .sub-text {{
      font-size: 17px;
      line-height: 1.8;
      color: rgba(255,255,255,0.90);
      margin: 14px 0 18px;
      word-break: break-word;
      white-space: pre-wrap;
    }}

    .score-bars {{
      display: grid;
      grid-template-columns: 1fr;
      gap: 10px;
      margin: 18px 0 20px;
    }}

    .score-row {{
      display: flex;
      align-items: center;
      gap: 10px;
      font-size: 14px;
      color: rgba(255,255,255,0.75);
    }}

    .score-track {{
      position: relative;
      flex: 1;
      height: 10px;
      background: rgba(255,255,255,0.12);
      border-radius: 999px;
      overflow: hidden;
    }}

    .score-fill {{
      position: absolute;
      left: 0; top: 0; bottom: 0;
      width: 0%;
      border-radius: 999px;
    }}

    .score-fill.memory {{ background: linear-gradient(90deg, #6fd6ff, #9cffd6); }}
    .score-fill.beauty {{ background: linear-gradient(90deg, #ffd36f, #ff9f6f); }}

    .score-num {{
      width: 44px;
      text-align: right;
      font-variant-numeric: tabular-nums;
      color: rgba(255,255,255,0.9);
    }}

    #fieldReason {{
      font-size: 16px;
      line-height: 1.8;
      margin-top: 6px;
    }}

    @media (max-width: 560px) {{
      .kpi {{ grid-template-columns: 1fr; }}
      .meta-box {{ min-width: 0; }}
    }}
  </style>
  <script src="https://cdn.jsdelivr.net/npm/qrcode@1.5.1/build/qrcode.min.js"></script>
</head>
<body>
  <div class="container">
    <a class="back" href="/review">← 返回 Review</a>
    <h1>墨水屏渲染效果预览</h1>
    <div class="subtitle">
      屏幕尺寸：480 x 800&nbsp;&nbsp;
      <span style="display:inline-flex; gap:6px; vertical-align:middle;">
        <span style="width:10px;height:10px;box-sizing:border-box;border-radius:50%;background:#000;border:1px solid rgba(255,255,255,0.70);"></span>
        <span style="width:10px;height:10px;box-sizing:border-box;border-radius:50%;background:#fff;border:1px solid rgba(255,255,255,0.45);"></span>
        <span style="width:10px;height:10px;box-sizing:border-box;border-radius:50%;background:#c80000;border:1px solid rgba(255,255,255,0.18);"></span>
        <span style="width:10px;height:10px;box-sizing:border-box;border-radius:50%;background:#e0b400;border:1px solid rgba(255,255,255,0.18);"></span>
      </span>
    </div>

    <div class="controls">
      <button type="button" id="rerollBtn">同一天换一张</button>
    </div>

    <div class="status" id="statusLine"></div>

    <div class="preview-wrap">
      <div class="canvas-box">
        <canvas id="previewCanvas" width="480" height="800"></canvas>
      </div>

      <div class="meta-box">
        <div class="hero-text" id="kpiSide"></div>

        <div class="chips" id="fieldType"></div>

        <div class="sub-text" id="fieldCaption"></div>

        <div class="score-bars">
          <div class="score-row">
            <div>回忆度</div>
            <div class="score-track">
              <div class="score-fill memory" id="barMemory"></div>
            </div>
            <div class="score-num" id="numMemory"></div>
          </div>
          <div class="score-row">
            <div>美观度</div>
            <div class="score-track">
              <div class="score-fill beauty" id="barBeauty"></div>
            </div>
            <div class="score-num" id="numBeauty"></div>
          </div>
        </div>

        <div class="sub-text" id="fieldReason"></div>

        <div class="action-buttons">
          <button type="button" id="selectTodayBtn" class="btn-primary">选为今天显示照片</button>
          <button type="button" id="downloadHBtn" class="btn-secondary">将这张图片设置为手机壁纸</button>
        </div>

        <!-- 壁纸二维码模态框 -->
        <div id="wallpaperModal" class="modal" style="display:none; position:fixed; z-index:1000; left:0; top:0; width:100%; height:100%; background-color:rgba(0,0,0,0.7);">
          <div class="modal-content" style="background:#1a1a2e; margin:10% auto; padding:30px; border-radius:12px; width:90%; max-width:400px; text-align:center;">
            <h3 style="color:#fff; margin-bottom:20px;">扫描二维码设置壁纸</h3>
            <div id="qrcodeContainer" style="background:#fff; padding:20px; border-radius:8px; display:inline-block; margin-bottom:20px;">
              <canvas id="qrcodeCanvas"></canvas>
            </div>
            <p style="color:#aaa; font-size:14px; margin-bottom:20px;">使用手机扫描上方二维码<br/>即可下载并设置壁纸</p>
            <button id="closeModalBtn" style="background:linear-gradient(135deg, #667eea 0%, #764ba2 100%); color:#fff; border:none; padding:10px 30px; border-radius:6px; cursor:pointer; font-size:14px;">关闭</button>
          </div>
        </div>

        <details class="fold">
          <summary>
            <span>更多信息</span>
            <span class="fold-hint">EXIF / 路径 / 调试</span>
          </summary>

          <div class="kv-grid">
            <div class="kv-k">日期</div><div class="kv-v" id="kpiDate"></div>
            <div class="kv-k">地点</div><div class="kv-v" id="kpiLocation"></div>
            <div class="kv-k">图片URL</div><div class="kv-v" id="fieldPath"></div>
            <div class="kv-k">原始路径</div><div class="kv-v" id="fieldOrigPath"></div>
            <div class="kv-k">分辨率</div><div class="kv-v" id="fieldRes"></div>
            <div class="kv-k">方向</div><div class="kv-v" id="fieldOrientation"></div>
            <div class="kv-k">已上屏</div><div class="kv-v" id="fieldUsedAt"></div>
            <div class="kv-k">EXIF摘要</div><div class="kv-v" id="fieldExifSummary"></div>
          </div>

          <details class="fold" style="margin-top:10px;">
            <summary>
              <span>EXIF JSON</span>
              <span class="fold-hint">调试</span>
            </summary>
            <div class="mono" id="fieldExifJson"></div>
          </details>
        </details>
      </div>
    </div>
  </div>

  <script>
    const PHOTOS = {data_json};
    const SELECTED_IMG = {selected_json};

    const byDate = new Map();
    for (const p of PHOTOS) {{
      if (!p.date) continue;
      if (!byDate.has(p.date)) byDate.set(p.date, []);
      byDate.get(p.date).push(p);
    }}
    for (const [d, arr] of byDate.entries()) {{
      arr.sort((a, b) => ((b.memory ?? -1) - (a.memory ?? -1)));
    }}

    const canvas = document.getElementById('previewCanvas');
    const ctx = canvas.getContext('2d');
    const statusLine = document.getElementById('statusLine');

    const kpiDate = document.getElementById('kpiDate');
    const kpiLocation = document.getElementById('kpiLocation');
    const kpiSide = document.getElementById('kpiSide');

    const fieldPath = document.getElementById('fieldPath');
    const fieldOrigPath = document.getElementById('fieldOrigPath');
    const fieldType = document.getElementById('fieldType');
    const fieldCaption = document.getElementById('fieldCaption');
    const fieldReason = document.getElementById('fieldReason');
    const fieldRes = document.getElementById('fieldRes');
    const fieldOrientation = document.getElementById('fieldOrientation');
    const fieldUsedAt = document.getElementById('fieldUsedAt');
    const fieldExifSummary = document.getElementById('fieldExifSummary');
    const fieldExifJson = document.getElementById('fieldExifJson');

    // 评分条
    const barMemory = document.getElementById('barMemory');
    const barBeauty = document.getElementById('barBeauty');
    const numMemory = document.getElementById('numMemory');
    const numBeauty = document.getElementById('numBeauty');

    let currentDate = null;
    let currentPhoto = null;

    function formatLocation(lat, lon, city) {{
      const c = (city || '').trim();
      if (c.length > 0) return c;
      if (lat == null || lon == null) return '';
      try {{
        return Number(lat).toFixed(5) + ', ' + Number(lon).toFixed(5);
      }} catch (e) {{
        return String(lat) + ', ' + String(lon);
      }}
    }}

    function formatDateDisplay(dateStr) {{
      if (!dateStr) return '';
      const parts = dateStr.split('-');
      if (parts.length < 3) return dateStr;
      const y = parts[0];
      const m = String(parseInt(parts[1], 10));
      const d = String(parseInt(parts[2], 10));
      return y + '.' + m + '.' + d;
    }}

    function escapeHtml(s) {{
      return String(s)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
    }}

    function hashToHue(str) {{
      // 简单稳定 hash -> 0..359
      let h = 0;
      const s = String(str || '');
      for (let i = 0; i < s.length; i++) {{
        h = (h * 31 + s.charCodeAt(i)) >>> 0;
      }}
      return h % 360;
    }}

    function renderTags(tags) {{
      if (!Array.isArray(tags) || tags.length === 0) return '';
      let htmlOut = '';
      for (const t of tags) {{
        if (!t) continue;
        const hue = hashToHue(t);
        const bg = 'hsla(' + hue + ', 90%, 55%, 0.14)';
        const bd = 'hsla(' + hue + ', 90%, 55%, 0.30)';
        const dot = 'hsl(' + hue + ', 90%, 62%)';
        htmlOut += '<span class="chip" style="background:' + bg + '; border-color:' + bd + ';">'
          + '<span class="chip-dot" style="background:' + dot + ';"></span>'
          + escapeHtml(t)
          + '</span>';
      }}
      return htmlOut;
    }}

    function safeText(v) {{
      if (v === null || v === undefined) return '';
      return String(v);
    }}

    function wrapText(ctx, text, x, y, maxWidth, lineHeight, maxLines) {{
      if (!text) return;
      const words = text.split(/\\s+/);
      let line = '';
      let lineCount = 0;
      for (let n = 0; n < words.length; n++) {{
        const testLine = line ? (line + ' ' + words[n]) : words[n];
        const metrics = ctx.measureText(testLine);
        if (metrics.width > maxWidth && n > 0) {{
          ctx.fillText(line, x, y);
          line = words[n];
          y += lineHeight;
          lineCount++;
          if (lineCount >= maxLines) break;
        }} else {{
          line = testLine;
        }}
      }}
      if (line && lineCount < maxLines) ctx.fillText(line, x, y);
    }}

    function applyFourColorDither() {{
      const w = canvas.width, h = canvas.height;
      let imgData;
      try {{
        imgData = ctx.getImageData(0, 0, w, h);
      }} catch (e) {{
        statusLine.textContent = '无法从画布读取像素（跨域或图片未走 /images）：' + e;
        return;
      }}
      const data = imgData.data;

      const palette = [
        {{ r: 0, g: 0, b: 0 }},
        {{ r: 255, g: 255, b: 255 }},
        {{ r: 200, g: 0, b: 0 }},
        {{ r: 220, g: 180, b: 0 }}
      ];

      const errR = new Float32Array(w);
      const errG = new Float32Array(w);
      const errB = new Float32Array(w);
      const nextErrR = new Float32Array(w);
      const nextErrG = new Float32Array(w);
      const nextErrB = new Float32Array(w);

      function nearestColor(r, g, b) {{
        let bestIndex = 0;
        let bestDist = Infinity;
        for (let i = 0; i < palette.length; i++) {{
          const pr = palette[i].r, pg = palette[i].g, pb = palette[i].b;
          const dr = r - pr, dg = g - pg, db = b - pb;
          const dist = dr*dr + dg*dg + db*db;
          if (dist < bestDist) {{ bestDist = dist; bestIndex = i; }}
        }}
        return palette[bestIndex];
      }}

      for (let y = 0; y < h; y++) {{
        for (let x = 0; x < w; x++) {{
          const idx = (y * w + x) * 4;

          let r = data[idx] + errR[x];
          let g = data[idx + 1] + errG[x];
          let b = data[idx + 2] + errB[x];

          r = r < 0 ? 0 : (r > 255 ? 255 : r);
          g = g < 0 ? 0 : (g > 255 ? 255 : g);
          b = b < 0 ? 0 : (b > 255 ? 255 : b);

          const nc = nearestColor(r, g, b);

          data[idx] = nc.r;
          data[idx + 1] = nc.g;
          data[idx + 2] = nc.b;

          const er = r - nc.r, eg = g - nc.g, eb = b - nc.b;

          if (x + 1 < w) {{
            errR[x + 1] += er * (7 / 16);
            errG[x + 1] += eg * (7 / 16);
            errB[x + 1] += eb * (7 / 16);
          }}
          if (y + 1 < h) {{
            if (x > 0) {{
              nextErrR[x - 1] += er * (3 / 16);
              nextErrG[x - 1] += eg * (3 / 16);
              nextErrB[x - 1] += eb * (3 / 16);
            }}
            nextErrR[x] += er * (5 / 16);
            nextErrG[x] += eg * (5 / 16);
            nextErrB[x] += eb * (5 / 16);
            if (x + 1 < w) {{
              nextErrR[x + 1] += er * (1 / 16);
              nextErrG[x + 1] += eg * (1 / 16);
              nextErrB[x + 1] += eb * (1 / 16);
            }}
          }}
        }}

        if (y + 1 < h) {{
          for (let i = 0; i < w; i++) {{
            errR[i] = nextErrR[i]; errG[i] = nextErrG[i]; errB[i] = nextErrB[i];
            nextErrR[i] = 0; nextErrG[i] = 0; nextErrB[i] = 0;
          }}
        }}
      }}

      ctx.putImageData(imgData, 0, 0);
    }}

    function updateMeta(photo) {{
      if (!photo) {{
        kpiDate.textContent = '';
        kpiLocation.textContent = '';
        kpiSide.textContent = '';

        fieldPath.textContent = '';
        fieldOrigPath.textContent = '';
        fieldType.innerHTML = '';
        fieldCaption.textContent = '';
        fieldReason.textContent = '';
        fieldRes.textContent = '';
        fieldOrientation.textContent = '';
        fieldUsedAt.textContent = '';
        fieldExifSummary.textContent = '';
        fieldExifJson.textContent = '';
        // 清空评分条
        barMemory.style.width = '0%';
        barBeauty.style.width = '0%';
        numMemory.textContent = '';
        numBeauty.textContent = '';
        return;
      }}

      // 填充 meta-box 新结构
      kpiSide.textContent = photo.side ? '「' + safeText(photo.side) + '」' : '';
      fieldType.innerHTML = renderTags(photo.type);
      fieldCaption.textContent = safeText(photo.caption);

      // 评分条
      const m = photo.memory != null ? Math.max(0, Math.min(100, photo.memory)) : 0;
      const b = photo.beauty != null ? Math.max(0, Math.min(100, photo.beauty)) : 0;
      barMemory.style.width = m + '%';
      barBeauty.style.width = b + '%';
      numMemory.textContent = m ? m.toFixed(1) : '';
      numBeauty.textContent = b ? b.toFixed(1) : '';

      fieldReason.textContent = photo.reason ? '评分理由：' + safeText(photo.reason) : '';

      // 更多信息区
      const loc = formatLocation(photo.lat, photo.lon, photo.city);
      kpiDate.textContent = safeText(photo.date);
      kpiLocation.textContent = safeText(loc);
      fieldPath.textContent = safeText(photo.path);
      fieldOrigPath.textContent = safeText(photo.orig_path || '');
      const res = (safeText(photo.width) || safeText(photo.height)) ? (safeText(photo.width) + ' x ' + safeText(photo.height)) : '';
      fieldRes.textContent = res;
      fieldOrientation.textContent = safeText(photo.orientation);
      fieldUsedAt.textContent = safeText(photo.used_at);
      fieldExifSummary.textContent = safeText(photo.exif_summary);
      fieldExifJson.textContent = safeText(photo.exif_json);
    }}

    function drawPreview(photo) {{
      if (!photo) {{
        statusLine.textContent = '未指定照片。请从 /review 点击某张照片进入模拟器。';
        return;
      }}

      statusLine.textContent = ''; // 正常情况不显示废话

      canvas.width = 480;
      canvas.height = 800;

      ctx.fillStyle = '#FFFFFF';
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      const img = new Image();
      img.onload = function() {{
          canvas.width = 480;
          canvas.height = 800;
          ctx.clearRect(0, 0, canvas.width, canvas.height);
          ctx.drawImage(img, 0, 0, 480, 800);
        }};
      img.onerror = function() {{
        statusLine.textContent = '图片加载失败：' + photo.path;
      }};
      img.src = '/sim_render?img=' + encodeURIComponent(photo.path);
    }}

    function pickPhotoFromDate(date) {{
      const arr = byDate.get(date) || [];
      if (!arr.length) return null;

      const THRESHOLD = {float(getattr(cfg, "MEMORY_THRESHOLD", 70.0) or 70.0)};
      const candidates = arr.filter(p => p.memory != null && p.memory > THRESHOLD);
      if (candidates.length > 0) {{
        const idx = Math.floor(Math.random() * candidates.length);
        return {{ photo: candidates[idx], dateUsed: date }};
      }}

      // 兜底：当天随便挑
      const idx = Math.floor(Math.random() * arr.length);
      return {{ photo: arr[idx], dateUsed: date, fallbackNoThreshold: true }};
    }}

    function getPreviousDateStr(dateStr) {{
      if (!dateStr) return null;
      const parts = dateStr.split('-');
      if (parts.length < 3) return null;
      const y = parseInt(parts[0], 10);
      const m = parseInt(parts[1], 10);
      const d = parseInt(parts[2], 10);
      if (!y || !m || !d) return null;
      const dt = new Date(y, m - 1, d);
      dt.setDate(dt.getDate() - 1);
      const yy = dt.getFullYear();
      const mm = String(dt.getMonth() + 1).padStart(2, '0');
      const dd = String(dt.getDate()).padStart(2, '0');
      return yy + '-' + mm + '-' + dd;
    }}

    function pickPhotoWithLookback(baseDate) {{
      if (!baseDate) return null;
      let date = baseDate;
      const MAX_LOOKBACK = 30;

      for (let i = 0; i < MAX_LOOKBACK; i++) {{
        const picked = pickPhotoFromDate(date);
        if (picked && picked.photo) return picked;
        const prev = getPreviousDateStr(date);
        if (!prev) break;
        date = prev;
      }}

      // 最终兜底：目标日期没找到 map，啥也不干
      return null;
    }}

    function findSelectedPhoto() {{
      if (!SELECTED_IMG) return null;
      for (const p of PHOTOS) {{
        if (p.path === SELECTED_IMG) return p;
      }}
      return null;
    }}

    function onRerollSameDay() {{
      if (!currentDate) {{
        statusLine.textContent = '请从 /review 点击某张照片进入模拟器。';
        return;
      }}

      const pick = pickPhotoWithLookback(currentDate);
      if (!pick || !pick.photo) {{
        statusLine.textContent = '该日期及向前 30 天内没有可用照片。';
        return;
      }}

      // 如果刚好又抽到自己，尝试再抽几次
      let tries = 0;
      let chosen = pick;
      while (tries < 6 && chosen && chosen.photo && currentPhoto && chosen.photo.path === currentPhoto.path) {{
        const again = pickPhotoWithLookback(currentDate);
        if (!again || !again.photo) break;
        chosen = again;
        tries++;
      }}

      currentPhoto = chosen.photo;
      updateMeta(currentPhoto);
      drawPreview(currentPhoto);
    }}

    document.getElementById('rerollBtn').addEventListener('click', onRerollSameDay);

    async function onSelectToday() {{
      if (!currentPhoto) {{
        statusLine.textContent = '请先选择一张照片';
        return;
      }}

      const selectBtn = document.getElementById('selectTodayBtn');
      const downloadBtn = document.getElementById('downloadHBtn');
      selectBtn.disabled = true;
      downloadBtn.disabled = true;

      try {{
        const response = await fetch('/api/select_today', {{
          method: 'POST',
          headers: {{
            'Content-Type': 'application/json',
          }},
          body: JSON.stringify({{ path: currentPhoto.path }}),
        }});

        const result = await response.json();
        if (result.success) {{
          alert('替换成功');
        }} else {{
          alert('替换失败: ' + (result.message || '未知错误'));
        }}
      }} catch (error) {{
        alert('替换失败: ' + error.message);
      }} finally {{
        selectBtn.disabled = false;
        downloadBtn.disabled = false;
      }}
    }}

    async function onDownloadH() {{
      if (!currentPhoto) {{
        statusLine.textContent = '请先选择一张照片';
        return;
      }}

      if (!currentPhoto.path) {{
        alert('无法获取照片路径');
        return;
      }}

      statusLine.textContent = '正在生成壁纸...';

      try {{
        console.log('开始生成壁纸，照片路径:', currentPhoto.path);
        
        const response = await fetch('/api/generate_wallpaper', {{
          method: 'POST',
          headers: {{
            'Content-Type': 'application/json',
          }},
          body: JSON.stringify({{ path: currentPhoto.path }}),
        }});

        console.log('API响应状态:', response.status);
        
        if (response.ok) {{
          const data = await response.json();
          console.log('API返回数据:', data);
          
          if (data.success && data.wallpaper_url) {{
            // 使用qrcodejs库在前端生成二维码
            const qrcodeContainer = document.getElementById('qrcodeContainer');
            if (!qrcodeContainer) {{
              throw new Error('找不到qrcodeContainer元素');
            }}
            
            // 清空之前的内容
            qrcodeContainer.innerHTML = '';
            
            // 创建新的二维码
            if (typeof QRCode === 'undefined') {{
              throw new Error('QRCode库未加载');
            }}
            
            // 创建canvas元素
            var canvas = document.createElement('canvas');
            canvas.width = 200;
            canvas.height = 200;
            qrcodeContainer.appendChild(canvas);
            
            // 使用QRCode.toCanvas生成二维码
            QRCode.toCanvas(canvas, data.wallpaper_url, {{
              width: 200,
              margin: 2,
              color: {{
                dark: '#000000',
                light: '#ffffff'
              }}
            }}, function(error) {{
              if (error) {{
                console.error('二维码生成失败:', error);
                qrcodeContainer.innerHTML = '<p style="color:red;">二维码生成失败</p>';
              }}
            }});
            
            document.getElementById('wallpaperModal').style.display = 'block';
            statusLine.textContent = '';
          }} else {{
            alert('生成壁纸失败: ' + (data.message || '未知错误'));
            statusLine.textContent = '';
          }}
        }} else {{
          const errorText = await response.text();
          alert('生成壁纸失败: ' + errorText);
          statusLine.textContent = '';
        }}
      }} catch (error) {{
        console.error('生成壁纸错误:', error);
        alert('生成壁纸时发生错误: ' + error.message);
        statusLine.textContent = '';
      }}
    }}

    // 关闭模态框
    document.getElementById('closeModalBtn').addEventListener('click', function() {{
      document.getElementById('wallpaperModal').style.display = 'none';
    }});

    // 点击模态框外部关闭
    document.getElementById('wallpaperModal').addEventListener('click', function(e) {{
      if (e.target === this) {{
        this.style.display = 'none';
      }}
    }});

    document.getElementById('selectTodayBtn').addEventListener('click', onSelectToday);
    document.getElementById('downloadHBtn').addEventListener('click', onDownloadH);

    // 默认进入：如果从 review 点进来，则显示该照片；否则提示用户从 review 进入
    const initPhoto = findSelectedPhoto();
    if (!initPhoto) {{
      updateMeta(null);
      drawPreview(null);
    }} else {{
      currentDate = initPhoto.date;
      currentPhoto = initPhoto;
      updateMeta(currentPhoto);
      drawPreview(currentPhoto);
    }}
  </script>
</body>
</html>
"""
    return html_str


# --------------------------
# Routes
# --------------------------

@app.get("/")
def index():
    if ENABLE_REVIEW_WEBUI:
        return redirect("/review")
    return Response("InkTime server running. WebUI disabled.", mimetype="text/plain; charset=utf-8")


@app.get("/login")
def login_get():
    return Response(build_login_html(), mimetype="text/html; charset=utf-8")


@app.post("/login")
def login_post():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    
    if username == LOGIN_USERNAME and password == LOGIN_PASSWORD:
        session['logged_in'] = True
        return redirect('/review')
    else:
        return Response(build_login_html('用户名或密码错误'), mimetype="text/html; charset=utf-8")


@app.get("/logout")
def logout():
    session.pop('logged_in', None)
    return redirect('/login')


@app.get("/review")
def review():
    if session.get('logged_in') != True:
        return redirect('/login')
    _require_webui_enabled()
    try:
        page = int(request.args.get("page", "1"))
    except Exception:
        page = 1

    md = (request.args.get('md', '') or '').strip()
    sort = (request.args.get('sort', '') or 'memory').strip() or 'memory'

    rows, total_count = load_rows(page=page, page_size=REVIEW_PAGE_SIZE, md=md, sort=sort)
    if not rows:
        return Response(
            "数据库里没有可展示的数据。请先运行你的分析脚本生成评分与文案。",
            status=404,
            mimetype="text/plain; charset=utf-8",
        )

    html_str = build_html(rows, page=page, page_size=REVIEW_PAGE_SIZE, total_count=total_count)
    return Response(html_str, mimetype="text/html; charset=utf-8")


# API endpoint for md list
@app.get('/api/md_list')
def api_md_list():
    _require_webui_enabled()
    md_list = _load_all_md_list()
    return Response(json.dumps(md_list, ensure_ascii=False), mimetype='application/json; charset=utf-8')


@app.get("/sim")
def sim():
    if session.get('logged_in') != True:
        return redirect('/login')
    _require_webui_enabled()
    selected_img = request.args.get("img", "")

    # 默认不再全库加载，避免 /sim 页面巨大 JSON 导致浏览器转圈
    sim_rows = []

    # 仅当从 /review 点进来且参数合法时，按“该日期 + 向前 30 天”加载
    if selected_img and isinstance(selected_img, str) and selected_img.startswith("/images/"):
        subpath = selected_img[len("/images/"):]
        try:
            p = _safe_join(IMAGE_DIR, subpath)
        except Exception:
            p = None

        if p is not None and p.exists() and p.is_file():
            meta = get_photo_meta_by_path(str(p))
            base_date = meta.get("date") if meta else ""

            if base_date:
                try:
                    from datetime import datetime, timedelta
                    dt0 = datetime.strptime(base_date, "%Y-%m-%d")
                    dates = [(dt0 - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(0, 31)]
                except Exception:
                    dates = [base_date]

                sim_rows = load_sim_rows_for_dates(dates)
                
                selected_in_rows = any(str(r[0]) == str(p) for r in sim_rows)
                if not selected_in_rows:
                    conn = sqlite3.connect(DB_PATH)
                    c = conn.cursor()
                    row = c.execute(
                        """
                        SELECT path,
                               caption,
                               type,
                               memory_score,
                               beauty_score,
                               reason,
                               side_caption,
                               exif_json,
                               width,
                               height,
                               orientation,
                               used_at,
                               exif_gps_lat,
                               exif_gps_lon,
                               exif_city
                        FROM photo_scores
                        WHERE path = ?
                        LIMIT 1
                        """,
                        (str(p),),
                    ).fetchone()
                    conn.close()
                    if row:
                        sim_rows.append(row)
    html_str = build_simulator_html(sim_rows, selected_img=selected_img)
    return Response(html_str, mimetype="text/html; charset=utf-8")


@app.get("/images/<path:subpath>")
def images(subpath: str):
    if session.get('logged_in') != True:
        abort(403)
    _require_webui_enabled()
    try:
        p = _safe_join(IMAGE_DIR, subpath)
    except Exception:
        abort(400)
    return _send_static_file(p)


@app.get("/sim_render")
def sim_render():
    if session.get('logged_in') != True:
        abort(403)
    _require_webui_enabled()

    img_uri = request.args.get("img", "")
    if not img_uri or not img_uri.startswith("/images/"):
        abort(400)

    subpath = img_uri[len("/images/"):]
    try:
        p = _safe_join(IMAGE_DIR, subpath)
    except Exception:
        abort(400)

    if not p.exists() or not p.is_file():
        abort(404)

    meta = get_photo_meta_by_path(str(p))
    if meta is None:
        # 兜底：DB 没命中就渲染纯图（不建议长期这样）
        meta = {
            "path": str(p),
            "date": "",
            "side": "",
            "memory": None,
            "lat": None,
            "lon": None,
            "city": "",
        }

    try:
        img = rdp.render_image(meta)
        img_dithered = rdp.apply_four_color_dither(img)

        bio = BytesIO()
        img_dithered.save(bio, format="PNG")
        bio.seek(0)
        return send_file(bio, mimetype="image/png", as_attachment=False)
    except Exception:
        abort(500)

@app.get("/static/inktime/<key>/photo_<int:idx>.bin")
def esp_photo(key: str, idx: int):
    if key != DOWNLOAD_KEY:
        abort(404)
    if idx < 0 or idx >= DAILY_PHOTO_QUANTITY:
        abort(404)
    p = BIN_OUTPUT_DIR / f"photo_{idx}.bin"
    return _send_static_file(p)


@app.get("/static/inktime/<key>/latest.bin")
def esp_latest(key: str):
    if key != DOWNLOAD_KEY:
        abort(404)
    p = BIN_OUTPUT_DIR / "latest.bin"
    return _send_static_file(p)


@app.get("/static/inktime/<key>/preview.png")
def esp_preview(key: str):
    if key != DOWNLOAD_KEY:
        abort(404)
    p = BIN_OUTPUT_DIR / "preview.png"
    return _send_static_file(p)


def _upload_to_obs(filename: str, content: str) -> str:
    """上传文件到华为云OBS（使用标准AWS Signature Version 4）"""
    import os
    import hmac
    import hashlib
    import base64
    import urllib.parse
    from datetime import datetime
    
    try:
        import requests
    except ImportError:
        print("[OBS] requests库未安装")
        return ""
    
    # 从环境变量获取OBS配置
    obs_endpoint = os.environ.get('OBS_ENDPOINT', 'obs.cn-north-4.myhuaweicloud.com')
    obs_bucket = os.environ.get('OBS_BUCKET', 'mypublicbucket0101')
    obs_ak = os.environ.get('OBS_ACCESS_KEY')
    obs_sk = os.environ.get('OBS_SECRET_KEY')
    
    if not obs_ak or not obs_sk:
        print("[OBS] 未配置OBS凭证（OBS_ACCESS_KEY/OBS_SECRET_KEY）")
        return ""
    
    try:
        # 当前时间
        now = datetime.utcnow()
        date_str = now.strftime('%Y%m%d')
        datetime_str = now.strftime('%Y%m%dT%H%M%SZ')
        
        # 区域和服务
        region = 'cn-north-4'
        service = 's3'  # OBS兼容S3
        
        # 内容
        content_bytes = content.encode('utf-8')
        content_hash = hashlib.sha256(content_bytes).hexdigest()
        
        # 请求参数
        host = f'{obs_bucket}.{obs_endpoint}'
        uri = f'/images/{filename}'
        
        # 构建Canonical Request
        canonical_uri = uri
        canonical_querystring = ''
        
        # 构建Canonical Headers（按字典序排序）
        canonical_headers = f'content-type:text/plain\nhost:{host}\nx-amz-content-sha256:{content_hash}\nx-amz-date:{datetime_str}\n'
        
        # 签名头部
        signed_headers = 'content-type;host;x-amz-content-sha256;x-amz-date'
        
        # 构建Canonical Request
        canonical_request = f"PUT\n{canonical_uri}\n{canonical_querystring}\n{canonical_headers}\n{signed_headers}\n{content_hash}"
        
        # 构建String to Sign
        algorithm = 'AWS4-HMAC-SHA256'
        credential_scope = f'{date_str}/{region}/{service}/aws4_request'
        string_to_sign = f"{algorithm}\n{datetime_str}\n{credential_scope}\n{hashlib.sha256(canonical_request.encode()).hexdigest()}"
        
        # 计算签名
        def sign(key, msg):
            return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()
        
        k_date = sign(('AWS4' + obs_sk).encode(), date_str)
        k_region = sign(k_date, region)
        k_service = sign(k_region, service)
        k_signing = sign(k_service, 'aws4_request')
        
        signature = hmac.new(k_signing, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()
        
        # 构建Authorization头
        authorization = f"{algorithm} Credential={obs_ak}/{credential_scope},SignedHeaders={signed_headers},Signature={signature}"
        
        # 发送请求
        url = f'https://{host}{uri}'
        headers = {
            'Content-Type': 'text/plain',
            'x-amz-acl': 'public-read',  # 使用S3兼容的ACL头
            'x-amz-date': datetime_str,
            'x-amz-content-sha256': content_hash,
            'Authorization': authorization,
        }
        
        response = requests.put(url, data=content_bytes, headers=headers, timeout=30)
        
        if response.status_code in [200, 201]:
            print(f"[OBS] 成功上传 {filename} 到 OBS")
            return "上传成功"
        else:
            print(f"[OBS] 上传失败: HTTP {response.status_code} - {response.text}")
            return f"失败({response.status_code})"
            
    except Exception as e:
        print(f"[OBS] 上传异常: {e}")
        return f"失败({str(e)})"


def _render_and_generate_h(photo_path, caption="", date_display=""):
    """渲染照片并生成.h文件内容（与render_daily_photo.py保持一致）"""
    from PIL import Image, ImageDraw, ImageFont, ImageOps
    import config as cfg
    
    CANVAS_WIDTH = 480
    CANVAS_HEIGHT = 800
    TEXT_AREA_HEIGHT = 100
    
    PALETTE = [
        (0, 0, 0),
        (255, 255, 255),
        (200, 0, 0),
        (220, 180, 0),
    ]
    
    COLOR_MAP = {0: 3, 1: 0, 2: 2, 3: 1}
    
    def nearest_palette_color(r, g, b):
        best_idx = 0
        best_dist = float("inf")
        for i, (pr, pg, pb) in enumerate(PALETTE):
            dr = r - pr
            dg = g - pg
            db = b - pb
            dist = dr * dr + dg * dg + db * db
            if dist < best_dist:
                best_dist = dist
                best_idx = i
        return best_idx
    
    def apply_four_color_dither(img):
        w, h = img.size
        img = img.convert('RGB')
        pixels = img.load()
        
        err_r = [0.0] * w
        err_g = [0.0] * w
        err_b = [0.0] * w
        next_err_r = [0.0] * w
        next_err_g = [0.0] * w
        next_err_b = [0.0] * w
        
        for y in range(h):
            for x in range(w):
                r, g, b = pixels[x, y]
                r = max(0.0, min(255.0, r + err_r[x]))
                g = max(0.0, min(255.0, g + err_g[x]))
                b = max(0.0, min(255.0, b + err_b[x]))
                
                best_idx = nearest_palette_color(r, g, b)
                pr, pg, pb = PALETTE[best_idx]
                pixels[x, y] = (pr, pg, pb)
                
                er = r - pr
                eg = g - pg
                eb = b - pb
                
                if x + 1 < w:
                    err_r[x + 1] += er * (7.0 / 16.0)
                    err_g[x + 1] += eg * (7.0 / 16.0)
                    err_b[x + 1] += eb * (7.0 / 16.0)
                if y + 1 < h:
                    if x > 0:
                        next_err_r[x - 1] += er * (3.0 / 16.0)
                        next_err_g[x - 1] += eg * (3.0 / 16.0)
                        next_err_b[x - 1] += eb * (3.0 / 16.0)
                    next_err_r[x] += er * (5.0 / 16.0)
                    next_err_g[x] += eg * (5.0 / 16.0)
                    next_err_b[x] += eb * (5.0 / 16.0)
                    if x + 1 < w:
                        next_err_r[x + 1] += er * (1.0 / 16.0)
                        next_err_g[x + 1] += eg * (1.0 / 16.0)
                        next_err_b[x + 1] += eb * (1.0 / 16.0)
            
            if y + 1 < h:
                for i in range(w):
                    err_r[i] = next_err_r[i]
                    err_g[i] = next_err_g[i]
                    err_b[i] = next_err_b[i]
                    next_err_r[i] = 0.0
                    next_err_g[i] = 0.0
                    next_err_b[i] = 0.0
        return img
    
    def rotate_cw_90(old_pixels, old_w, old_h):
        new_w = old_h
        new_h = old_w
        new_pixels = [0] * (new_w * new_h)
        for old_row in range(old_h):
            for old_col in range(old_w):
                new_col = old_row
                new_row = new_h - 1 - old_col
                old_idx = old_row * old_w + old_col
                new_idx = new_row * new_w + new_col
                new_pixels[new_idx] = old_pixels[old_idx]
        return new_pixels
    
    def pack_2bpp(pixels, width, height):
        result = bytearray()
        for row in range(height):
            for col in range(0, width, 4):
                idx = row * width + col
                p0 = COLOR_MAP.get(pixels[idx], 0)
                p1 = COLOR_MAP.get(pixels[idx + 1], 0) if col + 1 < width else 0
                p2 = COLOR_MAP.get(pixels[idx + 2], 0) if col + 2 < width else 0
                p3 = COLOR_MAP.get(pixels[idx + 3], 0) if col + 3 < width else 0
                byte = (p0 << 6) | (p1 << 4) | (p2 << 2) | p3
                result.append(byte)
        return bytes(result)
    
    def image_to_palette_bin(img):
        w, h = img.size
        pixels = []
        for y in range(h):
            for x in range(w):
                r, g, b = img.getpixel((x, y))
                for i, (pr, pg, pb) in enumerate(PALETTE):
                    if r == pr and g == pg and b == pb:
                        pixels.append(i)
                        break
                else:
                    pixels.append(nearest_palette_color(r, g, b))
        return pixels
    
    def wrap_text_chinese(draw, text, font, max_width, max_lines):
        if not text:
            return []
        lines = []
        line = ""
        for ch in text:
            test = line + ch
            w = draw.textlength(test, font=font)
            if w <= max_width:
                line = test
            else:
                if line:
                    lines.append(line)
                line = ch
                if len(lines) >= max_lines:
                    break
        if line and len(lines) < max_lines:
            lines.append(line)
        return lines
    
    # 渲染照片
    img = Image.open(photo_path)
    img = ImageOps.exif_transpose(img).convert("RGB")
    
    img_w, img_h = img.size
    img_area_w = CANVAS_WIDTH
    img_area_h = CANVAS_HEIGHT - TEXT_AREA_HEIGHT
    
    scale = max(img_area_w / img_w, img_area_h / img_h)
    draw_w = int(img_w * scale)
    draw_h = int(img_h * scale)
    img_resized = img.resize((draw_w, draw_h), Image.LANCZOS)
    
    left = max(0, (draw_w - img_area_w) // 2)
    top = max(0, (draw_h - img_area_h) // 2)
    img_cropped = img_resized.crop((left, top, left + img_area_w, top + img_area_h))
    
    canvas = Image.new('RGB', (CANVAS_WIDTH, CANVAS_HEIGHT), (255, 255, 255))
    canvas.paste(img_cropped, (0, 0))
    
    draw = ImageDraw.Draw(canvas)
    
    # 使用与render_daily_photo.py相同的字体配置
    FONT_PATH = Path(str(getattr(cfg, "FONT_PATH", "") or "")).expanduser()
    if str(FONT_PATH) and not FONT_PATH.is_absolute():
        FONT_PATH = (ROOT_DIR / FONT_PATH).resolve()
    
    try:
        font_big = ImageFont.truetype(str(FONT_PATH), 22)
        font_small = ImageFont.truetype(str(FONT_PATH), 20)
    except Exception:
        font_big = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    # 底部文字区域（与render_daily_photo.py一致）
    padding_x = 24
    text_area_top = CANVAS_HEIGHT - TEXT_AREA_HEIGHT + 10
    text_width = CANVAS_WIDTH - 2 * padding_x
    
    # 文案：最多两行，黑色（与render_daily_photo.py一致）
    y = text_area_top
    if caption:
        lines = wrap_text_chinese(draw, caption, font_big, text_width, max_lines=2)
        for line in lines:
            draw.text((padding_x, y), line, font=font_big, fill=(0, 0, 0))
            y += 24
    
    # 日期：黑色，固定在第二行（与render_daily_photo.py一致）
    second_line_y = text_area_top + 54
    if date_display:
        draw.text((padding_x, second_line_y), date_display, font=font_small, fill=(0, 0, 0))
    
    dithered = apply_four_color_dither(canvas)
    pixels = image_to_palette_bin(dithered)
    rotated = rotate_cw_90(pixels, CANVAS_WIDTH, CANVAS_HEIGHT)
    packed = pack_2bpp(rotated, CANVAS_HEIGHT, CANVAS_WIDTH)
    
    return packed


@app.post("/api/generate_h")
def api_generate_h():
    if session.get('logged_in') != True:
        return Response(json.dumps({'success': False, 'message': '未登录'}), status=401, mimetype='application/json')
    
    try:
        data = request.get_json()
        img_path = data.get('path', '')
        
        if not img_path or not img_path.startswith('/images/'):
            return Response(json.dumps({'success': False, 'message': '无效的图片路径'}), status=400, mimetype='application/json')
        
        subpath = img_path[len('/images/'):]
        p = _safe_join(IMAGE_DIR, subpath)
        
        if not p.exists() or not p.is_file():
            return Response(json.dumps({'success': False, 'message': '图片不存在'}), status=404, mimetype='application/json')
        
        # 获取照片元数据（使用绝对路径查询）
        abs_path = str(p.resolve())
        meta = get_photo_meta_by_path(abs_path)
        caption = meta.get('side', '') if meta else ''
        date_display = meta.get('date', '') if meta else ''
        
        # 生成.h文件内容
        packed = _render_and_generate_h(abs_path, caption, date_display)
        
        # 生成.h文件格式
        hex_strs = [f'0X{b:02X}' for b in packed]
        lines = []
        lines.append('const unsigned char gImage_1[96000] = { /* 0X00,0X02,0X20,0X03,0XE0,0X01, */')
        for i in range(0, len(hex_strs), 16):
            chunk = hex_strs[i:i+16]
            lines.append(','.join(chunk) + ',')
        lines[-1] = lines[-1].rstrip(',')
        lines.append('};')
        
        h_content = '\n'.join(lines)
        
        # 获取日期用于文件名
        today = datetime.now()
        filename = f"{today:%m%d}.h"
        
        return Response(h_content, mimetype='text/plain', headers={
            'Content-Disposition': f'attachment; filename="{filename}"'
        })
        
    except Exception as e:
        return Response(json.dumps({'success': False, 'message': str(e)}), status=500, mimetype='application/json')


@app.post("/api/select_today")
def api_select_today():
    if session.get('logged_in') != True:
        return Response(json.dumps({'success': False, 'message': '未登录'}), status=401, mimetype='application/json')
    
    try:
        data = request.get_json()
        img_path = data.get('path', '')
        
        if not img_path or not img_path.startswith('/images/'):
            return Response(json.dumps({'success': False, 'message': '无效的图片路径'}), status=400, mimetype='application/json')
        
        subpath = img_path[len('/images/'):]
        p = _safe_join(IMAGE_DIR, subpath)
        
        if not p.exists() or not p.is_file():
            return Response(json.dumps({'success': False, 'message': '图片不存在'}), status=404, mimetype='application/json')
        
        # 获取照片元数据（使用绝对路径查询）
        abs_path = str(p.resolve())
        meta = get_photo_meta_by_path(abs_path)
        caption = meta.get('side', '') if meta else ''
        date_display = meta.get('date', '') if meta else ''
        
        # 生成.h文件内容
        packed = _render_and_generate_h(abs_path, caption, date_display)
        
        # 生成.h文件格式
        hex_strs = [f'0X{b:02X}' for b in packed]
        lines = []
        lines.append('const unsigned char gImage_1[96000] = { /* 0X00,0X02,0X20,0X03,0XE0,0X01, */')
        for i in range(0, len(hex_strs), 16):
            chunk = hex_strs[i:i+16]
            lines.append(','.join(chunk) + ',')
        lines[-1] = lines[-1].rstrip(',')
        lines.append('};')
        
        h_content = '\n'.join(lines)
        
        # 获取今天日期用于文件名
        today = datetime.now()
        mmdd = f"{today:%m%d}"
        filename = f"{mmdd}.h"
        
        # 保存到本地data目录
        data_dir = Path(__file__).parent / 'data'
        data_dir.mkdir(exist_ok=True)
        local_path = data_dir / filename
        local_path.write_text(h_content, encoding='utf-8')
        
        # 尝试上传到华为云OBS
        obs_result = _upload_to_obs(filename, h_content)
        
        return Response(json.dumps({
            'success': True, 
            'message': '替换成功' + (f'，OBS: {obs_result}' if obs_result else '（本地）'),
            'filename': filename,
            'obs_upload': obs_result
        }), mimetype='application/json')
        
    except Exception as e:
        return Response(json.dumps({'success': False, 'message': str(e)}), status=500, mimetype='application/json')


@app.post("/api/generate_wallpaper")
def api_generate_wallpaper():
    """生成手机壁纸并返回下载URL"""
    if session.get('logged_in') != True:
        return Response(json.dumps({'success': False, 'message': '未登录'}), status=401, mimetype='application/json')
    
    try:
        data = request.get_json()
        img_path = data.get('path', '')
        
        if not img_path or not img_path.startswith('/images/'):
            return Response(json.dumps({'success': False, 'message': '无效的图片路径'}), status=400, mimetype='application/json')
        
        subpath = img_path[len('/images/'):]
        p = _safe_join(IMAGE_DIR, subpath)
        
        if not p.exists() or not p.is_file():
            return Response(json.dumps({'success': False, 'message': '图片不存在'}), status=404, mimetype='application/json')
        
        # 生成壁纸
        from PIL import Image, ImageOps
        import hashlib
        
        # 打开原图
        img = Image.open(p)
        img = ImageOps.exif_transpose(img).convert("RGB")
        
        # 手机壁纸尺寸 (9:16 比例，适合大多数手机)
        WALLPAPER_WIDTH = 1080
        WALLPAPER_HEIGHT = 1920
        
        # 计算缩放比例
        img_w, img_h = img.size
        scale = max(WALLPAPER_WIDTH / img_w, WALLPAPER_HEIGHT / img_h)
        new_w = int(img_w * scale)
        new_h = int(img_h * scale)
        
        # 缩放并裁剪
        img_resized = img.resize((new_w, new_h), Image.LANCZOS)
        left = max(0, (new_w - WALLPAPER_WIDTH) // 2)
        top = max(0, (new_h - WALLPAPER_HEIGHT) // 2)
        img_cropped = img_resized.crop((left, top, left + WALLPAPER_WIDTH, top + WALLPAPER_HEIGHT))
        
        # 生成唯一文件名
        file_hash = hashlib.md5(str(p).encode()).hexdigest()[:8]
        wallpaper_filename = f"wallpaper_{file_hash}.jpg"
        wallpaper_path = BIN_OUTPUT_DIR / wallpaper_filename
        
        # 保存壁纸
        img_cropped.save(wallpaper_path, "JPEG", quality=95)
        
        # 生成完整的下载URL（使用完整URL以便手机访问）
        wallpaper_url = f"http://{request.host}/static/inktime/{DOWNLOAD_KEY}/{wallpaper_filename}"
        
        return Response(json.dumps({
            'success': True,
            'wallpaper_url': wallpaper_url,
            'filename': wallpaper_filename
        }), mimetype='application/json')
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return Response(json.dumps({'success': False, 'message': str(e)}), status=500, mimetype='application/json')


@app.get("/static/inktime/<key>/<filename>")
def serve_wallpaper(key: str, filename: str):
    """提供壁纸和二维码文件下载"""
    if key != DOWNLOAD_KEY:
        abort(404)
    
    file_path = BIN_OUTPUT_DIR / filename
    if not file_path.exists():
        abort(404)
    
    # 根据文件扩展名确定MIME类型
    if filename.endswith('.png'):
        return send_file(file_path, mimetype='image/png')
    else:
        return send_file(file_path, mimetype='image/jpeg', as_attachment=True, download_name=filename)


@app.get("/files/")
@app.get("/files/<path:subpath>")
def browse(subpath: str = ""):
    _require_webui_enabled()
    try:
        p = _safe_join(BIN_OUTPUT_DIR, subpath)
    except Exception:
        abort(400)

    if p.is_file():
        return _send_static_file(p)

    if not p.exists() or not p.is_dir():
        abort(404)

    items = []
    for child in sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
        name = child.name + ("/" if child.is_dir() else "")
        rel = child.relative_to(BIN_OUTPUT_DIR)
        href = "/files/" + str(rel).replace("\\", "/")
        items.append(f'<li><a href="{html.escape(href)}">{html.escape(name)}</a></li>')

    up = ""
    if p != BIN_OUTPUT_DIR:
        parent_rel = p.parent.relative_to(BIN_OUTPUT_DIR)
        up_href = "/files/" + str(parent_rel).replace("\\", "/")
        up = f'<a href="{html.escape(up_href)}">⬅ 返回上级</a><br><br>'

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>InkTime Files</title>
<style>
body {{ font-family: -apple-system,BlinkMacSystemFont,system-ui,sans-serif; padding: 24px; }}
ul {{ line-height: 1.8; }}
code {{ background:#f2f2f2; padding:2px 6px; border-radius:4px; }}
</style>
</head>
<body>
<h3>输出目录浏览</h3>
<p>当前：<code>{html.escape(str(p.relative_to(BIN_OUTPUT_DIR) if p != BIN_OUTPUT_DIR else "."))}</code></p>
{up}
<ul>
{''.join(items)}
</ul>
</body>
</html>
"""


if __name__ == "__main__":
    mimetypes.add_type("application/octet-stream", ".bin")
    print(f"[InkTime] DB: {DB_PATH}")
    print(f"[InkTime] IMAGE_DIR: {IMAGE_DIR}")
    print(f"[InkTime] OUT: {BIN_OUTPUT_DIR}")
    print(f"[InkTime] key: {DOWNLOAD_KEY}")
    print(f"[InkTime] listen: {FLASK_HOST}:{FLASK_PORT}")
    print(f"[InkTime] open: http://127.0.0.1:{FLASK_PORT}/  (本机)")
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=False)