"""Compile the portable MonnLang subset to a standalone HTML application."""
import json
from html import escape
from .lexer import Lexer
from .parser import Parser

def _js_value(raw):
    if raw is None: return "null"
    s = str(raw).strip()
    if s.startswith("$"): return "state[" + json.dumps(s[1:], ensure_ascii=False) + "]"
    if len(s) > 1 and s[0] == s[-1] and s[0] in ("'", '"'): return json.dumps(s[1:-1], ensure_ascii=False)
    if s.lower() in ("true","درست"): return "true"
    if s.lower() in ("false","نادرست"): return "false"
    try: float(s); return s
    except ValueError: return "state[" + json.dumps(s, ensure_ascii=False) + "] ?? " + json.dumps(s, ensure_ascii=False)

def compile_to_html(source, title="Monn Web App"):
    """Compile common UI, variable, loop and conditional commands into one HTML file."""
    tree = Parser(Lexer().tokenize(source)).parse()
    js = [
      'const root=document.getElementById("app"); const state={};',
      'function add(tag,text,cls){const e=document.createElement(tag);if(text!==undefined)e.textContent=String(text);if(cls)e.className=cls;root.appendChild(e);return e;}',
      'function button(text,action){const e=add("button",text);e.addEventListener("click",()=>{const out=document.getElementById("result");if(!action){out.textContent="انتخاب شد: "+text;return;}const [kind,...rest]=action.split(":");const value=rest.join(":");if(kind==="پیام"||kind==="message"){out.textContent=value;}else if((kind==="تنظیم"||kind==="set")&&value.includes("=")){const [k,v]=value.split("=");state[k.trim()]=v.trim();out.textContent=k.trim()+" = "+v.trim();}else if(["افزایش","increase","کاهش","decrease"].includes(kind)&&value.includes("=")){const [k,v]=value.split("=");const d=Number(v);state[k.trim()]=(Number(state[k.trim()])||0)+(kind==="افزایش"||kind==="increase"?d:-d);out.textContent=k.trim()+" = "+state[k.trim()];}else{out.textContent="کنش ناشناخته: "+action;}});return e;}'
    ]
    def emit(nodes):
        for n in nodes:
            op,p=n.op,n.params
            if op=="SET_VAR":
                js.append("state["+json.dumps(p["name"],ensure_ascii=False)+"]="+_js_value(p["val"])+";")
            elif op=="PRINT":
                js.append('add("pre",JSON.stringify(state,null,2));')
            elif op=="CREATE_WINDOW": pass
            elif op=="CREATE_BUTTON":
                js.append("button("+json.dumps(p.get("t",p.get("text","")),ensure_ascii=False)+","+json.dumps(p.get("action",""),ensure_ascii=False)+");")
            elif op=="CREATE_LABEL":
                js.append('add("p",'+json.dumps(p.get("t",p.get("text","")),ensure_ascii=False)+');')
            elif op=="CREATE_ENTRY":
                js.append('add("input").placeholder="متن خود را وارد کنید";')
            elif op=="CREATE_TEXTBOX":
                js.append('add("textarea").placeholder="متن خود را بنویسید";')
            elif op=="CREATE_CHECKBOX":
                js.append('const c=add("label");const x=document.createElement("input");x.type="checkbox";c.append(x,c.ownerDocument.createTextNode(" گزینه"));')
            elif op=="CREATE_SLIDER":
                js.append('const s=add("input");s.type="range";s.min=0;s.max=100;')
            elif op=="CREATE_PROGRESS":
                js.append('const pr=add("progress");pr.max=100;pr.value=65;')
            elif op=="CREATE_LISTBOX":
                js.append('const s=add("select");["گزینه اول","گزینه دوم","گزینه سوم"].forEach(v=>{const o=document.createElement("option");o.textContent=v;s.append(o);});')
            elif op=="CREATE_COMBOBOX":
                js.append('const s=add("select");["گزینه اول","گزینه دوم","گزینه سوم"].forEach(v=>{const o=document.createElement("option");o.textContent=v;s.append(o);});')
            elif op=="CREATE_FRAME":
                js.append('const f=add("section");f.className="panel";')
            elif op=="CREATE_CANVAS":
                js.append('const c=add("canvas");c.width=480;c.height=180;c.className="panel";')
            elif op=="SET_TITLE":
                js.append("document.title="+json.dumps(p["t"],ensure_ascii=False)+";")
            elif op=="SET_BG":
                js.append("document.body.style.background="+json.dumps(p["c"])+";")
            elif op=="SET_FG":
                js.append("document.body.style.color="+json.dumps(p["c"])+";")
            elif op=="SET_FONT":
                js.append("document.body.style.fontSize="+json.dumps(str(p["s"])+"px")+";")
            elif op=="SET_SIZE":
                js.append("root.style.maxWidth="+json.dumps(str(p["w"])+"px")+";")
            elif op=="SET_PADDING":
                js.append("root.style.gap="+json.dumps(str(p["n"])+"px")+";")
            elif op=="THEME_DARK":
                js.append('document.body.classList.add("dark");')
            elif op=="THEME_LIGHT":
                js.append('document.body.classList.remove("dark");')
            elif op=="IF_START":
                if p:
                    left,right=_js_value(p["left"]),_js_value(p["right"])
                    operator={"=":"===","==":"===","!=":"!==","بزرگتر":">","کوچکتر":"<"}.get(p["op"],p["op"])
                    js.append("if("+left+operator+right+"){"); emit(n.children)
                    if n.alternate: js.append("}else{"); emit(n.alternate)
                    js.append("}")
                else:
                    js.append("if(true){"); emit(n.children); js.append("}")
            elif op=="LOOP_COUNT":
                js.append("for(let i=0;i<Math.max(0,Math.min(10000,"+str(max(0,min(int(p["n"]),10000)))+"));i++){state.loop_index=i;"); emit(n.children); js.append("}")
            elif op=="LOOP_START":
                js.append("{"); emit(n.children); js.append("}")
            elif op in ("PACK_LEFT","PACK_RIGHT","PACK_TOP","PACK_BOTTOM","PLACE_CENTER"):
                cls={"PACK_LEFT":"left","PACK_RIGHT":"right","PACK_TOP":"top","PACK_BOTTOM":"bottom","PLACE_CENTER":"center"}[op]
                js.append('root.classList.add("layout-'+cls+'");')
            elif op in ("CREATE_CHAT","CREATE_TABS","CREATE_RADIO","CREATE_MENU"):
                js.append('add("p","این ابزار در نسخه دسکتاپ کامل‌تر است؛ در وب از اجزای استاندارد استفاده کنید.","hint");')
            elif op in ("ELSE","BLOCK_END","IF_END"): pass
            else:
                js.append('add("p",'+json.dumps("در نسخه وب پشتیبانی نشده: "+op,ensure_ascii=False)+',"hint");')
    emit(tree.children)
    script="\n".join(js)
    safe_title=escape(title)
    return """<!doctype html>
<html lang="fa" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>"""+safe_title+"""</title><style>
*{box-sizing:border-box}body{margin:0;padding:24px;font-family:Tahoma,Arial,sans-serif;background:#eef2f7;color:#172033;transition:.2s}
#app{max-width:900px;margin:30px auto;padding:24px;display:flex;flex-wrap:wrap;align-items:center;gap:12px;background:#fff;border-radius:18px;box-shadow:0 12px 40px #14213d18}
button,input,textarea,select{font:inherit;padding:11px 14px;border:1px solid #cbd5e1;border-radius:10px;max-width:100%}
button{background:#2563eb;color:white;border:0;cursor:pointer}button:hover{filter:brightness(1.1)}
p{width:100%;margin:6px 0}.panel{width:100%;padding:16px;border:1px solid #cbd5e1;border-radius:12px}
pre,#result{width:100%;white-space:pre-wrap}.hint{color:#64748b;font-size:.9em}
.dark{background:#0f172a;color:#e2e8f0}.dark #app{background:#1e293b;color:#e2e8f0}.layout-left{justify-content:flex-start}.layout-right{justify-content:flex-end}.layout-center{justify-content:center}
</style></head><body><main id="app"><h1 style="width:100%">"""+safe_title+"""</h1><div id="result" aria-live="polite"></div></main><script>
"""+script+"""
</script></body></html>"""
