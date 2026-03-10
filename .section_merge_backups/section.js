(function(){
  if(window.__FF_LOADED__)return;
  window.__FF_LOADED__=true;
  const FF_DEFAULTS={gratitudeWall:true,superlatives:true,wishJar:true,songDedications:true,moodBoard:true,timeCapsule:true,memoryMosaic:false};
  const STICKY_COLORS=[{bg:'rgba(0,255,200,.08)',text:'#00ffc8',border:'#00ffc8'},{bg:'rgba(180,100,255,.08)',text:'#c87aff',border:'#c87aff'},{bg:'rgba(255,200,0,.08)',text:'#ffd700',border:'#ffd700'},{bg:'rgba(0,180,255,.08)',text:'#00b4ff',border:'#00b4ff'},{bg:'rgba(255,80,160,.08)',text:'#ff50a0',border:'#ff50a0'},{bg:'rgba(80,255,120,.08)',text:'#50ff78',border:'#50ff78'}];
  const MOOD_DATA=[{key:'happy',emoji:'😄',label:'Excited',color:'#FFD700'},{key:'proud',emoji:'🥲',label:'Proud',color:'#A8E6CF'},{key:'nostalgic',emoji:'🌅',label:'Nostalgic',color:'#FFB347'},{key:'thankful',emoji:'🙏',label:'Grateful',color:'#DDA0DD'},{key:'bittersweet',emoji:'💛',label:'Bittersweet',color:'#FFE66D'},{key:'nervous',emoji:'😬',label:'Nervous',color:'#74B9FF'}];
  const WISH_ICONS={dream:'🌟',advice:'💡',hope:'🕊️',funny:'😂'};
  const DEFAULT_SUPERLATIVES=[{id:1,emoji:'😂',title:'Class Clown',nominees:[]},{id:2,emoji:'📚',title:'Most Likely to Be Famous',nominees:[]},{id:3,emoji:'💼',title:'Future CEO',nominees:[]},{id:4,emoji:'🌍',title:'Most Likely to Travel the World',nominees:[]},{id:5,emoji:'😊',title:'Best Smile',nominees:[]},{id:6,emoji:'🎨',title:'Most Creative',nominees:[]},{id:7,emoji:'🏃',title:'Most Athletic',nominees:[]},{id:8,emoji:'🤝',title:'Most Likely to Change the World',nominees:[]}];
  function ffEsc(t){const d=document.createElement('div');d.textContent=String(t??'');return d.innerHTML}
  function ffAttr(t){return String(t??'').replace(/"/g,'&quot;')}
  function ffAgo(s){const sec=Math.floor((Date.now()-new Date(s))/1000);if(sec<60)return'just now';if(sec<3600)return`${Math.floor(sec/60)}m ago`;if(sec<86400)return`${Math.floor(sec/3600)}h ago`;return`${Math.floor(sec/86400)}d ago`}
  function ffNotify(t,title,msg){if(typeof showNotification==='function')showNotification(t,title,msg)}
  function ffApi(p){if(typeof apiUrl==='function')return apiUrl(p);const b=(window.CONFIG&&window.CONFIG.API_BASE)?window.CONFIG.API_BASE.replace(/\/$/,''):'';return b+(p.startsWith('/')?p:'/'+p)}
  async function ffGet(p){const r=await fetch(ffApi(p));return r.json()}
  async function ffPost(p,body){const r=await fetch(ffApi(p),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});return r.json()}
  async function loadFunFeatureToggles(){
    let t=Object.assign({},FF_DEFAULTS);
    try{const d=await ffGet('/api/fun/settings');if(d.success&&d.settings)t=Object.assign(t,d.settings)}catch(_){}
    window.__FF_TOGGLES__=t;applyFunFeatureToggles(t);return t;
  }
  function applyFunFeatureToggles(t){
    const map={gratitudeWall:'gratitudeWall',superlatives:'superlativesSection',wishJar:'wishJarSection',songDedications:'songDedicationsSection',moodBoard:'moodBoardSection',timeCapsule:'timeCapsuleSection',memoryMosaic:'memoryMosaicSection'};
    for(const[k,id]of Object.entries(map)){const el=document.getElementById(id);if(!el)continue;el.classList.toggle('ff-section-hidden',!t[k])}
  }
  async function loadGratitudeNotes(){
    const g=document.getElementById('gratitudeGrid');if(!g)return;
    try{const d=await ffGet('/api/fun/gratitude');if(d.success&&d.notes?.length){g.innerHTML=d.notes.map((n,i)=>{const c=STICKY_COLORS[i%STICKY_COLORS.length];const r=((i*7+3)%5)-2;return`<div class="sticky-note" style="background:${c.bg};color:${c.text};--r:${r}deg;border:1px solid ${c.border};box-shadow:0 0 18px ${c.border}44,inset 0 0 8px ${c.border}11;backdrop-filter:blur(12px);"><div class="s-from" style="color:${c.border};text-shadow:0 0 8px ${c.border};">From: ${ffEsc(n.from||n.from_name||'Anonymous')}</div><div class="s-to" style="color:${c.text}88;">For ${ffEsc(n.to||n.to_name||'Everyone')}</div><div class="s-msg">${ffEsc(n.message)}</div><div class="s-heart" style="filter:drop-shadow(0 0 6px ${c.border});">⬡</div></div>`}).join('')}else g.innerHTML='<div class="ff-empty">No sticky notes yet — be first! 💛</div>'}
    catch(_){g.innerHTML='<div class="ff-empty">No sticky notes yet — be first! 💛</div>'}
  }
  window.submitGratitudeNote=async function(){
    const from=document.getElementById('gwFrom')?.value?.trim();const to=document.getElementById('gwTo')?.value?.trim();const msg=document.getElementById('gwMsg')?.value?.trim();
    if(!from)return ffNotify('error','Missing','Please enter your name.');
    if(!to)return ffNotify('error','Missing','Who is this note for?');
    if(!msg)return ffNotify('error','Missing','Write something kind!');
    try{const d=await ffPost('/api/fun/gratitude',{from,to,message:msg});if(d.success){document.getElementById('gwFrom').value='';document.getElementById('gwTo').value='';document.getElementById('gwMsg').value='';ffNotify('success','Posted!','Your sticky note is on the wall 📌');if(typeof triggerConfetti==='function')triggerConfetti();loadGratitudeNotes()}else ffNotify('error','Failed',d.error)}
    catch(e){ffNotify('error','Error',e.message)}
  };
  let supData=[];
  async function loadSuperlatives(){
    const g=document.getElementById('superlativesGrid');if(!g)return;
    try{const d=await ffGet('/api/fun/superlatives');supData=(d.success&&d.categories)?d.categories:DEFAULT_SUPERLATIVES}catch(_){supData=DEFAULT_SUPERLATIVES}
    renderSuperlatives();
  }
  function renderSuperlatives(){
    const g=document.getElementById('superlativesGrid');if(!g)return;
    g.innerHTML=supData.map(cat=>{const noms=cat.nominees||[];const max=Math.max(1,...noms.map(n=>n.votes||0));
      return`<div class="superlative-card"><span class="superlative-emoji">${ffEsc(cat.emoji)}</span><div class="superlative-title">${ffEsc(cat.title)}</div><div class="superlative-nominee-list">${noms.length?noms.map(n=>`<div class="nominee-row" onclick="voteSuperlative(${cat.id},'${ffAttr(n.id||n.name)}')"><div><div class="nominee-name">${ffEsc(n.name)}</div><div class="nominee-bar" style="width:${Math.round((n.votes||0)/max*100)}%"></div></div><div class="nominee-votes">${n.votes||0} votes</div></div>`).join(''):'<div style="color:rgba(255,255,255,.35);font-size:.85rem;">No nominees yet. Add one!</div>'}</div><div class="superlative-add-form"><input class="ff-input" id="supAdd-${cat.id}" placeholder="Add a classmate..." maxlength="60"/><button class="ff-submit-btn" style="padding:10px 14px;margin-top:0;" type="button" onclick="addSuperlativeNominee(${cat.id})">+</button></div></div>`
    }).join('')
  }
  window.addSuperlativeNominee=async function(catId){
    const inp=document.getElementById(`supAdd-${catId}`);const name=inp?.value?.trim();if(!name)return;
    try{const d=await ffPost('/api/fun/superlatives/nominee',{categoryId:catId,name});if(d.success){inp.value='';loadSuperlatives()}else ffNotify('error','Failed',d.error)}
    catch(_){const cat=supData.find(c=>c.id===catId);if(cat){cat.nominees=cat.nominees||[];cat.nominees.push({id:Date.now(),name,votes:0});renderSuperlatives();inp.value=''}}
  };
  window.voteSuperlative=async function(catId,nomineeId){
    const voted=JSON.parse(localStorage.getItem('superlativeVotes')||'{}');
    if(voted[catId])return ffNotify('info','Already voted!','You already voted in this category.');
    try{const d=await ffPost('/api/fun/superlatives/vote',{categoryId:catId,nomineeId});if(d.success){voted[catId]=nomineeId;localStorage.setItem('superlativeVotes',JSON.stringify(voted));loadSuperlatives()}else ffNotify('error','Failed',d.error)}
    catch(_){const cat=supData.find(c=>c.id===catId);const nom=cat?.nominees?.find(n=>(n.id||n.name)==nomineeId);if(nom){nom.votes=(nom.votes||0)+1;voted[catId]=nomineeId;localStorage.setItem('superlativeVotes',JSON.stringify(voted));renderSuperlatives()}}
  };
  async function loadWishes(){
    const s=document.getElementById('wishesScroll');if(!s)return;
    try{const d=await ffGet('/api/fun/wishes');if(d.success&&d.wishes?.length){s.innerHTML=d.wishes.map(w=>`<div class="wish-item"><div class="wish-author">${WISH_ICONS[w.category]||'✨'} ${ffEsc(w.name||'Anonymous')} · ${ffAgo(w.created_at||w.createdAt)}</div><div class="wish-text">${ffEsc(w.text)}</div></div>`).join('')}else s.innerHTML='<div class="ff-empty">The jar is empty. Be first! 🫙</div>'}
    catch(_){s.innerHTML='<div class="ff-empty">The jar is empty. Be first! 🫙</div>'}
  }
  window.submitWish=async function(){
    const name=document.getElementById('wishName')?.value?.trim()||'Anonymous';const category=document.getElementById('wishCategory')?.value||'dream';const text=document.getElementById('wishText')?.value?.trim();
    if(!text)return ffNotify('error','Empty','Write your wish first!');
    try{const d=await ffPost('/api/fun/wishes',{name,category,text});if(d.success){document.getElementById('wishText').value='';ffNotify('success','Dropped!','Your wish is in the jar ✨');loadWishes()}else ffNotify('error','Failed',d.error)}
    catch(e){ffNotify('error','Error',e.message)}
  };
  async function loadDedications(){
    const l=document.getElementById('dedicationsList');if(!l)return;
    try{const d=await ffGet('/api/fun/dedications');if(d.success&&d.dedications?.length){l.innerHTML=d.dedications.map(d=>`<div class="dedication-card"><div class="dedication-vinyl">🎵</div><div class="dedication-content"><div class="dedication-song">${ffEsc(d.song)}</div>${d.message?`<div class="dedication-msg">"${ffEsc(d.message)}"</div>`:''}<div class="dedication-meta">From <strong>${ffEsc(d.from||d.from_name)}</strong> → To <strong>${ffEsc(d.to||d.to_name)}</strong> · ${ffAgo(d.created_at||d.createdAt)}</div></div></div>`).join('')}else l.innerHTML='<div class="ff-empty">No dedications yet. Be first! 🎵</div>'}
    catch(_){l.innerHTML='<div class="ff-empty">No dedications yet. Be first! 🎵</div>'}
  }
  window.submitDedication=async function(){
    const from=document.getElementById('dedFrom')?.value?.trim();const to=document.getElementById('dedTo')?.value?.trim();const song=document.getElementById('dedSong')?.value?.trim();const message=document.getElementById('dedMsg')?.value?.trim();
    if(!from)return ffNotify('error','Missing','Enter your name.');
    if(!to)return ffNotify('error','Missing','Who is this for?');
    if(!song)return ffNotify('error','Missing','Enter a song name.');
    try{const d=await ffPost('/api/fun/dedications',{from,to,song,message});if(d.success){['dedFrom','dedTo','dedSong','dedMsg'].forEach(id=>{const el=document.getElementById(id);if(el)el.value=''});ffNotify('success','Dedicated!','Your song has been dedicated 🎵');loadDedications()}else ffNotify('error','Failed',d.error)}
    catch(e){ffNotify('error','Error',e.message)}
  };
  let moodData={};
  async function loadMoodBoard(){
    try{const d=await ffGet('/api/fun/mood');if(d.success&&d.votes)moodData=d.votes}catch(_){}
    renderMoodBoard();
  }
  function renderMoodBoard(){
    const opts=document.getElementById('moodOptions');const bars=document.getElementById('moodBars');if(!opts||!bars)return;
    const myVote=localStorage.getItem('moodVote');const total=Object.values(moodData).reduce((s,v)=>s+v,0)||1;
    opts.innerHTML=MOOD_DATA.map(m=>`<button class="mood-btn ${myVote===m.key?'voted':''}" type="button" onclick="voteMood('${m.key}')"><span class="mood-emoji">${m.emoji}</span><span class="mood-label">${m.label}</span><span class="mood-count">${moodData[m.key]||0}</span></button>`).join('');
    bars.innerHTML=MOOD_DATA.map(m=>{const pct=Math.round(((moodData[m.key]||0)/total)*100);return`<div class="mood-bar-row"><div style="text-align:right;font-size:.9rem;">${m.emoji} ${m.label}</div><div class="mood-bar-bg"><div class="mood-bar-fill" style="width:${pct}%;background:linear-gradient(90deg,${m.color},${m.color}aa)"></div></div><div style="font-size:.82rem;color:var(--primary-gold);text-align:left;">${pct}%</div></div>`}).join('')
  }
  window.voteMood=async function(key){
    if(localStorage.getItem('moodVote'))return ffNotify('info','Already voted','You already shared your mood! 😊');
    moodData[key]=(moodData[key]||0)+1;localStorage.setItem('moodVote',key);renderMoodBoard();
    try{await ffPost('/api/fun/mood',{mood:key})}catch(_){}
    ffNotify('success','Vibe noted!','Your mood has been added 🌈');
  };
  async function loadTimeCapsules(){
    const list=document.getElementById('capsuleSealedList');if(!list)return;
    const ri=document.getElementById('capsuleRevealDate');if(ri&&!ri.value){const d=new Date();d.setFullYear(d.getFullYear()+1);ri.value=d.toISOString().split('T')[0]}
    try{const d=await ffGet('/api/fun/capsules');if(d.success&&d.capsules?.length){list.innerHTML=d.capsules.map(c=>`<div class="capsule-sealed-item"><div class="capsule-lock">📮</div><div><div class="capsule-from">${ffEsc(c.name)}</div><div class="capsule-open">Opens ${new Date(c.reveal_date||c.revealDate).toLocaleDateString('en-IN',{year:'numeric',month:'long',day:'numeric'})}</div></div></div>`).join('')}else list.innerHTML=''}
    catch(_){}
  }
  window.submitTimeCapsule=async function(){
    const name=document.getElementById('capsuleName')?.value?.trim();const revealDate=document.getElementById('capsuleRevealDate')?.value;const letter=document.getElementById('capsuleLetter')?.value?.trim();
    if(!name)return ffNotify('error','Missing','Enter your name.');
    if(!revealDate)return ffNotify('error','Missing','Pick a reveal date.');
    if(!letter||letter.length<20)return ffNotify('error','Too short','Write at least 20 characters.');
    if(new Date(revealDate)<=new Date())return ffNotify('error','Date in past','Choose a future date!');
    try{const d=await ffPost('/api/fun/capsules',{name,revealDate,letter});if(d.success){['capsuleName','capsuleLetter'].forEach(id=>{const el=document.getElementById(id);if(el)el.value=''});ffNotify('success','Sealed!','Your time capsule is locked 📮');if(typeof triggerConfetti==='function')triggerConfetti();loadTimeCapsules()}else ffNotify('error','Failed',d.error)}
    catch(e){ffNotify('error','Error',e.message)}
  };
  function loadMemoryMosaic(){
    const g=document.getElementById('mosaicGrid');if(!g)return;
    const memories=(window.state&&window.state.memories)||[];const map={};
    memories.forEach(m=>{const n=(m.student_name||'').trim();if(n)map[n]=(map[n]||0)+1});
    const entries=Object.entries(map).sort((a,b)=>b[1]-a[1]);
    if(!entries.length){g.innerHTML='<div class="ff-empty">No memories uploaded yet.</div>';return}
    const maxC=entries[0][1];
    g.innerHTML=entries.map(([name,count])=>{const ini=name.split(/\s+/).slice(0,2).map(x=>x[0]||'').join('').toUpperCase();return`<div class="mosaic-tile"><div class="mosaic-avatar">${ffEsc(ini)}</div><div class="mosaic-name" title="${ffAttr(name)}">${ffEsc(name)}</div><div class="mosaic-count">${count} ${count===1?'memory':'memories'}</div><div class="mosaic-bar" style="width:${Math.round(count/maxC*100)}%"></div></div>`}).join('')
  }
  function buildFunFeaturesPanel(){
    const panel=document.getElementById('panelFunFeatures');if(!panel)return;
    const t=window.__FF_TOGGLES__||FF_DEFAULTS;
    const features=[{key:'gratitudeWall',name:'🌟 Gratitude Wall',desc:'Students post sticky note thank-you messages'},{key:'superlatives',name:'🏆 Class Superlatives',desc:'Students nominate and vote for classmates'},{key:'wishJar',name:'🫙 Wish Jar',desc:'Students drop dreams, hopes and advice'},{key:'songDedications',name:'🎵 Song Dedications',desc:'Students dedicate songs to friends'},{key:'moodBoard',name:'🌈 Mood Board',desc:'Students vote on how they feel about Farewell'},{key:'timeCapsule',name:'📮 Time Capsule',desc:'Students write sealed letters to their future selves'},{key:'memoryMosaic',name:'🎨 Memory Mosaic',desc:'Auto leaderboard of top memory contributors'}];
    panel.innerHTML=`<div class="stat-card" style="text-align:left;"><div style="display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:18px;"><h3 style="font-family:var(--font-display);color:var(--primary-gold);font-size:1.3rem;">Fun Features</h3><div style="display:flex;gap:10px;flex-wrap:wrap;"><button class="admin-btn admin-btn-primary" type="button" onclick="saveFunFeatureToggles()">Save Changes</button><button class="admin-btn admin-btn-secondary" type="button" onclick="enableAllFunFeatures()">Enable All</button><button class="admin-btn admin-btn-secondary" type="button" onclick="disableAllFunFeatures()">Disable All</button></div></div><p style="font-size:.85rem;color:rgba(255,255,255,.5);margin-bottom:18px;">Toggle each section on or off for students.</p>${features.map(f=>`<div class="ff-feature-row"><div class="ff-feature-info"><div class="ff-feature-name">${f.name}</div><div class="ff-feature-desc">${f.desc}</div></div><label class="ff-toggle"><input type="checkbox" id="ffToggle_${f.key}" ${t[f.key]?'checked':''} onchange="previewFunFeatureToggle('${f.key}',this.checked)"/><span class="ff-toggle-slider"></span></label></div>`).join('')}</div>`;
  }
  window.previewFunFeatureToggle=function(key,val){const t=window.__FF_TOGGLES__||{};t[key]=val;window.__FF_TOGGLES__=t;applyFunFeatureToggles(t)};
  window.saveFunFeatureToggles=async function(){
    const t=window.__FF_TOGGLES__||FF_DEFAULTS;
    try{const res=await fetch(ffApi('/api/fun/settings'),{method:'POST',headers:{'Content-Type':'application/json','Authorization':'Bearer '+(window.state?.adminToken||'')},body:JSON.stringify({settings:t})});const d=await res.json();if(d.success)ffNotify('success','Saved','Fun feature settings updated.');else ffNotify('error','Failed',d.error||'Could not save.')}catch(e){ffNotify('error','Error',e.message)}
  };
  window.enableAllFunFeatures=function(){['gratitudeWall','superlatives','wishJar','songDedications','moodBoard','timeCapsule','memoryMosaic'].forEach(k=>{const el=document.getElementById(`ffToggle_${k}`);if(el)el.checked=(k!=='memoryMosaic');window.previewFunFeatureToggle(k,k!=='memoryMosaic')})};
  window.disableAllFunFeatures=function(){['gratitudeWall','superlatives','wishJar','songDedications','moodBoard','timeCapsule','memoryMosaic'].forEach(k=>{const el=document.getElementById(`ffToggle_${k}`);if(el)el.checked=false;window.previewFunFeatureToggle(k,false)})};
  const _origBuildAdminPanels=window.buildAdminPanels;
  window.buildAdminPanels=function(){if(typeof _origBuildAdminPanels==='function')_origBuildAdminPanels.apply(this,arguments);buildFunFeaturesPanel()};
  const _origSwitchAdminTab=window.switchAdminTab;
  window.switchAdminTab=function(tab){if(typeof _origSwitchAdminTab==='function')_origSwitchAdminTab.apply(this,arguments);const tabEl=document.getElementById('tabFunFeatures');const panelEl=document.getElementById('panelFunFeatures');if(tabEl)tabEl.classList.toggle('active',tab==='funFeatures');if(panelEl){panelEl.classList.toggle('active',tab==='funFeatures');if(tab==='funFeatures')buildFunFeaturesPanel()}};
  async function init(){
    await loadFunFeatureToggles();
    loadGratitudeNotes();loadSuperlatives();loadWishes();loadDedications();loadMoodBoard();loadTimeCapsules();
    
  }
  if(document.readyState==='loading'){document.addEventListener('DOMContentLoaded',init)}else{init()}
})();
