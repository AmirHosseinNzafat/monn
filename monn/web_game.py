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
const characterMap = Object.fromEntries((GAME.characters || []).map(character => [character.id, character]));
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
let gameStarted = !(GAME.ui && GAME.ui.menu_enabled);
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
function configureVideoClip(video,start,end,loop) {
  const from=Math.max(0,Number(start)||0),to=Math.max(0,Number(end)||0);
  video.loop=!(to>from)&&loop!==false;
  video.onloadedmetadata=()=>{if(from>0&&video.currentTime<from)video.currentTime=from;};
  video.ontimeupdate=()=>{if(to>from&&video.currentTime>=to){if(loop!==false){video.currentTime=from;video.play().catch(()=>{});}else video.pause();}};
}
function render() {
  const menu = $("menu-screen");
  if (!gameStarted) {
    stopSceneTimeline();
    menu.hidden = false; $("game-main").hidden = true;
    $("menu-title").textContent = GAME.ui?.menu_title || GAME.meta.title || "Monn";
    if(GAME.ui?.menu_background)menu.style.backgroundImage="linear-gradient(#080e1dcc,#080e1dcc),url("+JSON.stringify(GAME.ui.menu_background)+")";
    $("menu-start").textContent = GAME.ui?.start_label || "شروع بازی";
    $("menu-settings").textContent = GAME.ui?.settings_label || "تنظیمات";
    return;
  }
  menu.hidden = true; $("game-main").hidden = false;
  const scene = sceneMap[state.current_scene];
  $("game-title").textContent = GAME.meta.title || "Monn";
  $("scene-title").textContent = scene.title || scene.id;
  $("scene-text").textContent = scene.text || "";
  const sceneImage = $("scene-image");
  const sceneVideo = $("scene-video");
  if (scene.video) {
    if (sceneVideo.getAttribute("src") !== scene.video) { sceneVideo.src = scene.video; sceneVideo.load(); }
    sceneVideo.hidden = false; sceneImage.hidden = true; sceneImage.removeAttribute("src");
    configureVideoClip(sceneVideo,scene.video_start,scene.video_end,scene.video_loop);
  } else {
    sceneVideo.pause(); sceneVideo.removeAttribute("src"); sceneVideo.hidden = true;
    if (scene.image) { sceneImage.src = scene.image; sceneImage.alt = scene.title || scene.id; sceneImage.hidden = false; }
    else { sceneImage.removeAttribute("src"); sceneImage.hidden = true; }
  }
  const sceneModel = $("scene-model");
  if (scene.model) { sceneModel.src = scene.model; sceneModel.hidden = false; }
  else { sceneModel.removeAttribute("src"); sceneModel.hidden = true; }
  const worldCanvas = $("world-canvas");
  worldCanvas.hidden = !(GAME.world?.enabled || scene.world_enabled);
  $("world-viewport").hidden = worldCanvas.hidden;
  if (!worldCanvas.hidden) { drawWorld(); renderWorldModels(); }
  const audio = $("scene-audio");
  if (scene.music) {
    if (audio.getAttribute("src") !== scene.music) { audio.src = scene.music; audio.load(); }
    audio.volume=Number($("volume-game")?.value??0.65);
    audio.hidden = false;
  } else { audio.pause(); audio.removeAttribute("src"); audio.hidden = true; }
  $("dialogue").replaceChildren();
  (scene.dialogue || []).forEach(line => {
    const character = characterMap[line.character] || {};
    const card = document.createElement("div"); card.className = "dialogue-line";
    const expressionVideo = line.video || (line.expression && character.expressions?.[line.expression]) || character.video;
    const portrait = line.portrait || character.portrait;
    if (expressionVideo) {
      const avatar = document.createElement("video"); avatar.src = expressionVideo;
      avatar.autoplay = true; avatar.loop = true; avatar.muted = true; avatar.playsInline = true;
      configureVideoClip(avatar,line.video_start??character.video_start,line.video_end??character.video_end,true);
      avatar.className = "character-video"; card.append(avatar);
    } else if (portrait) {
      const avatar = document.createElement("img"); avatar.src = portrait;
      avatar.alt = character.name || line.speaker || "شخصیت"; card.append(avatar);
    }
    if (character.model) {
      const model = document.createElement("model-viewer"); model.src = character.model;
      model.setAttribute("camera-controls", ""); model.setAttribute("auto-rotate", "");
      model.style.width = "150px"; model.style.height = "150px"; card.append(model);
    }
    const body = document.createElement("div");
    const speaker = document.createElement("strong");
    speaker.textContent = character.name || line.speaker || line.character || "راوی";
    const words = document.createElement("p"); words.textContent = line.text;
    body.append(speaker, words);
    const voiceSrc=line.voice||character.voice;
    if (voiceSrc) { const voice = document.createElement("audio"); voice.controls = true; voice.src = voiceSrc; body.append(voice); }
    card.append(body); $("dialogue").append(card);
  });
  renderAICharacters(scene);
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
    button.addEventListener("click", () => { playSound(choice.sound || scene.button_sound || GAME.ui?.button_sound); choose(choice); });
    $("choices").append(button);
  });
  if (state.ended) {
    const end = document.createElement("div"); end.className = "ending";
    end.textContent = state.health === 0 ? "ماجراجویی به پایان رسید؛ جان بازیکن تمام شد." : "پایان ماجراجویی";
    const menuButton=document.createElement("button");menuButton.className="choice";menuButton.textContent="بازگشت به منو";menuButton.addEventListener("click",()=>{gameStarted=false;state=initialState();render()});
    $("choices").append(end,menuButton);
  } else if (!choices.length) {
    const end = document.createElement("div"); end.className = "ending";
    end.textContent = "در این صحنه انتخاب دیگری وجود ندارد.";
    $("choices").append(end);
  }
  $("turn").textContent = "نوبت " + state.turn + " · " + state.visited.length + " صحنه کشف‌شده";
  renderCustomUI();
  startSceneTimeline(scene);
  applyUIVisibility();
}
function startGame() { gameStarted = true; playSound(GAME.ui?.button_sound); const music=$("ui-audio");if(GAME.ui?.background_music){music.src=GAME.ui.background_music;music.loop=true;music.volume=Number(GAME.ui.music_volume??0.45);music.play().catch(()=>{});}render(); }
function showGameSettings() {
  const panel = $("settings-panel"); panel.hidden = false;
}
function showCredits() {
  const root=$("credits-list");root.replaceChildren();
  const add=(title,author,source,license)=>{const row=document.createElement("div");row.className="credit-row";const strong=document.createElement("strong");strong.textContent=title||"دارایی";const info=document.createElement("p");info.textContent="پدیدآورنده: "+(author||"ثبت نشده")+" · مجوز: "+(license||"ثبت نشده");row.append(strong,info);if(source&&/^https?:\/\//i.test(source)){const link=document.createElement("a");link.href=source;link.target="_blank";link.rel="noopener noreferrer";link.textContent="مشاهده منبع";row.append(link);}root.append(row);};
  if(GAME.meta.author||GAME.meta.license)add(GAME.meta.title,GAME.meta.author,"",GAME.meta.license);
  (GAME.assets||[]).forEach(asset=>add(asset.name,asset.author,asset.source,asset.license));
  $("credits-panel").hidden=false;
}
function hideCredits() { $("credits-panel").hidden=true; }
function hideGameSettings() { $("settings-panel").hidden = true; }
function setGameVolume(value) { const volume=Math.max(0,Math.min(1,Number(value)||0));$("scene-audio").volume=volume;$("ui-audio").volume=volume; }
function applyUIVisibility() {
  const ui=GAME.ui||{};
  $("health-panel").hidden=ui.show_health===false;
  $("inventory-panel").hidden=ui.show_inventory===false;
  $("quests-panel").hidden=ui.show_quests===false;
}
function renderCustomUI() {
  const root=$("custom-ui"); root.replaceChildren();
  (GAME.ui?.elements||[]).forEach((el,index)=>{
    let node;
    if(el.type==="button") { node=document.createElement("button");node.className="choice";node.textContent=el.text||"دکمه";node.addEventListener("click",()=>{playSound(GAME.ui?.button_sound);if(el.target&&sceneMap[el.target]){state.current_scene=el.target;render();}}); }
    else if(el.type==="name_input") { node=document.createElement("input");node.placeholder=el.text||"نام بازیکن";node.value=state.player_name||"";node.addEventListener("input",()=>state.player_name=node.value); }
    else if(el.type==="location") { node=document.createElement("div");node.className="custom-label";node.textContent=sceneMap[state.current_scene]?.title||el.text||"مکان فعلی"; }
    else if(el.type==="image") { node=document.createElement("img");node.alt=el.text||"تصویر رابط";node.src=el.src||el.image||"";node.style.objectFit="contain"; }
    else { node=document.createElement("div");node.className="custom-label";node.textContent=el.type==="panel"?"":String(el.text||"").replaceAll("{player}",state.player_name||"بازیکن"); }
    node.dataset.uiId=el.id||("ui-"+index);
    node.style.position="absolute";node.style.left=(Number(el.x)||0)+"%";node.style.top=(Number(el.y)||0)+"%";node.style.width=(Number(el.width)||30)+"%";node.style.height=(Number(el.height)||12)+"%";node.style.color=el.color||"#fff";node.style.background=el.background||"transparent";node.style.fontSize=(Number(el.font_size)||14)+"px";node.style.boxSizing="border-box";node.style.borderRadius="8px";node.style.padding="6px";root.append(node);
  });
}
let timelineSceneId=null,timelineStartedAt=0,timelineTimers=[],timelineAudio=[];
function stopSceneTimeline(){timelineTimers.forEach(clearTimeout);timelineTimers=[];timelineAudio.forEach(a=>{try{a.pause();a.src=""}catch(_){}});timelineAudio=[];timelineSceneId=null}
function startSceneTimeline(scene){
  if(timelineSceneId===scene?.id)return;
  stopSceneTimeline();timelineSceneId=scene?.id||null;
  if(!scene?.timeline?.tracks)return;
  timelineStartedAt=performance.now();
  (scene.timeline.tracks||[]).forEach(track=>(track.clips||[]).forEach(clip=>{
    const delay=Math.max(0,Number(clip.start)||0)*1000,duration=Math.max(.1,Number(clip.duration)||1)*1000;
    if(track.type==="audio"&&clip.src){const timer=setTimeout(()=>{const audio=new Audio(clip.src);audio.volume=Number($("volume-game")?.value??0.65);timelineAudio.push(audio);audio.addEventListener("loadedmetadata",()=>{audio.currentTime=Math.max(0,Number(clip.in)||0);audio.play().catch(()=>{});const stop=Number(clip.out)>Number(clip.in)?(Number(clip.out)-Number(clip.in))*1000:duration;setTimeout(()=>audio.pause(),stop)},{once:true})},delay);timelineTimers.push(timer)}
    else if(track.type==="video"&&clip.src){const timer=setTimeout(()=>{const video=$("scene-video");video.src=clip.src;video.hidden=false;video.controls=true;video.addEventListener("loadedmetadata",()=>{video.currentTime=Math.max(0,Number(clip.in)||0);video.play().catch(()=>{});const stop=Number(clip.out)>Number(clip.in)?(Number(clip.out)-Number(clip.in))*1000:duration;setTimeout(()=>video.pause(),stop)},{once:true});video.load()},delay);timelineTimers.push(timer)}
    else if(track.type==="animation"&&clip.target){const timer=setTimeout(()=>{const node=[...document.querySelectorAll("[data-ui-id]")].find(n=>n.dataset.uiId===clip.target);if(!node)return;const prop=clip.property||"opacity",from=Number(clip.from)||0,to=Number(clip.to)||1,begin=performance.now();const tick=()=>{const p=Math.min(1,(performance.now()-begin)/duration),v=from+(to-from)*p;if(prop==="x")node.style.left=v+"%";else if(prop==="y")node.style.top=v+"%";else if(prop==="scale")node.style.transform="scale("+v+")";else node.style.opacity=String(v);if(p<1)requestAnimationFrame(tick)};requestAnimationFrame(tick)},delay);timelineTimers.push(timer)}
  }));
}
function playSound(src) {
  if (!src || $("mute-game")?.checked) return;
  try { const audio = new Audio(src); audio.volume = Number($("volume-game")?.value??0.65); audio.play().catch(() => {}); } catch (_) {}
}
function renderAICharacters(scene) {
  (scene.dialogue || []).forEach(line => {
    const character = characterMap[line.character] || {};
    if (!character.ai?.enabled) return;
    const panel = document.createElement("section"); panel.className = "ai-chat";
    const title = document.createElement("strong"); title.textContent = "گفتگو با " + (character.name || "شخصیت");
    const log = document.createElement("div"); log.className = "ai-log";
    const input = document.createElement("input"); input.placeholder = "پیام خود را بنویس...";
    const key = document.createElement("input"); key.type = "password"; key.placeholder = "کلید API (فقط در این نشست)";
    const send = document.createElement("button"); send.textContent = "ارسال";
    const answer = document.createElement("p"); answer.setAttribute("aria-live", "polite");
    const history=[{role:"system",content:character.ai.system_prompt || ("تو نقش "+(character.name||"یک شخصیت بازی")+" را بازی می‌کنی. فقط در چارچوب شخصیت پاسخ بده.")}];
    send.addEventListener("click", async () => {
      const message = input.value.trim(), token = key.value.trim();
      if (!message) return;
      const scripted=(character.ai.rules||[]).find(rule=>String(rule.trigger||"").trim()&&message.toLocaleLowerCase().includes(String(rule.trigger).toLocaleLowerCase()));
      if (scripted) { const item=document.createElement("p");item.textContent=(character.name||"شخصیت")+": "+scripted.response;log.append(item);history.push({role:"user",content:message},{role:"assistant",content:scripted.response});input.value="";return; }
      if (!token) { answer.textContent = "برای پاسخ‌های آزاد، کلید API را وارد کن. قواعد پاسخ ثابت بدون کلید کار می‌کنند؛ کلید در فایل بازی ذخیره نمی‌شود."; return; }
      send.disabled = true; answer.textContent = "در حال دریافت پاسخ...";
      try {
        const endpoint = (character.ai.api_base || "https://api.openai.com/v1").replace(/\/$/, "") + "/chat/completions";
        const response = await fetch(endpoint, {method:"POST", headers:{"Content-Type":"application/json","Authorization":"Bearer "+token},
          body:JSON.stringify({model:character.ai.model || "gpt-4o-mini", messages:[...history,{role:"user",content:message}]})});
        const data = await response.json();
        if (!response.ok) throw new Error(data.error?.message || "خطای سرویس هوش مصنوعی");
        const reply = data.choices?.[0]?.message?.content || "پاسخی دریافت نشد.";
        history.push({role:"user",content:message},{role:"assistant",content:reply});
        const item = document.createElement("p"); item.textContent = "بازیکن: "+message+"\n"+(character.name||"شخصیت")+": "+reply; log.append(item); input.value=""; answer.textContent="";
      } catch(error) { answer.textContent = "خطا: "+error.message+" (ممکن است سرویس مقصد CORS را پشتیبانی نکند.)"; }
      finally { send.disabled = false; }
    });
    panel.append(title, log, input, key, send, answer); $("dialogue").append(panel);
  });
}
const worldImages = new Map();
const worldPosition = {x:Number(GAME.world?.player?.x||40),y:Number(GAME.world?.player?.y||40)};
const worldKeys = new Set();
let worldFrame = 0;
function imageFor(src) {
  if (!worldImages.has(src)) { const img = new Image(); img.src = src; worldImages.set(src,img); }
  return worldImages.get(src);
}
function overlaps(a,b) {
  return a.x < b.x+b.width && a.x+a.width > b.x && a.y < b.y+b.height && a.y+a.height > b.y;
}
let worldLoopStarted=false;
function drawWorld() {
  const canvas = $("world-canvas"), world = GAME.world || {}, ctx = canvas.getContext("2d");
  const width = Number(world.width || 800), height = Number(world.height || 450);
  canvas.width = width; canvas.height = height;
  ctx.fillStyle = world.color || "#18283b"; ctx.fillRect(0,0,width,height);
  if (world.background) { const bg=imageFor(world.background); if(bg.complete)ctx.drawImage(bg,0,0,width,height); }
  (world.sprites || []).forEach(sprite => {
    const img=sprite.image && imageFor(sprite.image);
    if (img?.complete && img.naturalWidth) {
      const fw=Number(sprite.frame_width||img.naturalWidth), fh=Number(sprite.frame_height||img.naturalHeight);
      const frames=Math.max(1,Number(sprite.frames||1)), frame=Math.floor(worldFrame/(60/Math.max(1,Number(sprite.fps||8))))%frames;
      ctx.drawImage(img,frame*fw,0,fw,fh,Number(sprite.x||0),Number(sprite.y||0),Number(sprite.width||fw),Number(sprite.height||fh));
    } else {
      ctx.fillStyle=sprite.color||"#6d8bab";ctx.fillRect(sprite.x||0,sprite.y||0,sprite.width||40,sprite.height||40);
    }
  });
  const player=world.player || {x:worldPosition.x,y:worldPosition.y,width:28,height:40,color:"#4bd7df",speed:3};
  const actor={x:worldPosition.x,y:worldPosition.y,width:Number(player.width||28),height:Number(player.height||40)};
  const dx=(worldKeys.has("ArrowRight")||worldKeys.has("d")?1:0)-(worldKeys.has("ArrowLeft")||worldKeys.has("a")?1:0);
  const dy=(worldKeys.has("ArrowDown")||worldKeys.has("s")?1:0)-(worldKeys.has("ArrowUp")||worldKeys.has("w")?1:0);
  const next={...actor,x:Math.max(0,Math.min(width-actor.width,actor.x+dx*Number(player.speed||3))),y:Math.max(0,Math.min(height-actor.height,actor.y+dy*Number(player.speed||3)))};
  const hit=(world.sprites||[]).some(s=>s.solid&&overlaps(next,{x:Number(s.x||0),y:Number(s.y||0),width:Number(s.width||40),height:Number(s.height||40)}));
  if (!hit) { worldPosition.x=next.x;worldPosition.y=next.y; }
  const pimg=player.image&&imageFor(player.image);
  if(pimg?.complete&&pimg.naturalWidth)ctx.drawImage(pimg,worldPosition.x,worldPosition.y,actor.width,actor.height);
  else {ctx.fillStyle=player.color||"#4bd7df";ctx.fillRect(worldPosition.x,worldPosition.y,actor.width,actor.height);}
  worldFrame++;
  if (!worldLoopStarted) { worldLoopStarted=true; const loop=()=>{ if($("world-viewport").hidden){worldLoopStarted=false;return;}drawWorldFrame();requestAnimationFrame(loop); }; requestAnimationFrame(loop); }
}
function renderWorldModels() {
  const root=$("world-models"),world=GAME.world||{},w=Number(world.width||800),h=Number(world.height||450);
  root.replaceChildren();
  (world.sprites||[]).filter(sp=>sp.model).forEach(sp=>{
    const model=document.createElement("model-viewer");model.src=sp.model;model.setAttribute("camera-controls","");
    model.style.position="absolute";model.style.left=(Number(sp.x||0)/w*100)+"%";model.style.top=(Number(sp.y||0)/h*100)+"%";
    model.style.width=(Number(sp.width||100)/w*100)+"%";model.style.height=(Number(sp.height||100)/h*100)+"%";root.append(model);
  });
  if(world.player?.model){const model=document.createElement("model-viewer");model.src=world.player.model;model.dataset.worldPlayer="true";model.setAttribute("camera-controls","");
    model.style.position="absolute";model.style.left=(worldPosition.x/w*100)+"%";model.style.top=(worldPosition.y/h*100)+"%";
    model.style.width=(Number(world.player.width||80)/w*100)+"%";model.style.height=(Number(world.player.height||100)/h*100)+"%";root.append(model);}
}
function drawWorldFrame() {
  const canvas=$("world-canvas"), world=GAME.world||{}, ctx=canvas.getContext("2d");
  const width=Number(world.width||800),height=Number(world.height||450);
  ctx.clearRect(0,0,width,height);ctx.fillStyle=world.color||"#18283b";ctx.fillRect(0,0,width,height);
  if(world.background){const bg=imageFor(world.background);if(bg.complete)ctx.drawImage(bg,0,0,width,height);}
  (world.sprites||[]).forEach(sprite=>{if(sprite.model)return;const img=sprite.image&&imageFor(sprite.image);if(img?.complete&&img.naturalWidth){const fw=Number(sprite.frame_width||img.naturalWidth),fh=Number(sprite.frame_height||img.naturalHeight),frames=Math.max(1,Number(sprite.frames||1)),frame=Math.floor(worldFrame/(60/Math.max(1,Number(sprite.fps||8))))%frames;ctx.drawImage(img,frame*fw,0,fw,fh,Number(sprite.x||0),Number(sprite.y||0),Number(sprite.width||fw),Number(sprite.height||fh));}else{ctx.fillStyle=sprite.color||"#6d8bab";ctx.fillRect(sprite.x||0,sprite.y||0,sprite.width||40,sprite.height||40);}});
  const player=world.player||{width:28,height:40,color:"#42d7e8",speed:3};
  const actor={x:worldPosition.x,y:worldPosition.y,width:Number(player.width||28),height:Number(player.height||40)};
  const dx=(worldKeys.has("ArrowRight")||worldKeys.has("d")?1:0)-(worldKeys.has("ArrowLeft")||worldKeys.has("a")?1:0);
  const dy=(worldKeys.has("ArrowDown")||worldKeys.has("s")?1:0)-(worldKeys.has("ArrowUp")||worldKeys.has("w")?1:0);
  const next={...actor,x:Math.max(0,Math.min(width-actor.width,actor.x+dx*Number(player.speed||3))),y:Math.max(0,Math.min(height-actor.height,actor.y+dy*Number(player.speed||3)))};
  const hit=(world.sprites||[]).some(sp=>sp.solid&&overlaps(next,{x:Number(sp.x||0),y:Number(sp.y||0),width:Number(sp.width||40),height:Number(sp.height||40)}));
  if(!hit){worldPosition.x=next.x;worldPosition.y=next.y;}
  const modelPlayer=$("world-models").querySelector('[data-world-player="true"]');
  if(modelPlayer){modelPlayer.style.left=(worldPosition.x/width*100)+"%";modelPlayer.style.top=(worldPosition.y/height*100)+"%";}
  const pimg=player.image&&imageFor(player.image);
  if(pimg?.complete&&pimg.naturalWidth){const fw=Number(player.frame_width||pimg.naturalWidth),fh=Number(player.frame_height||pimg.naturalHeight),frames=Math.max(1,Number(player.frames||1)),frame=Math.floor(worldFrame/(60/Math.max(1,Number(player.fps||8))))%frames;ctx.drawImage(pimg,frame*fw,0,fw,fh,worldPosition.x,worldPosition.y,actor.width,actor.height);}
  else{ctx.fillStyle=player.color||"#42d7e8";ctx.fillRect(worldPosition.x,worldPosition.y,actor.width,actor.height);}
  worldFrame++;
}
window.addEventListener("keydown",e=>{if(["ArrowUp","ArrowDown","ArrowLeft","ArrowRight"].includes(e.key))e.preventDefault();worldKeys.add(e.key)});
window.addEventListener("keyup",e=>worldKeys.delete(e.key));
function choose(choice) {
  const before = clone(state);
  try {
    (choice.effects || []).forEach(applyEffect);
    if (choice.target) {
      state.current_scene = choice.target;
      if (!state.visited.includes(choice.target)) state.visited.push(choice.target);
      state.turn += 1;
    } else {
      state.ended = true;
      if (GAME.meta.ending_scene && sceneMap[GAME.meta.ending_scene]) state.current_scene = GAME.meta.ending_scene;
    }
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
function validSavedState(s) {
  if (!s || typeof s !== "object" || !sceneMap[s.current_scene]) return false;
  if (!Number.isFinite(s.health) || !Number.isFinite(s.max_health) || s.health < 0 || s.health > s.max_health || s.max_health > 1000000) return false;
  if (!s.stats || typeof s.stats !== "object" || !s.flags || typeof s.flags !== "object") return false;
  if (!s.inventory || typeof s.inventory !== "object" || !s.quests || typeof s.quests !== "object") return false;
  if (!Array.isArray(s.journal) || !s.journal.every(x => typeof x === "string")) return false;
  if (!Array.isArray(s.visited) || !s.visited.every(id => !!sceneMap[id])) return false;
  if (typeof s.ended !== "boolean" || !Number.isInteger(s.turn) || s.turn < 1) return false;
  if (!Object.values(s.stats).every(v => typeof v === "number" && Number.isFinite(v))) return false;
  if (!Object.entries(s.inventory).every(([k,v]) => typeof k === "string" && Number.isInteger(v) && v > 0 && v <= 1000000)) return false;
  if (!Object.entries(s.quests).every(([k,v]) => !!questMap[k] && ["active","completed","failed"].includes(v))) return false;
  return true;
}
function loadGame() {
  try {
    const raw = localStorage.getItem(SAVE_KEY);
    if (!raw) throw new Error("ذخیره‌ای برای این بازی پیدا نشد.");
    const data = JSON.parse(raw);
    if (data.version !== 1 || !validSavedState(data.state)) throw new Error("فایل ذخیره معتبر نیست.");
    state = data.state; gameStarted=true; setMessage("بازی بارگذاری شد."); render();
  } catch(error) { setMessage(error.message, true); }
}
function resetGame() {
  if (!confirm("از شروع دوباره مطمئنی؟")) return;
  state = initialState(); gameStarted=true; setMessage("بازی از ابتدا آغاز شد."); render();
}
$("menu-start").addEventListener("click", startGame);
$("menu-settings").addEventListener("click", showGameSettings);
$("settings-close").addEventListener("click", hideGameSettings);
$("credits-open").addEventListener("click", showCredits);
$("credits-close").addEventListener("click", hideCredits);
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
.scene-image{display:block;width:100%;max-height:280px;object-fit:cover;border-radius:13px;margin:4px 0 16px;border:1px solid var(--line)}
.dialogue-list{display:grid;gap:9px;margin-top:14px}.dialogue-line{display:flex;align-items:flex-start;gap:12px;padding:12px;background:#0c1728;border:1px solid var(--line);border-radius:12px}
.dialogue-line img,.dialogue-line video{width:112px;height:112px;object-fit:cover;border-radius:12px}.world-viewport{position:relative;width:100%;aspect-ratio:16/9;margin:12px 0;overflow:hidden;border-radius:12px;background:#111}.world-canvas{display:block;width:100%;height:100%;object-fit:contain;background:#111}#world-models{position:absolute;inset:0;pointer-events:auto}.ai-chat{display:grid;gap:8px;padding:12px;background:#111c2e;border:1px solid var(--line);border-radius:12px}.ai-chat input{width:100%;padding:9px;border-radius:8px;border:1px solid var(--line);background:#0b1424;color:var(--text)}.ai-log{max-height:180px;overflow:auto}.ai-log p{white-space:pre-wrap}.dialogue-line strong{color:var(--gold);font-size:13px}.dialogue-line p{margin:5px 0 0;line-height:1.8}
audio{width:100%;margin:12px 0}
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
footer{text-align:center;color:#71839d;padding:16px;font-size:12px}.menu-screen,.settings-panel{position:fixed;inset:0;z-index:30;display:grid;place-items:center;background:linear-gradient(140deg,#080e1d,#172a45);background-size:cover;padding:20px}.menu-card{width:min(560px,100%);padding:36px;background:#0e1a2deF;border:1px solid #38577e;border-radius:20px;display:grid;gap:14px;text-align:center;box-shadow:0 25px 90px #0009}.menu-card h1{font-size:32px}.credit-row{text-align:right;border:1px solid var(--line);padding:10px;border-radius:9px;margin:8px 0}.credit-row p{font-size:12px;color:var(--muted)}.credit-row a{color:#7dddea}.settings-panel{z-index:31}.story{position:relative}.custom-ui{position:absolute;inset:0;pointer-events:none;z-index:5}.custom-ui>*{pointer-events:auto}.custom-ui .custom-label{padding:8px;background:#101b2dcc;border-radius:8px}
@media(max-width:780px){main{grid-template-columns:1fr;margin:14px auto}.story{min-height:320px}header{padding:18px}h2{font-size:21px}}
</style></head><body>
<div id="menu-screen" class="menu-screen" hidden><div class="menu-card"><h1 id="menu-title"></h1><button class="choice" id="menu-start">شروع بازی</button><button class="choice" id="menu-settings">تنظیمات</button></div></div><div id="credits-panel" class="settings-panel" hidden><div class="menu-card"><h2>عوامل و مجوزها</h2><div id="credits-list"></div><button id="credits-close">بازگشت</button></div></div><div id="settings-panel" class="settings-panel" hidden><div class="menu-card"><h2>تنظیمات بازی</h2><label><input id="mute-game" type="checkbox"> بی‌صدا</label><label>بلندی صدا <input id="volume-game" type="range" min="0" max="1" step="0.05" value="0.65" oninput="setGameVolume(this.value)"></label><button id="settings-close">بازگشت</button></div></div><header><div><h1 id="game-title">""" + page_title + """</h1><small id="turn"></small></div>
<div class="toolbar"><button id="credits-open">منابع و مجوزها</button><button id="save">ذخیره</button><button id="load">بارگذاری</button><button id="reset">شروع دوباره</button></div></header>
<audio id="ui-audio" preload="none"></audio><div id="message" role="status" aria-live="polite"></div>
<main id="game-main"><section class="panel story"><div class="eyebrow">روایت تعاملی · MONN GAME ENGINE</div><h2 id="scene-title"></h2>
<img id="scene-image" class="scene-image" alt="" hidden><video id="scene-video" class="scene-image" controls playsinline preload="metadata" hidden></video><model-viewer id="scene-model" camera-controls auto-rotate style="width:100%;height:300px" hidden></model-viewer><div id="world-viewport" class="world-viewport" hidden><canvas id="world-canvas" class="world-canvas"></canvas><div id="world-models"></div></div><div id="scene-text" class="story-text"></div>
<div id="dialogue" class="dialogue-list"></div><audio id="scene-audio" controls preload="none" hidden></audio>
<div id="choices" class="choices"></div><div id="custom-ui" class="custom-ui"></div></section>
<aside class="side">
<section class="panel" id="health-panel"><h3>وضعیت بازیکن</h3><div id="health"></div><div class="health-track"><div id="health-bar" class="health-fill"></div></div><div id="stats" class="stat-list" style="margin-top:12px"></div></section>
<section class="panel" id="inventory-panel"><h3>کوله‌پشتی</h3><div id="inventory"></div></section>
<section class="panel" id="quests-panel"><h3>مأموریت‌ها</h3><div id="quests"></div></section>
<section class="panel"><h3>دفترچه وقایع</h3><ul id="journal"></ul></section>
</aside></main><footer>ساخته‌شده با موتور بازی MonnLang · ذخیره محلی روی همین مرورگر</footer>
<script type="module" src="https://unpkg.com/@google/model-viewer/dist/model-viewer.min.js"></script><script>""" + script + """</script></body></html>"""
