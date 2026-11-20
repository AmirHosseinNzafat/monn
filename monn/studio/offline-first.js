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
    const headers={"Content-Type":"application/json"};const token=localStorage.getItem("monn-auth-token");if(token)headers.Authorization="Bearer "+token;const response=await fetch(path,{method:"POST",headers,body:JSON.stringify(data)});
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
  window.openAccount=function(){
    modal("حساب محلی Monn",'<p class="muted">حساب روی همین رایانه ذخیره می‌شود. نام کاربری فارسی یا انگلیسی و گذرواژهٔ حداقل ۸ نویسه قابل قبول است.</p>'+
      '<div class="field"><label>نام کاربری (۳ تا ۳۲ نویسه)</label><input id="authUser" autocomplete="username" placeholder="نام کاربری"></div>'+
      '<div class="field"><label>گذرواژه (حداقل ۸ نویسه)</label><input id="authPass" type="password" autocomplete="current-password" placeholder="گذرواژه"></div>'+
      '<div class="row"><button class="primary" onclick="accountAction(\'login\')">ورود</button><button onclick="accountAction(\'register\')">ساخت حساب</button></div>'+
      '<button class="danger" style="margin-top:12px" onclick="accountLogout()">خروج از حساب</button><p class="muted" id="authStatus"></p>',"520px");
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

  window.MonnOffline.openTemplate=async function(key){
    try{
      const result=await postJSON("/api/nitro/offline",{template:key,prompt:""});
      project=result.project;
      if(typeof ensureProjectShape==="function")ensureProjectShape();
      active=project.meta.start_scene;
      if(typeof render==="function")render();
      if(typeof persist==="function")persist();
      try{localStorage.setItem("monn-welcome-seen","1")}catch(_){}
      closePreview();
      toast("قالب آماده بارگذاری شد: "+project.meta.title);
    }catch(error){toast("بارگذاری قالب ناموفق بود: "+error.message);}
  };
  window.MonnOffline.startBlank=function(){
    project={meta:{id:"my-monn-game",title:"بازی تازه من",start_scene:"start"},ui:{menu_enabled:true,start_label:"شروع بازی",settings_label:"تنظیمات",show_health:true,show_inventory:true,show_quests:true,elements:[]},player:{health:100,max_health:100,stats:{امتیاز:0},inventory:[]},characters:[],quests:[],assets:[],scenes:[{id:"start",title:"شروع بازی",text:"به پروژهٔ تازه‌ات خوش آمدی. از پنل سمت راست متن و انتخاب‌ها را بساز.",choices:[{id:"next",text:"رفتن به صحنهٔ بعد",target:"end",conditions:[],effects:[]}]},{id:"end",title:"پایان نمونه",text:"این صحنه را با داستان خودت جایگزین کن.",choices:[]}],world:{enabled:false,width:960,height:540,sprites:[],player:{x:40,y:40,width:28,height:40,speed:3,color:"#42d7e8"}},world3d:{enabled:false,objects:[],player:{position:[0,1,6],camera_mode:"third_person",camera_distance:7,speed:5,sensitivity:.2},lighting:{ambient:.45,directional:.9,direction:[-.5,-1,-.3]}}};
    if(typeof ensureProjectShape==="function")ensureProjectShape();
    active="start";if(typeof render==="function")render();if(typeof persist==="function")persist();
    try{localStorage.setItem("monn-welcome-seen","1")}catch(_){}
    closePreview();toast("پروژهٔ خالی آماده است.");
  };
  function showWelcome(){
    if(localStorage.getItem("monn-welcome-seen")==="1")return;
    modal("به Monn Studio خوش آمدی",'<p class="muted">برای اینکه با صفحهٔ خالی شروع نکنی، یکی از پروژه‌های آماده را باز کن. همهٔ قالب‌ها سبک‌اند و بدون اینترنت یا مدل هوش مصنوعی ساخته می‌شوند.</p>'+
      '<div class="grid" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:10px">'+
      '<div class="choice-card"><b>نامه‌ای زیر باران</b><p class="muted">داستان عاشقانهٔ تصویری با چند انتخاب و دو پایان</p><button class="primary" onclick="MonnOffline.openTemplate(\'romance_short\')">باز کردن داستان</button></div>'+
      '<div class="choice-card"><b>کارگاه شماره ۷</b><p class="muted">پروژهٔ متوسط با محیط صنعتی، مدل‌های هندسی و نور</p><button class="primary" onclick="MonnOffline.openTemplate(\'workshop_medium\')">باز کردن کارگاه</button></div>'+
      '<div class="choice-card"><b>پایگاه نبرد</b><p class="muted">پایگاه سه‌بعدی، دشمن آموزشی و هدف تمرینی</p><button class="primary" onclick="MonnOffline.openTemplate(\'battle_base\')">باز کردن بتل‌بیس</button></div>'+
      '<div class="choice-card"><b>ماجراجویی تازه</b><p class="muted">قالب سبک برای ساخت بازی از صفر</p><button class="primary" onclick="MonnOffline.openTemplate(\'starter\')">باز کردن پروژه</button></div></div>'+
      '<div class="row" style="margin-top:12px"><button onclick="MonnOffline.startBlank()">شروع از صفحهٔ خالی</button><button onclick="localStorage.setItem(\'monn-welcome-seen\',\'1\');closePreview()">فعلاً نه</button></div>',"900px");
  }
  window.addEventListener("load",function(){try{showWelcome()}catch(error){console.error("Monn welcome:",error)}},{once:true});

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
