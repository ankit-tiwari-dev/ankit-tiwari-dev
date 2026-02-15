#!/usr/bin/env python3
import os
import sys
import json
import math
from datetime import datetime, timedelta
from urllib.request import Request, urlopen

def github_get(url, token=None):
    req = Request(url, headers={"User-Agent": "widget-generator"})
    if token:
        req.add_header("Authorization", f"token {token}")
    with urlopen(req) as resp:
        return json.load(resp)

def fetch_repos(username, token=None):
    url = f"https://api.github.com/users/{username}/repos?per_page=100"
    return github_get(url, token)

def fetch_user(username, token=None):
    url = f"https://api.github.com/users/{username}"
    return github_get(url, token)

def fetch_events(username, token=None):
    url = f"https://api.github.com/users/{username}/events/public?per_page=100"
    return github_get(url, token)

def aggregate_languages(repos):
    counts = {}
    for r in repos:
        lang = r.get("language") or "Unknown"
        counts[lang] = counts.get(lang, 0) + 1
    # sort
    items = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    return items

def make_repos_language_svg(items, outpath):
    # Simple horizontal list of language badges
    width = 700
    height = 100
    gap = 8
    x = 12
    parts = []
    parts.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">')
    parts.append('<rect width="100%" height="100%" fill="#000000"/>')
    badge_w = 140
    badge_h = 44
    font_size = 15
    font_weight = 700
    for i, (lang, cnt) in enumerate(items[:6]):
        label = f"{lang} ({cnt})"
        # subtle gold highlight for top language
        if i == 0:
            parts.append(f'<rect x="{x-2}" y="22" width="{badge_w+4}" height="{badge_h}" rx="6" fill="#070707" stroke="#FFD166" stroke-width="2"/>')
        parts.append(f'<rect x="{x}" y="24" width="{badge_w}" height="{badge_h-4}" rx="6" fill="#000000" stroke="#222222"/>')
        parts.append(f'<text x="{x+badge_w/2}" y="{24 + badge_h/2 + 6}" fill="#00d4ff" font-family="Inter, Arial, sans-serif" font-size="{font_size}" font-weight="{font_weight}" text-anchor="middle">{label}</text>')
        x += badge_w + gap
    parts.append('</svg>')
    with open(outpath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(parts))

def make_most_commit_language_svg(items, outpath):
    top = items[0] if items else ("None", 0)
    text = f"Most-used language: {top[0]} ({top[1]} repos)"
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="640" height="64">
  <rect width="100%" height="100%" fill="#000000" />
  <text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" fill="#00d4ff" font-family="Inter, Arial, sans-serif" font-size="18" font-weight="700">{text}</text>
</svg>'''
    with open(outpath, 'w', encoding='utf-8') as f:
        f.write(svg)

def make_profile_svg(user, outpath):
    name = user.get('name') or user.get('login')
    followers = user.get('followers', 0)
    repos = user.get('public_repos', 0)
    created = user.get('created_at', '')
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="420" height="100">
  <rect width="100%" height="100%" fill="#000000" />
  <text x="18" y="36" fill="#FFFFFF" font-family="Inter, Arial, sans-serif" font-size="18" font-weight="700">{name}</text>
  <text x="18" y="64" fill="#00d4ff" font-family="Inter, Arial, sans-serif" font-size="14">Followers: {followers} • Repos: {repos} • Joined: {created[:10]}</text>
</svg>'''
    with open(outpath, 'w', encoding='utf-8') as f:
        f.write(svg)

def make_activity_svg(daily_counts, outpath):
    width = 600
    height = 80
    maxc = max(daily_counts) if daily_counts else 1
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">']
    parts.append('<rect width="100%" height="100%" fill="#000000"/>')
    # draw sparkline
    margin = 10
    w = width - margin*2
    h = height - margin*2
    n = len(daily_counts)
    if n:
        step = w / max(n-1, 1)
        points = []
        for i, v in enumerate(daily_counts):
            x = margin + i*step
            y = margin + h - (v / maxc) * h
            points.append(f"{x},{y}")
        points_str = ' '.join(points)
        parts.append(f'<polyline points="{points_str}" fill="none" stroke="#00d4ff" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>')
        # add subtle baseline and gold marker at latest point
        if n:
            parts.append(f'<line x1="{margin}" y1="{margin+h+6}" x2="{margin+w}" y2="{margin+h+6}" stroke="#111" stroke-width="1"/>')
            parts.append(f'<circle cx="{margin + (n-1)*step}" cy="{margin + h - (daily_counts[-1]/maxc)*h}" r="4" fill="#FFD166" stroke="#222" stroke-width="0.8"/>')
    parts.append('</svg>')
    with open(outpath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(parts))

def main():
    username = os.environ.get('WIDGET_GH_USER') or os.environ.get('USERNAME') or 'ankit-tiwari-dev'
    token = os.environ.get('GITHUB_TOKEN')
    outdir = os.path.join(os.getcwd(), 'assets', 'generated')
    os.makedirs(outdir, exist_ok=True)

    repos = fetch_repos(username, token)
    user = fetch_user(username, token)
    events = fetch_events(username, token)

    langs = aggregate_languages(repos)
    make_repos_language_svg(langs, os.path.join(outdir, 'repos_per_language.svg'))
    make_most_commit_language_svg(langs, os.path.join(outdir, 'most_commit_language.svg'))
    make_profile_svg(user, os.path.join(outdir, 'profile_stats.svg'))

    # activity: counts per day for last 30 days using events
    days = 30
    counts = [0] * days
    today = datetime.utcnow().date()
    for ev in events:
        dt = datetime.strptime(ev['created_at'], '%Y-%m-%dT%H:%M:%SZ').date()
        diff = (today - dt).days
        if 0 <= diff < days:
            counts[days-1-diff] += 1
    make_activity_svg(counts, os.path.join(outdir, 'activity_last30.svg'))

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print('Error generating widgets:', e)
        sys.exit(1)
