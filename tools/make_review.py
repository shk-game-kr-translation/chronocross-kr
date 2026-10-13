"""Review page: one self-contained HTML with every translated row next to its English and Japanese source.

  make_review.py <version>     -> 40_release/CCRDE_KR_v<version>_review.html

Reads the original text from 00_original (lang.dat) and 10_extracted/rd/translate.txt, so the page contains game
text and must NOT be published in the repository (40_release/ is git-ignored). Open it in any browser: sheet list on
the left, search across all sheets (Korean / English / Japanese / key) at the top.
"""
import html
import json
import sys

import cctext
import export_cc
import rdtext
from paths import EXTRACTED, RELEASE, TRANS_CC, TRANS_RD


def cc_sheets():
    z = export_cc.lang()
    msg = {k: (jp, en) for k, jp, en in export_cc.msg_rows(z)}
    btel = {k: (jp, en) for k, jp, en in export_cc.btel_rows(z)}
    tables = {}
    for name in export_cc.TABLES:
        tables["tbl_" + name.split(".")[0]] = {n: (jp, en) for n, _, jp, en in export_cc.table_rows(z, name)}
    out = []
    for p in sorted(TRANS_CC.glob("*.json")):
        src = msg if p.stem.startswith("msg_") else btel if p.stem == "btel" else tables[p.stem]
        rows = []
        for r in json.loads(p.read_text(encoding="utf-8")):
            jp, en = src[r["k"]]
            if p.stem.startswith("msg_") or p.stem == "btel":  # literal \n in dialogue
                jp, en = jp.replace("\\n", "\n"), en.replace("\\n", "\n")
                ko = r["ko"].replace("\\n", "\n")
            else:
                ko = r["ko"]
            rows.append([r["k"], ko, en, jp])
        out.append(["크로노 크로스 " + p.stem, rows])
    return out


def rd_sheets():
    src = rdtext.parse((EXTRACTED / "rd" / "translate.txt").read_bytes())["rows"]
    out = []
    for p in sorted(TRANS_RD.glob("*.json")):
        rows = []
        for r in json.loads(p.read_text(encoding="utf-8")):
            t = src[r["i"]]["text"]
            if not (r["ko"] or t["EN"].strip()):
                continue
            rows.append([r["addr"], r["ko"], t["EN"], t["JP"]])
        out.append(["래디컬 드리머즈 " + p.stem, rows])
    return out


PAGE = """<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>크로노 크로스 한글 패치 검수 v%(ver)s</title>
<style>
:root{--bg:#fbfaf7;--fg:#1d1d1f;--mut:#6b6b70;--line:#e3e1db;--side:#f1efe9;--hl:#fff1a8;--tag:#2f6fb0;--ko:#111}
@media (prefers-color-scheme:dark){:root{--bg:#18181a;--fg:#e6e6e6;--mut:#9a9aa0;--line:#333;--side:#202023;--hl:#5a4b00;--tag:#7fb2e8;--ko:#fff}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.55 "Malgun Gothic","Apple SD Gothic Neo",sans-serif}
header{position:sticky;top:0;z-index:2;display:flex;gap:12px;align-items:center;padding:10px 16px;background:var(--bg);border-bottom:1px solid var(--line)}
header h1{font-size:15px;margin:0;white-space:nowrap}header input{flex:1;min-width:0;padding:7px 10px;border:1px solid var(--line);border-radius:6px;background:var(--bg);color:var(--fg);font:inherit}
#count{color:var(--mut);white-space:nowrap}
main{display:flex}nav{width:230px;flex:none;height:calc(100vh - 51px);overflow:auto;position:sticky;top:51px;background:var(--side);border-right:1px solid var(--line)}
nav a{display:block;padding:4px 12px;color:var(--fg);text-decoration:none;font-size:13px}nav a:hover{background:var(--line)}nav a.on{background:var(--tag);color:#fff}
nav a span{float:right;color:var(--mut)}nav a.on span{color:#fff}
section{flex:1;min-width:0;padding:0 16px 40px}
table{width:100%%;border-collapse:collapse;table-layout:fixed}th,td{border-bottom:1px solid var(--line);padding:6px 8px;vertical-align:top;text-align:left;white-space:pre-wrap;word-break:break-word}
th{position:sticky;top:51px;background:var(--bg);color:var(--mut);font-weight:600}
td.k{width:110px;color:var(--mut);font:12px monospace}td.ko{color:var(--ko)}td.en,td.jp{color:var(--mut)}
th.k{width:110px}.t{color:var(--tag);font-size:12px}mark{background:var(--hl);color:inherit}
.sh{margin:18px 0 4px;font-weight:700}
@media (max-width:760px){nav{display:none}td.k,th.k{width:64px}}
</style></head><body>
<header><h1>한글 패치 검수 v%(ver)s</h1><input id="q" placeholder="검색: 한국어 / 영어 / 일본어 / 키 (2글자 이상)"><span id="count"></span></header>
<main><nav id="nav"></nav><section id="out"></section></main>
<script>
const DATA=%(data)s;
const nav=document.getElementById('nav'),out=document.getElementById('out'),q=document.getElementById('q'),cnt=document.getElementById('count');
function esc(s){return s.replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]))}
function fmt(s,re){let h=esc(s);if(re)h=h.replace(re,m=>'<mark>'+m+'</mark>');return h.replace(/\\{[^{}]*\\}/g,m=>'<span class="t">'+m+'</span>').replace(/\\[NAME\\]/g,m=>'<span class="t">'+m+'</span>')}
function table(rows,re){return '<table><tr><th class="k">키</th><th>한국어</th><th>English</th><th>日本語</th></tr>'+rows.map(r=>'<tr><td class="k">'+esc(r[0])+'</td><td class="ko">'+fmt(r[1],re)+'</td><td class="en">'+fmt(r[2],re)+'</td><td class="jp">'+fmt(r[3],re)+'</td></tr>').join('')+'</table>'}
let cur=0;
function show(i){cur=i;q.value='';[...nav.children].forEach((a,j)=>a.classList.toggle('on',j===i));out.innerHTML='<div class="sh">'+esc(DATA[i][0])+'</div>'+table(DATA[i][1]);cnt.textContent=DATA[i][1].length+'행';scrollTo(0,0)}
DATA.forEach((s,i)=>{const a=document.createElement('a');a.href='#';a.innerHTML=esc(s[0])+'<span>'+s[1].length+'</span>';a.onclick=e=>{e.preventDefault();show(i)};nav.appendChild(a)});
let timer;q.oninput=()=>{clearTimeout(timer);timer=setTimeout(search,250)};
function search(){const v=q.value.trim();if(v.length<2){show(cur);return}
 const re=new RegExp(v.replace(/[.*+?^${}()|[\\]\\\\]/g,'\\\\$&'),'gi');let html='',n=0;
 for(const [name,rows] of DATA){const hit=rows.filter(r=>r.some(c=>{re.lastIndex=0;return re.test(c)}));if(hit.length){n+=hit.length;if(n<=3000)html+='<div class="sh">'+esc(name)+' ('+hit.length+')</div>'+table(hit,re)}}
 out.innerHTML=html||'<p>결과 없음</p>';cnt.textContent=n+'건'+(n>3000?' (앞 3000건만 표시)':'');[...nav.children].forEach(a=>a.classList.remove('on'))}
show(0);
</script></body></html>
"""


def main():
    ver = sys.argv[1]
    data = cc_sheets() + rd_sheets()
    js = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    RELEASE.mkdir(exist_ok=True)
    out = RELEASE / f"CCRDE_KR_v{ver}_review.html"
    out.write_text(PAGE % {"ver": html.escape(ver), "data": js}, encoding="utf-8")
    print(f"{out} {out.stat().st_size} bytes, {sum(len(s[1]) for s in data)} rows in {len(data)} sheets")


if __name__ == "__main__":
    main()
