"""Review/edit page: one self-contained HTML with every translated row next to its Japanese and English source.

  make_review.py <version>     -> 40_release/CCRDE_KR_v<version>_review.html

Reads the original text from 00_original (lang.dat) and 10_extracted/rd/translate.txt, so the page contains game
text and must NOT be published in the repository (40_release/ is git-ignored). Open it in any browser: sheet list on
the left, search across all sheets (Korean / Japanese / English / key) at the top. Identical rows (same Korean,
English and Japanese) appear once, with all their keys.

The Korean column is editable. Edits are kept in the browser (localStorage) and can be exported as JSON
("JSON 내보내기") and loaded again ("JSON 불러오기"); tools/apply_review.py merges an export into the sheets.
"일괄 바꾸기" replaces a word in the Korean column (all sheets or the current one, never inside {tags}) with a
preview to pick rows from and one-step undo; the results are ordinary edits.
Export format: {"format": "ccrde-review", "ver": ..., "edits": {"cc:<sheet>" | "rd:<sheet>": {"<key>": "한국어"}}}
with real newlines in the text (apply_review.py restores the literal \\n of dialogue rows).
"""
import html
import json
import sys

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
        out.append(["cc:" + p.stem, "크로노 크로스 " + p.stem, rows])
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
        out.append(["rd:" + p.stem, "래디컬 드리머즈 " + p.stem, rows])
    return out


def dedupe(data):
    """-> [[title, [[label, ko, en, jp, [[sheet id, key], ...]], ...]], ...]. Rows whose Korean, English and Japanese
    are all identical are shown once (first occurrence); refs lists every place they occur, so an edit made on the
    page goes to all of them. The game data keeps every row."""
    first, refs = {}, {}
    for sid, _, rows in data:
        for r in rows:
            sig = (r[1], r[2], r[3])
            first.setdefault(sig, r)
            refs.setdefault(sig, []).append([sid, r[0]])
    out = []
    for sid, title, rows in data:
        kept = []
        for r in rows:
            sig = (r[1], r[2], r[3])
            if first[sig] is not r:
                continue
            rs = refs[sig]
            names = [k if s == sid else f"{s.split(':')[1]} {k}" for s, k in rs]
            label = names[0] if len(names) == 1 else ", ".join(names[:4]) + (
                f" 외 {len(names) - 4}곳" if len(names) > 4 else "")
            kept.append([label] + r[1:] + [rs])
        if kept:
            out.append([title, kept])
    return out


PAGE = """<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>크로노 크로스 한글 패치 검수 v%(ver)s</title>
<style>
:root{--bg:#fbfaf7;--fg:#1d1d1f;--mut:#6b6b70;--line:#e3e1db;--side:#f1efe9;--hl:#fff1a8;--tag:#2f6fb0;--ko:#111;--ed:#fff6e0;--edb:#d98a00;--in:#fff}
@media (prefers-color-scheme:dark){:root{--bg:#18181a;--fg:#e6e6e6;--mut:#9a9aa0;--line:#333;--side:#202023;--hl:#5a4b00;--tag:#7fb2e8;--ko:#fff;--ed:#3a2e10;--edb:#e0a030;--in:#222226}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.55 "Malgun Gothic","Apple SD Gothic Neo",sans-serif}
header{position:sticky;top:0;z-index:2;display:flex;gap:8px;align-items:center;padding:10px 16px;background:var(--bg);border-bottom:1px solid var(--line);flex-wrap:wrap}
header h1{font-size:15px;margin:0;white-space:nowrap}header input[type=search]{flex:1;min-width:160px;padding:7px 10px;border:1px solid var(--line);border-radius:6px;background:var(--in);color:var(--fg);font:inherit}
button,label.btn{padding:6px 10px;border:1px solid var(--line);border-radius:6px;background:var(--side);color:var(--fg);font:inherit;font-size:13px;cursor:pointer;white-space:nowrap}
button:hover,label.btn:hover{border-color:var(--tag)}#file{display:none}
#count,#edn{color:var(--mut);white-space:nowrap;font-size:13px}#edn b{color:var(--edb)}
#bulk{flex-basis:100%%;display:flex;gap:8px;align-items:center;flex-wrap:wrap;padding-top:6px;border-top:1px dashed var(--line)}#bulk[hidden]{display:none}
#bulk input[type=text]{width:180px;padding:6px 8px;border:1px solid var(--line);border-radius:6px;background:var(--in);color:var(--fg);font:inherit}
#bulk label{font-size:13px;white-space:nowrap}#bmsg{color:var(--mut);font-size:13px}
td.c,th.c{width:34px;text-align:center}td.c input{transform:scale(1.2)}ins{background:var(--hl);text-decoration:none}del{color:var(--mut)}
main{display:flex}nav{width:230px;flex:none;height:calc(100vh - var(--hh,51px));overflow:auto;position:sticky;top:var(--hh,51px);background:var(--side);border-right:1px solid var(--line)}
nav a{display:block;padding:4px 12px;color:var(--fg);text-decoration:none;font-size:13px}nav a:hover{background:var(--line)}nav a.on{background:var(--tag);color:#fff}
nav a span{float:right;color:var(--mut)}nav a.on span{color:#fff}nav a.edl{font-weight:700;border-bottom:1px solid var(--line)}
section{flex:1;min-width:0;padding:0 16px 40px}
table{width:100%%;border-collapse:collapse;table-layout:fixed}th,td{border-bottom:1px solid var(--line);padding:6px 8px;vertical-align:top;text-align:left;white-space:pre-wrap;word-break:break-word}
th{position:sticky;top:var(--hh,51px);background:var(--bg);color:var(--mut);font-weight:600;z-index:1}
td.k{width:120px;color:var(--mut);font:12px monospace}td.en{color:var(--mut)}td.jp{color:var(--fg)}
th.k{width:120px}.t{color:var(--tag);font-size:12px}mark{background:var(--hl);color:inherit}
td.ko{padding:3px 4px}textarea{display:block;width:100%%;resize:vertical;border:1px solid transparent;border-radius:4px;padding:3px 4px;background:transparent;color:var(--ko);font:inherit;line-height:1.55;overflow:hidden}
textarea:hover{border-color:var(--line)}textarea:focus{outline:none;border-color:var(--tag);background:var(--in)}
tr.ed td{background:var(--ed)}tr.ed textarea{border-left:3px solid var(--edb)}
.rv{display:block;font-size:11px;color:var(--edb);cursor:pointer;margin-top:2px}
.sh{margin:18px 0 4px;font-weight:700}
@media (max-width:760px){nav{display:none}td.k,th.k{width:64px}}
</style></head><body>
<header><h1>한글 패치 검수 v%(ver)s</h1><input type="search" id="q" placeholder="검색: 한국어 / 일본어 / 영어 / 키"><span id="count"></span>
<span id="edn"></span><button id="exp">JSON 내보내기</button><label class="btn" for="file">JSON 불러오기</label><input type="file" id="file" accept=".json,application/json"><button id="clr">수정 초기화</button><button id="bulkbtn">일괄 바꾸기</button>
<div id="bulk" hidden><input type="text" id="bf" placeholder="찾을 말 (한국어)"><span>→</span><input type="text" id="bt" placeholder="바꿀 말">
<label><input type="checkbox" id="bcur"> 현재 시트만</label><button id="bprev">미리보기</button><button id="bapply">선택한 행 바꾸기</button><button id="bundo" disabled>되돌리기</button><span id="bmsg">{태그} 안은 바꾸지 않습니다.</span></div></header>
<main><nav id="nav"></nav><section id="out"></section></main>
<script>
const VER=%(verjs)s,DATA=%(data)s,LS='ccrde_review_edits';
const nav=document.getElementById('nav'),out=document.getElementById('out'),q=document.getElementById('q'),cnt=document.getElementById('count'),edn=document.getElementById('edn');
// row id = "<sheet id>|<key>" of the row's first occurrence
const ROWS={},REF={};DATA.forEach(s=>s[1].forEach(r=>{const id=r[4][0][0]+'|'+r[4][0][1];r.id=id;ROWS[id]=r;r[4].forEach(f=>REF[f[0]+'|'+f[1]]=id)}));
let edits={};try{edits=JSON.parse(localStorage.getItem(LS)||'{}')||{}}catch(e){edits={}}
for(const id in edits)if(!ROWS[id]||edits[id]===ROWS[id][1])delete edits[id];  // edits already in this version drop out
function save(){try{localStorage.setItem(LS,JSON.stringify(edits))}catch(e){}const n=Object.keys(edits).length;edn.innerHTML=n?'수정 <b>'+n+'</b>행':'';navEd.querySelector('span').textContent=n}
function esc(s){return s.replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}
function fmt(s,re){let h=esc(s);if(re)h=h.replace(re,m=>'<mark>'+m+'</mark>');return h.replace(/\\{[^{}]*\\}/g,m=>'<span class="t">'+m+'</span>').replace(/\\[NAME\\]/g,m=>'<span class="t">'+m+'</span>')}
function ko(r){return r.id in edits?edits[r.id]:r[1]}
function lines(s){return s.split('\\n').length}
function tr(r,re){const v=ko(r),e=r.id in edits;return '<tr data-id="'+esc(r.id)+'"'+(e?' class="ed"':'')+'><td class="k">'+esc(r[0])+'</td><td class="jp">'+fmt(r[3],re)+'</td><td class="ko"><textarea rows="'+lines(v)+'" spellcheck="false">'+esc(v)+'</textarea>'+(e?'<span class="rv">원래대로</span>':'')+'</td><td class="en">'+fmt(r[2],re)+'</td></tr>'}
function table(rows,re){return '<table><tr><th class="k">키</th><th>日本語 (기준)</th><th>한국어 (편집)</th><th>English</th></tr>'+rows.map(r=>tr(r,re)).join('')+'</table>'}
function mark(row,r){const e=r.id in edits;row.classList.toggle('ed',e);const td=row.querySelector('td.ko');let b=td.querySelector('.rv');if(e&&!b){b=document.createElement('span');b.className='rv';b.textContent='원래대로';td.appendChild(b)}else if(!e&&b)b.remove()}
out.addEventListener('input',ev=>{const t=ev.target;if(t.tagName!=='TEXTAREA')return;const row=t.closest('tr'),r=ROWS[row.dataset.id];
 if(t.value===r[1])delete edits[r.id];else edits[r.id]=t.value;t.rows=lines(t.value);mark(row,r);save()});
out.addEventListener('click',ev=>{if(!ev.target.classList.contains('rv'))return;const row=ev.target.closest('tr'),r=ROWS[row.dataset.id];delete edits[r.id];const t=row.querySelector('textarea');t.value=r[1];t.rows=lines(r[1]);mark(row,r);save()});
let cur=0;
function setNav(i){[...nav.children].forEach((a,j)=>a.classList.toggle('on',j===i+2))}
function back(){cur<0?showAll():show(cur)}
// all rows: rendered in chunks of 400 as the page is scrolled down (cur = -1)
let allObs=null;
function showAll(){cur=-1;q.value='';setNav(-1);out.innerHTML='';let si=0,ri=0;const total=DATA.reduce((a,s)=>a+s[1].length,0);cnt.textContent=total+'행';
 const more=document.createElement('div');more.className='sh';more.textContent='불러오는 중…';
 function chunk(){let n=0,h='';while(si<DATA.length&&n<400){const rows=DATA[si][1].slice(ri,ri+400-n);if(ri===0)h+='<div class="sh">'+esc(DATA[si][0])+' ('+DATA[si][1].length+')</div>';h+=table(rows);n+=rows.length;ri+=rows.length;if(ri>=DATA[si][1].length){si++;ri=0}}
  more.insertAdjacentHTML('beforebegin',h);if(si>=DATA.length){more.remove();if(allObs)allObs.disconnect()}}
 out.appendChild(more);chunk();if(allObs)allObs.disconnect();
 allObs=new IntersectionObserver(es=>{if(es.some(e=>e.isIntersecting)&&cur<0&&more.isConnected){chunk();if(more.isConnected){allObs.unobserve(more);allObs.observe(more)}}},{rootMargin:'2000px'});allObs.observe(more);scrollTo(0,0)}
function show(i){if(allObs)allObs.disconnect();cur=i;q.value='';setNav(i);out.innerHTML='<div class="sh">'+esc(DATA[i][0])+'</div>'+table(DATA[i][1]);cnt.textContent=DATA[i][1].length+'행';scrollTo(0,0)}
function showEdited(){q.value='';[...nav.children].forEach((a,j)=>a.classList.toggle('on',j===0));let h='',n=0;
 for(const [name,rows] of DATA){const hit=rows.filter(r=>r.id in edits);if(hit.length){n+=hit.length;h+='<div class="sh">'+esc(name)+' ('+hit.length+')</div>'+table(hit)}}
 out.innerHTML=h||'<p>아직 수정한 행이 없습니다.</p>';cnt.textContent=n+'행';scrollTo(0,0)}
const navEd=document.createElement('a');navEd.href='#';navEd.className='edl';navEd.innerHTML='수정한 행<span>0</span>';navEd.onclick=e=>{e.preventDefault();showEdited()};nav.appendChild(navEd);
const navAll=document.createElement('a');navAll.href='#';navAll.className='edl';navAll.innerHTML='전체 행<span>'+DATA.reduce((a,s)=>a+s[1].length,0)+'</span>';navAll.onclick=e=>{e.preventDefault();showAll()};nav.appendChild(navAll);
DATA.forEach((s,i)=>{const a=document.createElement('a');a.href='#';a.innerHTML=esc(s[0])+'<span>'+s[1].length+'</span>';a.onclick=e=>{e.preventDefault();show(i)};nav.appendChild(a)});
let timer;q.oninput=()=>{clearTimeout(timer);timer=setTimeout(search,250)};
function search(){const v=q.value.trim();if(!v){const s=q.value;back();q.value=s;return}
 const re=new RegExp(v.replace(/[.*+?^${}()|[\\]\\\\]/g,'\\\\$&'),'gi');const hit1=s=>{re.lastIndex=0;return re.test(s)};let h='',n=0;
 for(const [name,rows] of DATA){const hit=rows.filter(r=>hit1(r[0])||hit1(ko(r))||hit1(r[2])||hit1(r[3]));if(hit.length){n+=hit.length;if(n<=2000)h+='<div class="sh">'+esc(name)+' ('+hit.length+')</div>'+table(hit,re)}}
 out.innerHTML=h||'<p>결과 없음</p>';cnt.textContent=n+'건'+(n>2000?' (앞 2000건만 표시)':'');[...nav.children].forEach(a=>a.classList.remove('on'))}
document.getElementById('exp').onclick=()=>{const ed={};let n=0;
 for(const id in edits){const r=ROWS[id];for(const [s,k] of r[4]){(ed[s]=ed[s]||{})[k]=edits[id];n++}}
 if(!n){alert('수정한 행이 없습니다.');return}
 const blob=new Blob([JSON.stringify({format:'ccrde-review',ver:VER,edits:ed},null,1)],{type:'application/json'});
 const d=new Date(),p=x=>String(x).padStart(2,'0');const a=document.createElement('a');a.href=URL.createObjectURL(blob);
 a.download='ccrde_review_edits_'+d.getFullYear()+p(d.getMonth()+1)+p(d.getDate())+'_'+p(d.getHours())+p(d.getMinutes())+'.json';document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(a.href),1000)};
document.getElementById('file').onchange=ev=>{const f=ev.target.files[0];if(!f)return;f.text().then(t=>{let j;try{j=JSON.parse(t)}catch(e){alert('JSON 형식이 아닙니다.');return}
 if(!j||j.format!=='ccrde-review'||!j.edits){alert('이 검수 페이지에서 내보낸 파일이 아닙니다.');return}
 let n=0,miss=0;for(const s in j.edits)for(const k in j.edits[s]){const id=REF[s+'|'+k];if(!id){miss++;continue}const r=ROWS[id],v=j.edits[s][k];if(v===r[1])delete edits[id];else edits[id]=v;n++}
 save();showEdited();alert(n+'개 항목을 불러왔습니다.'+(miss?' (이 버전에 없는 키 '+miss+'개는 건너뜀)':''))});ev.target.value=''};
document.getElementById('clr').onclick=()=>{const n=Object.keys(edits).length;if(!n)return;if(!confirm('수정한 '+n+'행을 모두 지울까요? (먼저 JSON으로 내보내 두는 것을 권장)'))return;edits={};save();back()};
// bulk replace: literal, case-sensitive, Korean column only (current text incl. edits), never inside {tags}
const hdr=document.querySelector('header'),bp=document.getElementById('bulk'),bf=document.getElementById('bf'),bt=document.getElementById('bt'),
 bcur=document.getElementById('bcur'),bmsg=document.getElementById('bmsg'),bundo=document.getElementById('bundo');
function hh(){document.documentElement.style.setProperty('--hh',hdr.offsetHeight+'px')}
addEventListener('resize',hh);
document.getElementById('bulkbtn').onclick=()=>{bp.hidden=!bp.hidden;hh();if(!bp.hidden)bf.focus()};
function repl(s,f,t){return s.split(/(\\{[^{}]*\\})/).map((p,i)=>(i&1)?p:p.split(f).join(t)).join('')}
function lit(s){return new RegExp(s.replace(/[.*+?^${}()|[\\]\\\\]/g,'\\\\$&'),'g')}
let bHits=[],bChk=[],bUndo=null;const BMAX=2000;
function bulkPreview(){const f=bf.value,t=bt.value;if(!f){bmsg.textContent='찾을 말을 입력하세요.';return}
 bHits=[];const src=bcur.checked&&cur>=0?[DATA[cur]]:DATA;
 for(const [name,rows] of src)for(const r of rows){const v=ko(r),nv=repl(v,f,t);if(nv!==v)bHits.push([r,nv,name])}
 bChk=bHits.map(()=>true);const rf=lit(esc(f)),rt=t?lit(esc(t)):null;
 const cell=(s,re,tg)=>{let h=esc(s);if(re)h=h.replace(re,m=>'<'+tg+'>'+m+'</'+tg+'>');return h};
 out.innerHTML='<div class="sh">일괄 바꾸기 미리보기: “'+esc(f)+'” → “'+esc(t)+'” ('+bHits.length+'행'+(bHits.length>BMAX?', 앞 '+BMAX+'행만 표시, 선택은 전체에 적용':'')+')</div>'+
  '<table><tr><th class="c"><input type="checkbox" id="ball" checked></th><th class="k">키</th><th>日本語</th><th>변경 전</th><th>변경 후</th></tr>'+
  bHits.slice(0,BMAX).map(([r,nv,name],i)=>'<tr><td class="c"><input type="checkbox" class="bk" data-i="'+i+'" checked></td><td class="k">'+esc(name.split(' ').pop()+' '+r[0])+'</td><td class="jp">'+fmt(r[3])+'</td><td>'+cell(ko(r),rf,'del')+'</td><td>'+cell(nv,rt,'ins')+'</td></tr>').join('')+'</table>';
 [...nav.children].forEach(a=>a.classList.remove('on'));cnt.textContent=bHits.length+'행';bmsg.textContent=bHits.length?'바꿀 행을 고른 뒤 "선택한 행 바꾸기"를 누르세요.':'해당하는 행이 없습니다.';scrollTo(0,0)}
out.addEventListener('change',ev=>{const t=ev.target;if(t.id==='ball'){bChk=bChk.map(()=>t.checked);out.querySelectorAll('input.bk').forEach(b=>b.checked=t.checked)}else if(t.classList.contains('bk'))bChk[+t.dataset.i]=t.checked});
document.getElementById('bprev').onclick=bulkPreview;bf.onkeydown=bt.onkeydown=e=>{if(e.key==='Enter')bulkPreview()};
document.getElementById('bapply').onclick=()=>{if(!bHits.length){bmsg.textContent='먼저 미리보기를 하세요.';return}
 bUndo=JSON.stringify(edits);let n=0;bHits.forEach(([r,nv],i)=>{if(!bChk[i])return;if(nv===r[1])delete edits[r.id];else edits[r.id]=nv;n++});
 save();bHits=[];bChk=[];bundo.disabled=false;showEdited();bmsg.textContent=n+'행을 바꿨습니다. (되돌리기 가능)'};
bundo.onclick=()=>{if(bUndo===null)return;edits=JSON.parse(bUndo);bUndo=null;bundo.disabled=true;save();showEdited();bmsg.textContent='일괄 바꾸기를 되돌렸습니다.'};
save();showAll();hh();
</script></body></html>
"""


def main():
    ver = sys.argv[1]
    data = cc_sheets() + rd_sheets()
    total = sum(len(s[2]) for s in data)
    data = dedupe(data)
    js = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    RELEASE.mkdir(exist_ok=True)
    out = RELEASE / f"CCRDE_KR_v{ver}_review.html"
    out.write_text(PAGE % {"ver": html.escape(ver), "verjs": json.dumps(ver), "data": js}, encoding="utf-8")
    shown = sum(len(s[1]) for s in data)
    print(f"{out} {out.stat().st_size} bytes, {shown} unique of {total} rows in {len(data)} sheets")


if __name__ == "__main__":
    main()
