"""Build the daily email digest and the Teams card from digest-data.json.

    python build_digests.py            -> email.html, email-preview.html, teams-card.json, teams-preview.html

Styled to match the dashboard: Aldar dark theme, Poppins, rounded corners.

email.html is the message body itself (table layout, inline styles, safe for Outlook).
email-preview.html wraps it in an inbox-style frame for review.
teams-card.json is an Adaptive Card (v1.5) that a Teams Workflow or bot can post.
teams-preview.html renders that same card with the official Adaptive Cards renderer
(inlined if adaptivecards.min.js sits next to this script, otherwise loaded from jsDelivr).
"""
import json, html, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
D = json.load(open(os.path.join(HERE, 'digest-data.json'), encoding='utf-8'))
e = lambda s: html.escape(str(s), quote=True)
MINUS = '−'

def bp(n):
    return '0' if n == 0 else ('+' if n > 0 else MINUS) + str(abs(n))

def fix_minus(s):
    return s.replace('-', MINUS) if s[:1] == '-' else s

def mix(hex_a, hex_b, p):
    a = [int(hex_a[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(hex_b[i:i + 2], 16) for i in (1, 3, 5)]
    return '#' + ''.join(f'{round(x * p + y * (1 - p)):02x}' for x, y in zip(a, b))

# Aldar dark palette, same values as the dashboard's :root
UP, DOWN, MID, INK, INK2, MUTED, GRID, ACCENT = '#EC6A5A', '#86AEDB', '#232322', '#F0F1EF', '#D7D1CA', '#8f9191', '#232322', '#D7D1CA'
PAGE, CARD, RAISED, BORDER, WARN = '#000000', '#0d0d0c', '#1a1a19', '#2a2a29', '#E3B94F'
FONT = "Poppins, 'Helvetica Neue', Arial, sans-serif"
FONTS_CSS = 'https://fonts.googleapis.com/css2?family=Poppins:wght@200;300;400;500;600;700;900&display=swap'

# nav shared by the two preview pages, so each links back to the dashboard and to the other
def nav(here):
    links = [('Dashboard', '../index.html'), ('Email digest', 'email-preview.html'), ('Teams card', 'teams-preview.html')]
    return '<nav class="nav"><img src="../aldar-logo.svg" alt="Aldar">' + ''.join(
        f'<a href="{h}"{" aria-current=page" if l == here else ""}>{l}</a>' for l, h in links) + '</nav>'

NAV_CSS = ('.nav{max-width:820px;margin:0 auto;padding:16px 16px 0;display:flex;gap:8px;align-items:center;flex-wrap:wrap}'
           '.nav img{height:30px;filter:invert(1);margin-right:8px}'
           '.nav a{color:#D7D1CA;text-decoration:none;border:1px solid #2a2a29;border-radius:999px;padding:4px 14px;font-size:13px}'
           '.nav a:hover{border-color:#D7D1CA}.nav a[aria-current]{background:#F0F1EF;color:#000;border-color:#F0F1EF;font-weight:600}')

def cell(v, full=10):
    p = min(1, abs(v) / full)
    if v == 0:
        return MID, INK
    p = max(.18, p)
    return mix(UP if v > 0 else DOWN, MID, p), ('#ffffff' if p >= .55 else INK)

page = D['page_url']
n_alerts = len(D['alerts'])
subject = f"Macro Signals {D['date_short']}: 3M EIBOR {bp(D['headline_bp'])}bp expected, {n_alerts} alerts"
preheader = f"{n_alerts} alerts, {len(D['actions'])} suggested actions. Aldar credit spread expected {fix_minus(D['kpis'][1]['value'])}."

# ---------------------------------------------------------------- email
def h2(text):
    return f'''<tr><td style="padding:24px 28px 8px 28px;font-family:{FONT};font-size:13px;color:{INK2};font-weight:600;">{text}</td></tr>'''

def tenor_line(move):
    parts = [f'<span style="white-space:nowrap;">{t}&nbsp;<b>{bp(v)}</b></span>' for t, v in zip(D['tenors'], move) if v != 0]
    return ' &nbsp;·&nbsp; '.join(parts)

def alert_block(a, first):
    border = '' if first else f'border-top:1px solid {GRID};'
    if 'move' in a:
        effect = f'<span style="color:{MUTED};">Expected move, bp:</span> {tenor_line(a["move"])}'
    else:
        effect = f'<span style="color:{MUTED};">Aldar credit spread:</span> <b>{bp(a["spread"])}bp</b> over 5 days'
    return f'''<tr><td style="padding:0 28px;"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="{border}">
  <tr><td style="padding:14px 0 0 0;font-family:{FONT};font-size:12px;color:{MUTED};">
    <span style="border:1px solid {UP};color:{UP};font-weight:600;font-size:11px;padding:1px 8px;border-radius:999px;">Alert {a["score"]}</span>
    &nbsp;<b style="color:{INK2};">{e(a["driver"])}</b> &nbsp;{e(a["time"])} GST</td></tr>
  <tr><td style="padding:6px 0 0 0;font-family:{FONT};font-size:15px;line-height:21px;font-weight:600;"><a href="{e(a["url"])}" style="color:{INK};text-decoration:none;">{e(a["title"])}</a></td></tr>
  <tr><td style="padding:6px 0 0 0;font-family:{FONT};font-size:14px;line-height:20px;color:{INK};font-weight:300;"><b style="font-weight:600;">For Aldar:</b> {e(a["impl"])}</td></tr>
  <tr><td style="padding:6px 0 0 0;font-family:{FONT};font-size:13px;line-height:19px;color:{INK};">{effect}</td></tr>
  <tr><td style="padding:6px 0 14px 0;font-family:{FONT};font-size:12.5px;line-height:18px;color:{INK2};font-weight:300;"><b style="font-weight:600;">Why it scored {a["score"]}:</b> {e(a["why"])} <a href="{e(a["url"])}" style="color:{ACCENT};text-decoration:underline;">Source: {e(a["cite"])}</a></td></tr>
</table></td></tr>'''

def curve_table():
    head = ''.join(f'<td align="center" style="font-family:{FONT};font-size:11px;color:{MUTED};padding:0 0 4px 0;">{t}</td>' for t in D['tenors'])
    plat = ''
    for v in D['curve_platform']:
        bg, fg = cell(v)
        plat += f'<td align="center" style="font-family:{FONT};font-size:13px;font-weight:600;background:{bg};color:{fg};padding:6px 0;border:2px solid {CARD};border-radius:6px;">{bp(v)}</td>'
    pri = ''.join(f'<td align="center" style="font-family:{FONT};font-size:12px;color:{INK2};padding:5px 0;">{bp(v)}</td>' for v in D['curve_priced'])
    gap = ''.join(f'<td align="center" style="font-family:{FONT};font-size:12px;font-weight:700;color:{INK};padding:5px 0;border-top:1px solid {GRID};">{bp(a - b)}</td>' for a, b in zip(D['curve_platform'], D['curve_priced']))
    lab = lambda t, extra='': f'<td style="font-family:{FONT};font-size:12px;color:{INK2};padding:5px 8px 5px 0;white-space:nowrap;{extra}">{t}</td>'
    return f'''<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="table-layout:fixed;">
  <tr><td width="92"></td>{head}</tr>
  <tr>{lab("Platform view")}{plat}</tr>
  <tr>{lab("Priced in")}{pri}</tr>
  <tr>{lab("Not yet priced", f"border-top:1px solid {GRID};font-weight:700;color:{INK};")}{gap}</tr>
</table>'''

def kpi_row():
    # 2 x 2 grid so it stays readable on a phone and in Outlook
    def td(k, left, top):
        bl = f'border-left:1px solid {GRID};' if left else ''
        bt = f'border-top:1px solid {GRID};' if top else ''
        return f'''<td width="50%" valign="top" style="padding:10px 14px;{bl}{bt}font-family:{FONT};">
      <div style="font-size:12px;color:{INK2};line-height:16px;">{e(k["label"])}</div>
      <div style="font-size:21px;font-weight:300;color:{INK};line-height:28px;">{e(fix_minus(k["value"]))}</div>
      <div style="font-size:11.5px;color:{MUTED};line-height:15px;">{e(k["note"])}</div></td>'''
    k = D['kpis']
    rows = f'<tr>{td(k[0], False, False)}{td(k[1], True, False)}</tr><tr>{td(k[2], False, True)}{td(k[3], True, True)}</tr>'
    return f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="border:1px solid {BORDER};border-radius:12px;border-collapse:separate;">{rows}</table>'

def action_rows():
    out = ''
    for i, a in enumerate(D['actions']):
        border = '' if i == 0 else f'border-top:1px solid {GRID};'
        out += f'''<tr><td style="padding:0 28px;"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="{border}"><tr><td style="padding:12px 0;font-family:{FONT};">
      <div style="font-size:12px;color:{INK2};font-weight:600;">{e(a["type"])}</div>
      <div style="font-size:14px;line-height:20px;font-weight:600;color:{INK};padding-top:3px;">{e(a["title"])}</div>
      <div style="font-size:12.5px;line-height:18px;color:{INK2};font-weight:300;padding-top:3px;"><b style="color:{INK};font-weight:600;">{e(a["impact"])}</b> &nbsp;·&nbsp; From: {e(a["from"])}</div>
    </td></tr></table></td></tr>'''
    return out

def other_rows():
    out = ''
    for o in D['others']:
        out += f'''<tr><td style="padding:5px 0;font-family:{FONT};font-size:13px;line-height:18px;color:{INK};border-top:1px solid {GRID};">
      <span style="color:{MUTED};font-size:12px;">{o["score"]} · {e(o["driver"])}</span><br><a href="{e(o["url"])}" style="color:{INK};text-decoration:none;">{e(o["title"])}</a></td></tr>'''
    return f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">{out}</table>'

def market_table():
    rows = ''
    m = D['market']
    for i in range(0, len(m), 2):
        tds = ''
        for r in m[i:i + 2]:
            tds += f'''<td width="50%" style="padding:6px 0;border-top:1px solid {GRID};font-family:{FONT};font-size:13px;">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
          <td style="font-family:{FONT};font-size:13px;color:{INK2};">{e(r["name"])}</td>
          <td align="right" style="font-family:{FONT};font-size:13px;font-weight:600;color:{INK};">{e(r["value"])}</td>
          <td align="right" width="56" style="font-family:{FONT};font-size:12px;color:{MUTED};padding-right:14px;">{e(fix_minus(r["chg"]))}</td></tr></table></td>'''
        rows += f'<tr>{tds}</tr>'
    return f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">{rows}</table>'

def button(label, href, primary=True):
    bg, fg, bd = (INK, '#000000', INK) if primary else (CARD, INK, MUTED)
    return f'''<td style="border-radius:999px;background:{bg};border:1px solid {bd};"><a href="{e(href)}" style="display:inline-block;padding:10px 20px;font-family:{FONT};font-size:14px;font-weight:500;color:{fg};text-decoration:none;">{label}</a></td>'''

email = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="dark"><meta name="supported-color-schemes" content="dark">
<link href="{FONTS_CSS}" rel="stylesheet">
<title>{e(subject)}</title></head>
<body style="margin:0;padding:0;background:{PAGE};">
<div style="display:none;max-height:0;overflow:hidden;mso-hide:all;">{e(preheader)}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="{PAGE}" style="background:{PAGE};"><tr><td align="center" style="padding:24px 12px;">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" bgcolor="{CARD}" style="width:100%;max-width:600px;background:{CARD};border:1px solid {BORDER};border-radius:16px;border-collapse:separate;">

  <tr><td style="padding:22px 28px 18px 28px;border-bottom:1px solid {BORDER};">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
      <td width="52" valign="middle"><img src="{page}aldar-logo-white.png" width="40" height="40" alt="Aldar" style="display:block;border:0;"></td>
      <td style="font-family:{FONT};padding-left:12px;border-left:1px solid {MUTED};"><div style="font-size:11px;font-weight:300;color:{MUTED};">Group Treasury</div>
        <div style="padding-top:4px;"><span style="display:inline-block;font-size:17px;font-weight:900;color:{INK};border:1.5px solid {INK};border-radius:8px;padding:4px 9px 3px;">Macro Signals</span></div></td>
      <td align="right" style="font-family:{FONT};font-size:12px;font-weight:300;color:{MUTED};line-height:17px;"><b style="color:{INK};font-size:13px;font-weight:600;">{e(D["date_long"])}</b><br>Generated {e(D["generated"])}</td>
    </tr></table></td></tr>
  <tr><td style="padding:8px 28px;background:{RAISED};font-family:{FONT};font-size:11.5px;font-weight:300;color:{WARN};line-height:16px;">Prototype with synthetic data, for design review only. Not investment advice.</td></tr>

  <tr><td style="padding:22px 28px 0 28px;font-family:{FONT};">
    <div style="font-size:13px;color:{INK2};font-weight:600;">Today's read</div>
    <div style="padding-top:6px;"><span style="font-size:60px;line-height:64px;font-weight:200;letter-spacing:-2px;color:{INK};">{bp(D["headline_bp"])}</span><span style="font-size:16px;font-weight:900;color:{INK};"> bp</span></div>
    <div style="font-size:12.5px;font-weight:300;color:{MUTED};">{e(D["headline_cap"])}</div>
    <div style="font-size:14.5px;line-height:23px;font-weight:300;color:{INK};padding-top:12px;margin-top:12px;border-top:1px solid {BORDER};">{e(D["read"])}</div>
  </td></tr>
  <tr><td style="padding:16px 28px 0 28px;">{kpi_row()}</td></tr>

  {h2("Expected move across the curve, next 5 trading days, bp")}
  <tr><td style="padding:2px 28px 0 28px;">{curve_table()}</td></tr>

  {h2(f"Alerts · {n_alerts} of {D['kept']} items scored {D['alert_threshold']} or more")}
  {''.join(alert_block(a, i == 0) for i, a in enumerate(D['alerts']))}

  {h2("Suggested actions · for review by FRM and Head of Treasury")}
  {action_rows()}

  {h2(f"Below the alert threshold · {len(D['others'])} items")}
  <tr><td style="padding:2px 28px 0 28px;">{other_rows()}</td></tr>

  {h2("Market close, 30 Sep · change on the day")}
  <tr><td style="padding:2px 28px 0 28px;">{market_table()}</td></tr>

  <tr><td style="padding:26px 28px 6px 28px;">
    <table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>
      {button("Open the full digest", page + "#today")}<td width="10"></td>{button("Report something we missed", page + "#missed", False)}
    </tr></table></td></tr>
  <tr><td style="padding:8px 28px 24px 28px;font-family:{FONT};font-size:12.5px;line-height:18px;font-weight:300;color:{INK2};">Rate each item as useful or not useful on the page. Ratings tune tomorrow's scoring, and a missed move counts for more than a false alarm.</td></tr>

  <tr><td style="padding:16px 28px 20px 28px;border-top:1px solid {BORDER};font-family:{FONT};font-size:11.5px;line-height:17px;font-weight:300;color:{MUTED};">
    {D["scanned"]} items scanned from {e(D["window"])} GST, {D["kept"]} kept after the market check. Sent to the Financial Risk Manager and Head of Treasury. Prototype by an NYU Stern team for Aldar Group Treasury.</td></tr>
</table>
</td></tr></table>
</body></html>
'''

# email preview: inbox-style header above the same body, rendered in an iframe so its styles stay isolated
preview = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Email digest preview</title>
<link href="{FONTS_CSS}" rel="stylesheet">
<style>
body{{margin:0;background:#000;font:14px/1.5 Poppins,'Helvetica Neue',Arial,sans-serif;color:#F0F1EF}}
{NAV_CSS}
.note{{max-width:820px;margin:14px auto 0;padding:0 16px;font-size:12.5px;font-weight:300;color:#8f9191}}
.note b{{color:#D7D1CA;font-weight:600}}
.win{{max-width:820px;margin:12px auto 32px;background:#0d0d0c;border:1px solid #2a2a29;border-radius:16px;overflow:hidden}}
.env{{padding:16px 20px;border-bottom:1px solid #2a2a29}}
.subj{{font-size:18px;font-weight:600;margin-bottom:10px}}
.row{{display:flex;gap:12px;align-items:center}}
.av{{width:36px;height:36px;border-radius:50%;background:#D7D1CA;color:#000;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:13px;flex:none}}
.who b{{font-weight:600}} .who div{{font-size:12.5px;font-weight:300;color:#8f9191}}
.time{{margin-left:auto;font-size:12.5px;font-weight:300;color:#8f9191;white-space:nowrap}}
iframe{{display:block;width:100%;border:0;height:2400px}}
</style></head><body>
{nav('Email digest')}
<div class="note"><b>Mock email digest.</b> Same synthetic data as the page. The frame below is the actual email body (email.html), built with tables and inline styles so it renders in Outlook.</div>
<div class="win">
  <div class="env">
    <div class="subj">{e(subject)}</div>
    <div class="row"><div class="av">MS</div>
      <div class="who"><b>Macro Signals (prototype)</b><div>To: Financial Risk Manager; Head of Treasury</div></div>
      <div class="time">{e(D["date_short"])}, 06:31</div></div>
  </div>
  <iframe id="body" title="Email body" srcdoc="{e(email)}"></iframe>
</div>
<script>
const f=document.getElementById('body');
f.addEventListener('load',()=>{{try{{f.style.height=f.contentDocument.documentElement.scrollHeight+'px'}}catch(e){{}}}});
</script>
</body></html>
'''

# ---------------------------------------------------------------- Teams adaptive card
def tb(text, **kw):
    d = {'type': 'TextBlock', 'text': text, 'wrap': True}
    d.update(kw)
    return d

def alert_container(a, idx):
    effect = ('Expected move, bp: ' + ' · '.join(f'{t} {bp(v)}' for t, v in zip(D['tenors'], a['move']) if v != 0)) if 'move' in a \
        else f'Aldar credit spread: {bp(a["spread"])}bp over 5 days'
    return {
        'type': 'Container', 'separator': idx > 0, 'spacing': 'Medium',
        'items': [
            {'type': 'ColumnSet', 'columns': [
                {'type': 'Column', 'width': 'auto', 'verticalContentAlignment': 'Top', 'items': [
                    {'type': 'Container', 'style': 'attention', 'bleed': False, 'items': [
                        tb(str(a['score']), weight='Bolder', size='Medium', horizontalAlignment='Center', color='Attention', spacing='None')]}]},
                {'type': 'Column', 'width': 'stretch', 'items': [
                    tb(f'{a["driver"]} · {a["time"]} GST', size='Small', isSubtle=True, spacing='None'),
                    tb(f'[{a["title"]}]({a["url"]})', weight='Bolder', spacing='Small'),
                    tb(f'**For Aldar:** {a["impl"]}', spacing='Small'),
                    tb(effect, size='Small', isSubtle=True, spacing='Small'),
                ]}]},
            {'type': 'Container', 'id': f'why{idx}', 'isVisible': False, 'items': [
                tb(f'**Why it scored {a["score"]}:** {a["why"]}', size='Small'),
                tb(f'Source: [{a["cite"]}]({a["url"]})', size='Small', isSubtle=True, spacing='Small')]},
            {'type': 'ActionSet', 'spacing': 'Small', 'actions': [
                {'type': 'Action.ToggleVisibility', 'title': f'Why it scored {a["score"]}', 'targetElements': [f'why{idx}']}]},
        ]}

card = {
    '$schema': 'http://adaptivecards.io/schemas/adaptive-card.json',
    'type': 'AdaptiveCard', 'version': '1.5', 'msteams': {'width': 'Full'},
    'body': [
        {'type': 'ColumnSet', 'columns': [
            {'type': 'Column', 'width': 'auto', 'verticalContentAlignment': 'Center', 'items': [
                {'type': 'Image', 'url': page + 'aldar-logo-white.png', 'altText': 'Aldar', 'width': '36px'}]},
            {'type': 'Column', 'width': 'stretch', 'items': [
                tb('Group Treasury', size='Small', isSubtle=True, spacing='None'),
                tb(f'Macro Signals · {D["date_short"]}', size='Large', weight='Bolder', spacing='None')]},
            {'type': 'Column', 'width': 'auto', 'verticalContentAlignment': 'Bottom', 'items': [
                tb('Synthetic data', size='Small', color='Warning', horizontalAlignment='Right')]}]},
        {'type': 'Container', 'style': 'emphasis', 'bleed': True, 'spacing': 'Medium', 'items': [
            {'type': 'ColumnSet', 'columns': [
                {'type': 'Column', 'width': 'auto', 'verticalContentAlignment': 'Center', 'items': [
                    tb(f'{bp(D["headline_bp"])}bp', size='ExtraLarge', weight='Bolder', spacing='None'),
                    tb('3M EIBOR, next 5 days', size='Small', isSubtle=True, spacing='None', wrap=False)]},
                {'type': 'Column', 'width': 'stretch', 'verticalContentAlignment': 'Center', 'items': [
                    tb(D['read_short'])]}]}]},
        {'type': 'FactSet', 'spacing': 'Medium', 'facts': [
            {'title': k['label'], 'value': f'{fix_minus(k["value"])} · {k["note"]}'} for k in D['kpis'] if k['label'] != 'Alerts']},
        tb(f'**Alerts** · {n_alerts} of {D["kept"]} items scored {D["alert_threshold"]} or more', spacing='Large', separator=True),
        *[alert_container(a, i) for i, a in enumerate(D['alerts'])],
        tb('**Suggested actions** · for review by FRM and Head of Treasury', spacing='Large', separator=True),
        *[{'type': 'Container', 'spacing': 'Small', 'items': [
            tb(f'**{a["type"]}:** {a["title"]}', spacing='None'),
            tb(f'{a["impact"]} · From: {a["from"]}', size='Small', isSubtle=True, spacing='None')]} for a in D['actions']],
        {'type': 'Container', 'id': 'others', 'isVisible': False, 'spacing': 'Medium', 'separator': True, 'items': [
            tb(f'**Below the alert threshold**', spacing='None'),
            *[tb(f'{o["score"]} · {o["driver"]} · [{o["title"]}]({o["url"]})', size='Small', spacing='Small') for o in D['others']]]},
    ],
    'actions': [
        {'type': 'Action.OpenUrl', 'title': 'Open full digest', 'url': page + '#today'},
        {'type': 'Action.ToggleVisibility', 'title': f'Show {len(D["others"])} lower items', 'targetElements': ['others']},
        {'type': 'Action.OpenUrl', 'title': 'Report a miss', 'url': page + '#missed'},
    ],
}

card_json = json.dumps(card, indent=2, ensure_ascii=False)

# Teams preview: real Adaptive Cards renderer with a dark host config matching the dashboard
renderer = open(os.path.join(HERE, 'adaptivecards.min.js'), encoding='utf-8').read() if os.path.exists(os.path.join(HERE, 'adaptivecards.min.js')) else None
host_config = {
    'fontFamily': FONT,
    'spacing': {'small': 4, 'default': 8, 'medium': 14, 'large': 20, 'extraLarge': 28, 'padding': 16},
    'separator': {'lineThickness': 1, 'lineColor': GRID},
    'fontSizes': {'small': 12, 'default': 14, 'medium': 16, 'large': 18, 'extraLarge': 30},
    'fontWeights': {'lighter': 200, 'default': 300, 'bolder': 600},
    'containerStyles': {
        'default': {'backgroundColor': CARD, 'foregroundColors': {
            'default': {'default': INK, 'subtle': MUTED}, 'accent': {'default': ACCENT, 'subtle': ACCENT},
            'attention': {'default': UP, 'subtle': UP}, 'warning': {'default': WARN, 'subtle': WARN},
            'good': {'default': '#7CC79A', 'subtle': '#7CC79A'}, 'dark': {'default': INK, 'subtle': MUTED}, 'light': {'default': '#FFFFFF', 'subtle': '#FFFFFF'}}},
        'emphasis': {'backgroundColor': RAISED, 'foregroundColors': {'default': {'default': INK, 'subtle': MUTED}}},
        'attention': {'backgroundColor': '#2a1614', 'foregroundColors': {'attention': {'default': UP, 'subtle': UP}, 'default': {'default': INK, 'subtle': MUTED}}},
    },
    'actions': {'maxActions': 6, 'spacing': 'default', 'buttonSpacing': 8, 'showCard': {'actionMode': 'inline'}, 'actionsOrientation': 'horizontal', 'actionAlignment': 'left'},
    'factSet': {'title': {'weight': 'bolder', 'size': 'default', 'wrap': True, 'maxWidth': 200}, 'value': {'wrap': True}, 'spacing': 10},
    'supportsInteractivity': True,
}

teams_preview = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Teams digest preview</title>
<link href="{FONTS_CSS}" rel="stylesheet">
<style>
body{{margin:0;background:#000;font:14px/1.5 Poppins,'Helvetica Neue',Arial,sans-serif;color:#F0F1EF}}
{NAV_CSS}
.note{{max-width:820px;margin:14px auto 0;padding:0 16px;font-size:12.5px;font-weight:300;color:#8f9191}}
.note b{{color:#D7D1CA;font-weight:600}}
.chan{{max-width:820px;margin:12px auto 32px;background:#0d0d0c;border:1px solid #2a2a29;border-radius:16px;overflow:hidden}}
.chan-h{{padding:12px 18px;border-bottom:1px solid #2a2a29;font-weight:600;display:flex;gap:10px;align-items:center}}
.chan-h span{{font-weight:300;color:#8f9191;font-size:12.5px}}
.post{{padding:16px 18px 20px;display:flex;gap:12px;background:#0d0d0c}}
.av{{width:32px;height:32px;border-radius:50%;background:#D7D1CA;color:#000;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:12px;flex:none}}
.msg{{flex:1;min-width:0}}
.by{{font-size:12.5px;font-weight:300;color:#8f9191;margin-bottom:6px}} .by b{{color:#F0F1EF;font-weight:600;margin-right:6px}}
.tag{{display:inline-block;font-size:10.5px;border:1px solid #2a2a29;border-radius:999px;padding:0 7px;margin-right:6px;color:#8f9191}}
#card{{background:#0d0d0c;border:1px solid #2a2a29;border-radius:14px;overflow:hidden}}
#card .ac-pushButton{{border:1px solid #2a2a29 !important;background:transparent !important;color:#F0F1EF !important;border-radius:999px !important;font-family:Poppins,Arial,sans-serif !important;font-weight:400 !important;padding:6px 14px !important;font-size:13px !important;min-height:32px}}
#card .ac-pushButton:hover{{border-color:#D7D1CA !important}}
#card a{{color:#D7D1CA}}
#card .ac-actionSet{{flex-wrap:wrap;row-gap:8px}}
.fallback{{padding:16px;color:#EC6A5A}}
@media (max-width:520px){{.post{{padding:12px}}.av{{display:none}}}}
</style></head><body>
{nav('Teams card')}
<div class="note"><b>Mock Teams digest.</b> This is the Adaptive Card in teams-card.json, drawn with the official Adaptive Cards renderer in the dashboard's dark theme. In Teams itself the card follows each person's Teams theme and font. The "Why it scored" and "Show lower items" buttons work here and in Teams.</div>
<div class="chan">
  <div class="chan-h">Treasury <span>· Macro Signals channel</span></div>
  <div class="post"><div class="av">MS</div><div class="msg">
    <div class="by"><b>Macro Signals (prototype)</b><span class="tag">App</span>{e(D["date_short"])} 06:31</div>
    <div id="card"><div class="fallback">Card renderer did not load.</div></div>
  </div></div>
</div>
{('<script>' + renderer + '</script>') if renderer else '<script src="https://cdn.jsdelivr.net/npm/adaptivecards@3.0.6/dist/adaptivecards.min.js"></script>'}
<script>
const CARD = {card_json};
const HOST = {json.dumps(host_config)};
try {{
  const ac = new AdaptiveCards.AdaptiveCard();
  ac.hostConfig = new AdaptiveCards.HostConfig(HOST);
  AdaptiveCards.AdaptiveCard.onProcessMarkdown = (text, result) => {{
    const esc = s => s.replace(/[&<>]/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;'}}[c]));
    result.outputHtml = esc(text).replace(/\\*\\*(.+?)\\*\\*/g, '<b>$1</b>').replace(/\\[([^\\]]+)\\]\\((https?:[^)]+)\\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
    result.didProcess = true;
  }};
  ac.onExecuteAction = a => {{ if (a instanceof AdaptiveCards.OpenUrlAction) window.open(a.url, '_blank', 'noopener'); }};
  ac.parse(CARD);
  const el = ac.render();
  const host = document.getElementById('card'); host.innerHTML = ''; host.appendChild(el);
}} catch (err) {{ document.querySelector('.fallback').textContent = 'Card renderer error: ' + err.message; }}
</script>
</body></html>
'''

out = sys.argv[1] if len(sys.argv) > 1 else HERE
os.makedirs(out, exist_ok=True)
for name, body in [('email.html', email), ('email-preview.html', preview), ('teams-card.json', card_json), ('teams-preview.html', teams_preview)]:
    open(os.path.join(out, name), 'w', encoding='utf-8').write(body)
print('subject:', subject)
print('renderer inlined:', bool(renderer))
