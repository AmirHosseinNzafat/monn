/* Monn Studio offline-first UX repair layer.
   Loaded after the core Studio script; no external libraries or network calls. */
(function(){
  "use strict";
  const $ = id => document.getElementById(id);
  const escapeHTML = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  let projectFolderId = null;
  const templates = [
    ["starter-story","داستان آموزشی","پروژه سبک برای یادگیری صحنه و انتخاب"],
    ["romance_short","داستان عاشقانه کوتاه","داستان تصویری کوتاه با چند پایان"],
    ["workshop_medium","کارگاه متوسط سه‌بعدی","محیط صنعتی، اشیای سه‌بعدی و نورپردازی"],
    ["battle_base","بتل‌بیس سه‌بعدی","پایگاه، دشمن آموزشی و هدف تمرینی"]
  ];
  function modal(title,body,width="760px"){
    const card=$("modal").querySelector(".modal-card");
    card.style.width="min("+width+",100%)";
    card.innerHTML='<div class="panel-head">'+title+' <button onclick="closePreview()">بستن</button></div>'+body;
    $("modal").classList.add("open");
  }
  async function postJSON(path,data){
    const response=await fetch(path,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(data)});
    const type=response.headers.get("content-type")||"";
    const body=type.includes("application/json")?await response.json():{error:await response.text()};
    if(!response.ok)throw new Error(body.error||("خطای سرور: "+response.status));
    return body;
  }
  window.newProject=function(){
    modal("پروژهٔ جدید Monn",'<p class="muted">یک قالب انتخاب کن. Monn پروژه را با الگوریتم‌های داخلی می‌سازد؛ برای این کار به اینترنت، API یا مدل زبانی نیاز نیست.</p>'+
      '<div class="field"><label>نام پروژه</label><input id="newProjectTitle" value="بازی تازه من" maxlength="64"></div>'+
      '<div class="field"><label>قالب شروع</label><select id="newProjectTemplate">'+templates.map(t=>'<option value="'+t[0]+'">'+t[1]+' — '+t[2]+'</option>').join("")+'</select></div>'+
      '<div class="field"><label>ایده یا توضیح اختیاری برای نیترو آفلاین</label><textarea id="newProjectPrompt" placeholder="مثلاً یک پایگاه آموزشی با دشمن و دو هدف بساز..."></textarea></div>'+
      '<button class="primary" id="createProjectButton" onclick="MonnOffline.createProject()">انتخاب پوشه و ساخت پروژه</button><p class="muted" id="newProjectStatus">پوشهٔ انتخابی روی همین رایانه ساخته می‌شود.</p>',"680px");
  };
  window.MonnOffline={
    async createProject(){
      const button=$("createProjectButton"),status=$("newProjectStatus");
      button.disabled=true;status.textContent="در حال ساخت پروژه...";
      try{
        const result=await postJSON("/api/project/create",{
          title:$("newProjectTitle").value.trim()||"بازی تازه من",
          template:$("newProjectTemplate").value,
          prompt:$("newProjectPrompt").value
        });
        projectFolderId=result.folder_id;
        project=result.project;
        if(typeof ensureProjectShape==="function")ensureProjectShape();
        active=project.meta.start_scene;
        if(typeof render==="function")render();
        if(typeof persist==="function")persist();
        status.textContent="پروژه ساخته شد: "+result.path;
        toast("پروژه در پوشهٔ انتخابی ساخته شد.");
        closePreview();
      }catch(error){status.textContent="ساخت پروژه ناموفق بود: "+error.message;button.disabled=false;}
    },
    async save(){
      if(!projectFolderId){if(typeof saveMonn==="function")return saveMonn();return;}
      try{
        const result=await postJSON("/api/project/save",{folder_id:projectFolderId,project:project});
        toast("پروژه در مسیر انتخاب‌شده ذخیره شد.");
        $("saveStatus").textContent="● ذخیره در پوشه پروژه";
        return result;
      }catch(error){toast("خطای ذخیره: "+error.message);}
    }
  };
  window.openNitro=function(){
    modal("نیترو · سازندهٔ الگوریتمی آفلاین",'<p class="muted">نیترو داخلی Monn بدون Ollama، مدل زبانی، اینترنت یا کلید API کار می‌کند. ایده را می‌خواند، نوع پروژه را با قواعد تشخیص می‌دهد و از مولدهای داخلی برای ساخت صحنه، مسیرها و اشیای پایه استفاده می‌کند. این سیستم مولد قاعده‌محور است، نه یک مدل زبانی آزاد.</p>'+
      '<div class="field"><label>ایدهٔ بازی</label><textarea id="offlineNitroPrompt" rows="5" placeholder="یک بتل‌بیس علمی‌تخیلی با اتاق فرماندهی، دشمن آموزشی و دو هدف بساز..."></textarea></div>'+
      '<div class="row"><button class="primary" onclick="MonnOffline.generate()">ساخت بازی از روی ایده</button><button onclick="newProject()">قالب‌های آماده</button></div><div id="offlineNitroResult" class="choice-card">نیترو آماده است.</div>',"760px");
  };
  window.MonnOffline.generate=async function(){
    const out=$("offlineNitroResult");out.textContent="در حال ساخت با الگوریتم‌های داخلی...";
    try{
      const result=await postJSON("/api/nitro/offline",{prompt:$("offlineNitroPrompt").value});
      project=result.project;
      if(typeof ensureProjectShape==="function")ensureProjectShape();
      active=project.meta.start_scene;
      if(typeof render==="function")render();
      if(typeof persist==="function")persist();
      out.textContent="بازی ساخته شد: "+result.project.meta.title+" · "+result.project.scenes.length+" صحنه · "+((result.project.world3d||{}).objects||[]).length+" شیء سه‌بعدی. برای نگهداری دائمی از «ذخیره پروژه» استفاده کن.";
      toast("نیترو آفلاین بازی را ساخت.");
    }catch(error){out.textContent="خطا: "+error.message;}
  };
  const oldSave=window.saveMonn;
  window.saveMonn=function(){if(projectFolderId)return window.MonnOffline.save();return oldSave();};
  window.accountAction=async function(action){
    const status=$("authStatus"),username=$("authUser").value.trim(),password=$("authPass").value;
    if(!username||!password){status.textContent="نام کاربری و گذرواژه را وارد کن.";return;}
    status.textContent="در حال اتصال به حساب محلی...";
    try{
      const result=await postJSON("/api/auth/"+action,{username,password});
      localStorage.setItem("monn-auth-token",result.token);
      status.textContent="ورود موفق: "+result.username;
      toast(action==="register"?"حساب محلی ساخته شد.":"وارد حساب شدی.");
    }catch(error){status.textContent=error.message;toast("خطای حساب: "+error.message);}
  };
  window.apiJSON=postJSON;
  // Prevent the browser's Google/Chrome context menu and show Monn's own menu.
  const menu=document.createElement("div");
  menu.id="monn-context-menu";
  menu.style.cssText="position:fixed;z-index:99999;display:none;min-width:210px;padding:7px;background:#101b2d;border:1px solid #42d7e8;border-radius:12px;box-shadow:0 16px 44px #000b;color:#e9f1ff";
  document.body.appendChild(menu);
  function hideMenu(){menu.style.display="none";}
  document.addEventListener("click",hideMenu,true);
  document.addEventListener("keydown",e=>{if(e.key==="Escape")hideMenu();});
  document.addEventListener("contextmenu",e=>{
    e.preventDefault();e.stopPropagation();
    const target=e.target,insideCanvas=!!target.closest("#canvas,.world3d-viewport,.designer-canvas");
    const actions=insideCanvas?[
      ["افزودن صحنه","addScene()"],["چیدمان خودکار","autoLayout()"],["نمایش همه صحنه‌ها","fitCanvas()"],["پروژهٔ جدید","newProject()"]
    ]:[
      ["پروژهٔ جدید","newProject()"],["ساخت بازی با نیترو آفلاین","openNitro()"],["ذخیرهٔ پروژه","saveMonn()"],["پیش‌نمایش بازی","preview()"]
    ];
    menu.innerHTML=actions.map(([label,call])=>'<button style="display:block;width:100%;margin:3px 0;text-align:right;background:#182941" onclick="'+call+';document.getElementById(\'monn-context-menu\').style.display=\'none\'">'+label+'</button>').join("");
    menu.style.display="block";
    const x=Math.min(e.clientX,innerWidth-230),y=Math.min(e.clientY,innerHeight-menu.offsetHeight-12);
    menu.style.left=Math.max(8,x)+"px";menu.style.top=Math.max(8,y)+"px";
  },true);
})();
