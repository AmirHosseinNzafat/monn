"""Standalone HTML5 player for Monn narrative-game projects."""
import json
from html import escape

from .game import GameProject


def compile_game_to_html(project, title=None):
    """Compile a validated game project into a self-contained browser game."""
    game = project if isinstance(project, GameProject) else GameProject(project)
    payload = json.dumps(game.data, ensure_ascii=False, separators=(",", ":"))
    payload = payload.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    page_title = escape(title or game.title)
    fingerprint = game.fingerprint
    script = r"""
const GAME = __GAME__;
const SAVE_KEY = "monn-game-" + __FINGERPRINT__;
const $ = (id) => document.getElementById(id);
const clone = (value) => JSON.parse(JSON.stringify(value));
const sceneMap = Object.fromEntries(GAME.scenes.map(scene => [scene.id, scene]));
const questMap = Object.fromEntries((GAME.quests || []).map(q => [q.id, q]));
function initialState() {
  const p = GAME.player || {};
  const health = Number(p.health ?? 100);
  const maxHealth = Number(p.max_health ?? Math.max(health, 100));
  const inventory = {};
  (p.inventory || []).forEach(item => {
    if (typeof item === "string") inventory[item] = (inventory[item] || 0) + 1;
    else inventory[item.name] = (inventory[item.name] || 0) + Number(item.count || 1);
  });
  return {
    current_scene: GAME.meta.start_scene, health, max_health: maxHealth,
    stats: clone(p.stats || {}), flags: {}, inventory, quests: {},
    journal: [], visited: [GAME.meta.start_scene], ended: false, turn: 1
  };
}
let state = initialState();
function setMessage(text, bad=false) {
  $("message").textContent = text || "";
  $("message").classList.toggle("error", !!bad);
}
function cmp(a, op, b) {
  switch(op) {
    case "=": case "==": return a === b;
    case "!=": return a !== b;
    case ">": return a > b;
    case "<": return a < b;
    case ">=": return a >= b;
    case "<=": return a <= b;
    default: return false;
  }
}
function condition(c) {
  let actual;
  switch(c.type || "stat") {
    case "stat": actual = state.stats[c.name || c.id] ?? 0; break;
    case "health": actual = state.health; break;
    case "flag": actual = state.flags[c.name || c.id] ?? false; break;
    case "item": actual = state.inventory[c.name || c.id] ?? 0; break;
    case "quest": actual = state.quests[c.name || c.id] ?? "inactive"; break;
    default: return false;
  }
  return cmp(actual, c.op || "==", c.value ?? true);
}
function applyEffect(e) {
  const name = e.name || e.id;
  const value = Number(e.value ?? 0);
  if (e.type === "stat") {
    const old = Number(state.stats[name] || 0);
    state.stats[name] = e.op === "set" ? value : e.op === "subtract" ? old - value : old + value;
  } else if (e.type === "health") {
    const old = state.health;
    const next = e.op === "set" ? value : e.op === "subtract" ? old - value : old + value;
    state.health = Math.max(0, Math.min(state.max_health, next));
    if (state.health === 0) state.ended = true;
  } else if (e.type === "item") {
    const count = Number(e.count || 1), old = Number(state.inventory[name] || 0);
    if (e.action === "remove") {
      if (old < count) throw new Error("آیتم کافی در کوله‌پشتی وجود ندارد: " + name);
      if (old === count) delete state.inventory[name]; else state.inventory[name] = old - count;
    } else if (e.action === "set") {
      if (count > 0) state.inventory[name] = count; else delete state.inventory[name];
    } else state.inventory[name] = old + count;
  } else if (e.type === "flag") {
    state.flags[name] = e.value ?? true;
  } else if (e.type === "quest") {
    state.quests[name] = ({start:"active", complete:"completed", fail:"failed"})[e.action];
  } else if (e.type === "journal") {
    state.journal.push(e.text);
  }
}
function render() {
  const scene = sceneMap[state.current_scene];
  $("game-title").textContent = GAME.meta.title || "Monn";
  $("scene-title").textContent = scene.title || scene.id;
  $("scene-text").textContent = scene.text || "";
  $("health").textContent = state.health + " / " + state.max_health;
  $("health-bar").style.width = (state.health / state.max_health * 100) + "%";
  $("stats").replaceChildren();
  Object.entries(state.stats).forEach(([key, value]) => {
    const item = document.createElement("div"); item.className = "stat";
    const name = document.createElement("span"); name.textContent = key;
    const val = document.createElement("b"); val.textContent = String(value);
    item.append(name, val); $("stats").append(item);
  });
  $("inventory").replaceChildren();
  const items = Object.entries(state.inventory);
  if (!items.length) $("inventory").textContent = "کوله‌پشتی خالی است";
  items.forEach(([name, count]) => {
    const item = document.createElement("div"); item.className = "inventory-item";
    item.textContent = name + " × " + count; $("inventory").append(item);
  });
  $("quests").replaceChildren();
  const quests = Object.entries(state.quests);
  if (!quests.length) $("quests").textContent = "هنوز مأموریتی ثبت نشده";
  quests.forEach(([id, status]) => {
    const item = document.createElement("div"); item.className = "quest";
    item.textContent = (questMap[id]?.title || id) + " — " + status; $("quests").append(item);
  });
  $("journal").replaceChildren();
  if (!state.journal.length) $("journal").textContent = "هنوز یادداشتی ثبت نشده";
  state.journal.forEach(line => {
    const item = document.createElement("li"); item.textContent = line; $("journal").append(item);
  });
  $("choices").replaceChildren();
  const choices = (scene.choices || []).filter(choice => (choice.conditions || []).every(condition));
  choices.forEach(choice => {
    const button = document.createElement("button"); button.className = "choice";
    button.textContent = choice.text;
    button.addEventListener("click", () => choose(choice));
    $("choices").append(button);
  });
  if (state.ended) {
    const end = document.createElement("div"); end.className = "ending";
    end.textContent = state.health === 0 ? "ماجراجویی به پایان رسید؛ جان بازیکن تمام شد." : "پایان ماجراجویی";
    $("choices").append(end);
  } else if (!choices.length) {
    const end = document.createElement("div"); end.className = "ending";
    end.textContent = "در این صحنه انتخاب دیگری وجود ندارد.";
    $("choices").append(end);
  }
  $("turn").textContent = "نوبت " + state.turn + " · " + state.visited.length + " صحنه کشف‌شده";
}
function choose(choice) {
  const before = clone(state);
  try {
    (choice.effects || []).forEach(applyEffect);
    if (choice.target) {
      state.current_scene = choice.target;
      if (!state.visited.includes(choice.target)) state.visited.push(choice.target);
      state.turn += 1;
    } else state.ended = true;
    setMessage("");
    render();
  } catch(error) {
    state = before; setMessage(error.message, true); render();
  }
}
function saveGame() {
  try {
    localStorage.setItem(SAVE_KEY, JSON.stringify({version:1, state}));
    setMessage("بازی روی همین مرورگر ذخیره شد.");
  } catch(error) { setMessage("ذخیره‌سازی ناموفق بود: " + error.message, true); }
}
function loadGame() {
  try {
    const raw = localStorage.getItem(SAVE_KEY);
    if (!raw) throw new Error("ذخیره‌ای برای این بازی پیدا نشد.");
    const data = JSON.parse(raw);
    if (data.version !== 1 || !data.state || !sceneMap[data.state.current_scene]) throw new Error("فایل ذخیره معتبر نیست.");
    state = data.state; setMessage("بازی بارگذاری شد."); render();
  } catch(error) { setMessage(error.message, true); }
}
function resetGame() {
  if (!confirm("از شروع دوباره مطمئنی؟")) return;
  state = initialState(); setMessage("بازی از ابتدا آغاز شد."); render();
}
$("save").addEventListener("click", saveGame);
$("load").addEventListener("click", loadGame);
$("reset").addEventListener("click", resetGame);
render();
""".replace("__GAME__", payload).replace("__FINGERPRINT__", json.dumps(fingerprint))
    return """<!doctype html>
<html lang="fa" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>""" + page_title + """</title>
<style>
:root{color-scheme:dark;--bg:#090e19;--panel:#111b2c;--panel2:#17243a;--line:#283a55;--text:#edf3ff;--muted:#9aabc4;--accent:#73a7ff;--gold:#e8bd69;--danger:#ff737d}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(ellipse at 20% 0%,#1b3154 0,transparent 42%),var(--bg);color:var(--text);font-family:Tahoma,Arial,sans-serif;min-height:100vh}
header{padding:24px max(20px,calc((100vw - 1180px)/2));border-bottom:1px solid var(--line);display:flex;justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap}
header h1{margin:0;font-size:22px}header small{color:var(--muted)}
main{max-width:1180px;margin:24px auto;padding:0 18px;display:grid;grid-template-columns:minmax(0,1fr) 300px;gap:18px}
.panel{background:linear-gradient(145deg,#142138,#0f1828);border:1px solid var(--line);border-radius:18px;padding:22px;box-shadow:0 18px 50px #0004}
.story{min-height:390px;display:flex;flex-direction:column}.eyebrow{color:var(--gold);font-size:12px;letter-spacing:1px}
h2{font-size:25px;margin:12px 0 18px}.story-text{font-size:16px;line-height:2.2;white-space:pre-wrap;color:#d9e4f5;flex:1}
.choices{display:grid;gap:10px;margin-top:24px}.choice{border:1px solid #38577e;background:linear-gradient(90deg,#203b62,#1a2b45);color:white;text-align:right;padding:14px 16px;border-radius:12px;font:inherit;cursor:pointer;transition:.16s}
.choice:hover{border-color:var(--accent);transform:translateY(-1px);background:#294b78}
.ending{padding:15px;border:1px solid #8b6c39;color:var(--gold);border-radius:12px;margin-top:10px}
.side{display:grid;gap:14px;align-content:start}.side h3{margin:0 0 12px;font-size:15px;color:#c9d8ee}
.health-track{height:9px;background:#27354b;border-radius:9px;overflow:hidden;margin-top:9px}.health-fill{height:100%;background:linear-gradient(90deg,#e05c69,#e9a46c);width:100%;transition:width .2s}
.stat-list{display:grid;gap:8px}.stat{display:flex;justify-content:space-between;color:var(--muted);padding:7px 0;border-bottom:1px solid #26364d}.stat b{color:var(--text)}
.inventory-item,.quest{padding:8px 10px;background:var(--panel2);border-radius:9px;margin:6px 0;color:#d9e4f5;font-size:13px}
.quest{color:var(--gold)}ul{padding-right:20px;color:var(--muted);line-height:1.9;font-size:13px}
.toolbar{display:flex;gap:8px;flex-wrap:wrap}.toolbar button{font:inherit;border:1px solid var(--line);background:#1b2a42;color:var(--text);padding:9px 12px;border-radius:9px;cursor:pointer}.toolbar button:hover{border-color:var(--accent)}
#message{max-width:1180px;margin:0 auto 18px;padding:0 18px;color:#8dd7ae;min-height:22px}#message.error{color:var(--danger)}
footer{text-align:center;color:#71839d;padding:16px;font-size:12px}
@media(max-width:780px){main{grid-template-columns:1fr;margin:14px auto}.story{min-height:320px}header{padding:18px}h2{font-size:21px}}
</style></head><body>
<header><div><h1 id="game-title">""" + page_title + """</h1><small id="turn"></small></div>
<div class="toolbar"><button id="save">ذخیره</button><button id="load">بارگذاری</button><button id="reset">شروع دوباره</button></div></header>
<div id="message" role="status" aria-live="polite"></div>
<main><section class="panel story"><div class="eyebrow">روایت تعاملی · MONN GAME ENGINE</div><h2 id="scene-title"></h2>
<div id="scene-text" class="story-text"></div><div id="choices" class="choices"></div></section>
<aside class="side">
<section class="panel"><h3>وضعیت بازیکن</h3><div id="health"></div><div class="health-track"><div id="health-bar" class="health-fill"></div></div><div id="stats" class="stat-list" style="margin-top:12px"></div></section>
<section class="panel"><h3>کوله‌پشتی</h3><div id="inventory"></div></section>
<section class="panel"><h3>مأموریت‌ها</h3><div id="quests"></div></section>
<section class="panel"><h3>دفترچه وقایع</h3><ul id="journal"></ul></section>
</aside></main><footer>ساخته‌شده با موتور بازی MonnLang · ذخیره محلی روی همین مرورگر</footer>
<script>""" + script + """</script></body></html>"""
