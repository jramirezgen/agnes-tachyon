(function(){const t=document.createElement("link").relList;if(t&&t.supports&&t.supports("modulepreload"))return;for(const i of document.querySelectorAll('link[rel="modulepreload"]'))s(i);new MutationObserver(i=>{for(const a of i)if(a.type==="childList")for(const n of a.addedNodes)n.tagName==="LINK"&&n.rel==="modulepreload"&&s(n)}).observe(document,{childList:!0,subtree:!0});function e(i){const a={};return i.integrity&&(a.integrity=i.integrity),i.referrerPolicy&&(a.referrerPolicy=i.referrerPolicy),i.crossOrigin==="use-credentials"?a.credentials="include":i.crossOrigin==="anonymous"?a.credentials="omit":a.credentials="same-origin",a}function s(i){if(i.ep)return;i.ep=!0;const a=e(i);fetch(i.href,a)}})();class J{constructor(){this.x=0,this.y=0,this.zoom=1,this.targetX=0,this.targetY=0,this.smoothing=.1}setPosition(t,e){this.targetX=t,this.targetY=e}snapTo(t,e){this.x=t,this.y=e,this.targetX=t,this.targetY=e}update(){this.x+=(this.targetX-this.x)*this.smoothing,this.y+=(this.targetY-this.y)*this.smoothing}apply(t){t.setTransform(this.zoom,0,0,this.zoom,-this.x*this.zoom,-this.y*this.zoom)}screenToWorld(t,e){return{x:t/this.zoom+this.x,y:e/this.zoom+this.y}}}class Z{constructor(t,e,s,i){this.layers=[],this.animationId=null,this.lastTime=0,this.scale=i,this.canvas=document.createElement("canvas"),this.canvas.width=e,this.canvas.height=s,this.canvas.style.imageRendering="pixelated",this.canvas.style.width=`${e*i}px`,this.canvas.style.height=`${s*i}px`;const a=this.canvas.getContext("2d");if(!a)throw new Error("Could not get 2D context");this.ctx=a,this.ctx.imageSmoothingEnabled=!1,this.camera=new J,t.appendChild(this.canvas)}addLayer(t){this.layers.push(t),this.layers.sort((e,s)=>e.order-s.order)}removeLayer(t){this.layers=this.layers.filter(e=>e!==t)}start(){this.lastTime=performance.now();const t=e=>{const s=(e-this.lastTime)/1e3;this.lastTime=e,this.render(s),this.animationId=requestAnimationFrame(t)};this.animationId=requestAnimationFrame(t)}stop(){this.animationId!==null&&(cancelAnimationFrame(this.animationId),this.animationId=null)}render(t){const{ctx:e,canvas:s}=this;e.setTransform(1,0,0,1,0,0),e.clearRect(0,0,s.width,s.height),this.camera.update(),this.camera.apply(e);for(const i of this.layers)e.save(),i.render(e,t),e.restore()}resize(t,e){this.canvas.width=t,this.canvas.height=e,this.canvas.style.width=`${t*this.scale}px`,this.canvas.style.height=`${e*this.scale}px`,this.ctx.imageSmoothingEnabled=!1}getScale(){return this.scale}screenToWorld(t,e){const s=this.canvas.getBoundingClientRect(),i=(t-s.left)/this.scale,a=(e-s.top)/this.scale;return this.camera.screenToWorld(i,a)}}class Q{constructor(t){this.walkableCache=null,this.grid=t}get height(){return this.grid.length}get width(){var t;return((t=this.grid[0])==null?void 0:t.length)??0}findPath(t,e,s,i){const a=Math.round(t),n=Math.round(e),r=Math.round(s),o=Math.round(i);if(!this.isWalkable(r,o))return[];const c=[],l=new Set,h={x:a,y:n,g:0,h:0,f:0,parent:null};for(h.h=this.heuristic(a,n,r,o),h.f=h.h,c.push(h);c.length>0;){c.sort((m,b)=>m.f-b.f);const d=c.shift(),f=`${d.x},${d.y}`;if(d.x===r&&d.y===o)return this.reconstructPath(d);l.add(f);for(const[m,b]of[[-1,0],[1,0],[0,-1],[0,1]]){const u=d.x+m,v=d.y+b,S=`${u},${v}`;if(!this.isWalkable(u,v)||l.has(S))continue;const w=d.g+1,T=c.find(M=>M.x===u&&M.y===v);if(T)w<T.g&&(T.g=w,T.f=w+T.h,T.parent=d);else{const M=this.heuristic(u,v,r,o);c.push({x:u,y:v,g:w,h:M,f:w+M,parent:d})}}}return[]}isWalkable(t,e){return t>=0&&e>=0&&e<this.height&&t<this.width&&this.grid[e][t]}getWalkableTiles(){if(this.walkableCache)return this.walkableCache;const t=[];for(let e=0;e<this.height;e++)for(let s=0;s<this.width;s++)this.grid[e][s]&&t.push({x:s,y:e});return this.walkableCache=t,t}heuristic(t,e,s,i){return Math.abs(t-s)+Math.abs(e-i)}reconstructPath(t){const e=[];let s=t;for(;s;)e.unshift({x:s.x,y:s.y}),s=s.parent;return e}}const V="";class tt{constructor(t){this.order=0,this.tileImages=new Map,this.loaded=!1,this.config=t,this.pathfinder=new Q(t.walkable)}async load(t){const e=Object.entries(this.config.tiles).map(([s,i])=>new Promise(a=>{const n=new Image;n.onload=()=>{this.tileImages.set(s,n),a()},n.onerror=()=>{a()};const r=/^(\/|blob:|data:|https?:\/\/)/.test(i);n.src=r?i:`${t}/${i}`}));await Promise.all(e),this.loaded=!0}getLocation(t){return this.config.locations[t]}getTileImages(){return this.tileImages}addTile(t,e){this.tileImages.set(t,e),this.config.tiles[t]=""}render(t,e){if(!this.loaded)return;const{tileWidth:s,tileHeight:i,layers:a}=this.config;for(const n of a)for(let r=0;r<n.length;r++)for(let o=0;o<n[r].length;o++){const c=n[r][o];if(c===V){t.fillStyle="#2a2a2e",t.fillRect(o*s,r*i,s,i);continue}const l=this.tileImages.get(c);l&&t.drawImage(l,0,0,l.naturalWidth,l.naturalHeight,o*s,r*i,s,i)}}}class H{constructor(t){this.images=new Map,this.loaded=!1,this.config=t}async load(t){const e=Object.entries(this.config.sheets).map(([s,i])=>new Promise(a=>{const n=new Image;n.onload=()=>{this.images.set(s,n),a()},n.onerror=()=>{a()};const r=/^(\/|blob:|data:|https?:\/\/)/.test(i);n.src=r?i:`${t}/${i}`}));await Promise.all(e),this.loaded=!0}getImage(t){return this.images.get(t)}isLoaded(){return this.loaded}drawFrame(t,e,s,i,a){const n=this.config.animations[e];if(!n)return;const r=this.images.get(n.sheet);if(!r)return;const{frameWidth:o,frameHeight:c}=this.config,l=s%n.frames*o,h=n.row*c;t.drawImage(r,l,h,o,c,i,a,o,c)}}class et{constructor(t,e="idle_down"){this.currentAnimation="idle_down",this.frame=0,this.elapsed=0,this.spriteSheet=t,this.currentAnimation=e}play(t){this.currentAnimation!==t&&(this.currentAnimation=t,this.frame=0,this.elapsed=0)}getCurrentAnimation(){return this.currentAnimation}update(t){const e=this.spriteSheet.config.animations[this.currentAnimation];e&&(this.elapsed+=t,this.elapsed>=e.speed&&(this.elapsed-=e.speed,this.frame=(this.frame+1)%e.frames))}draw(t,e,s){this.spriteSheet.drawFrame(t,this.currentAnimation,this.frame,e,s)}}class st{constructor(){this.map=new Map}key(t,e){return`${t},${e}`}reserve(t,e,s){const i=this.key(t,e),a=this.map.get(i);return a&&a!==s?!1:(this.map.set(i,s),!0)}release(t){for(const[e,s]of this.map)s===t&&this.map.delete(e)}isAvailable(t,e,s){const i=this.map.get(this.key(t,e));return!i||i===s}}const _={working:"working",idle:"idle_down",thinking:"idle_down",error:"idle_down",waiting:"idle_down",collaborating:"walk_down",sleeping:"sleeping",listening:"idle_down",speaking:"talking",offline:"idle_down"};class B{constructor(t,e,s,i){this.x=0,this.y=0,this.state="idle",this.task=null,this.energy=1,this.visible=!0,this.separationX=0,this.separationY=0,this.path=[],this.pathIndex=0,this.moveSpeed=2,this.moveProgress=0,this.homePosition="",this.tileWidth=16,this.tileHeight=16,this.idleBehaviorTimer=0,this.idleBehaviorInterval=5+Math.random()*5,this.currentAnchor=null,this.npcPhase="idle",this.npcPhaseTimer=0,this.npcPhaseDuration=0,this.agentId=t.agentId,this.name=t.name,this.spriteSheet=e,this.animator=new et(e),this.homePosition=t.position,this.tileWidth=s,this.tileHeight=i,this.frameWidth=e.config.frameWidth,this.frameHeight=e.config.frameHeight,this.isNpc=t.npc??!1,this.isNpc&&(this.npcPhase="idle",this.npcPhaseDuration=3+Math.random()*5)}getHomePosition(){return this.homePosition}setHomePosition(t){this.homePosition=t}setPixelPosition(t,e){this.x=t,this.y=e}setTilePosition(t,e){this.x=t*this.tileWidth,this.y=e*this.tileHeight}getTilePosition(){return{x:Math.round(this.x/this.tileWidth),y:Math.round(this.y/this.tileHeight)}}walkTo(t){t.length<=1||(this.path=t,this.pathIndex=1,this.moveProgress=0)}isMoving(){return this.pathIndex<this.path.length}updateState(t,e,s){const i=this.state;if(this.state=t,this.task=e,this.energy=s,this.visible=t!=="offline",i!==t&&!this.isMoving()){const a=_[t]??"idle_down";this.animator.play(a)}}faceDirection(t){const e=`${this.state==="idle"?"idle":"walk"}_${t}`;this.spriteSheet.config.animations[e]&&this.animator.play(e)}update(t,e,s,i,a,n){if(this.isNpc&&!this.isMoving()&&this.updateNpcPhase(t,e,i,a,n),this.isMoving())this.updateMovement(t);else if(this.state==="idle")this.updateIdleBehavior(t,e,s,i,a,n);else{const r=_[this.state]??"idle_down";this.animator.getCurrentAnimation()!==r&&this.animator.play(r)}this.animator.update(t)}updateNpcPhase(t,e,s,i,a){if(this.npcPhaseTimer+=t,this.npcPhaseTimer<this.npcPhaseDuration)return;this.npcPhaseTimer=0,this.npcPhase,this.npcPhase==="idle"?(this.npcPhase=Math.random()<.6?"working":"resting",this.npcPhaseDuration=10+Math.random()*20):(this.npcPhase="idle",this.npcPhaseDuration=5+Math.random()*10);const n=this.npcPhase==="working"?"working":this.npcPhase==="resting"?"sleeping":"idle";if(n!==this.state){let r=!1;if(s&&s.length>0)if(n==="working"){const o=this.getHomePosition();r=this.goToAnchor(o,s,e,i)||this.goToAnchorType("work",s,e,i,a)}else n==="sleeping"&&(r=this.goToAnchorType("rest",s,e,i,a));n==="idle"||r?(this.updateState(n,null,this.energy),n==="idle"&&(this.idleBehaviorTimer=this.idleBehaviorInterval)):(this.npcPhase="idle",this.npcPhaseDuration=3+Math.random()*5)}}updateMovement(t){if(this.pathIndex>=this.path.length)return;const e=this.path[this.pathIndex],s=e.x*this.tileWidth,i=e.y*this.tileHeight,a=s-this.x,n=i-this.y;if(Math.abs(a)>Math.abs(n)?this.animator.play(a>0?"walk_right":"walk_left"):this.animator.play(n>0?"walk_down":"walk_up"),this.moveProgress+=t*this.moveSpeed,this.moveProgress>=1){if(this.x=s,this.y=i,this.moveProgress=0,this.pathIndex++,this.pathIndex>=this.path.length){this.path=[],this.pathIndex=0;const r=_[this.state]??"idle_down";this.animator.play(r)}}else{const r=this.path[this.pathIndex-1],o=r.x*this.tileWidth,c=r.y*this.tileHeight;this.x=o+(s-o)*this.moveProgress,this.y=c+(i-c)*this.moveProgress}}goToAnchor(t,e,s,i){const a=e.find(o=>o.name===t);if(!a||i&&!i.isAvailable(a.x,a.y,this.agentId))return!1;const n=this.getTilePosition();if(n.x===a.x&&n.y===a.y)return i&&(i.release(this.agentId),i.reserve(a.x,a.y,this.agentId)),this.currentAnchor=a.name,!0;const r=s.findPath(n.x,n.y,a.x,a.y);return r.length>1?(i&&(i.release(this.agentId),i.reserve(a.x,a.y,this.agentId)),this.currentAnchor=a.name,this.walkTo(r),!0):!1}goToAnchorType(t,e,s,i,a){const n=e.filter(c=>c.type===t&&(!a||!a.has(c.name)));if(n.length===0)return!1;const r=[...n].sort(()=>Math.random()-.5),o=this.getTilePosition();for(const c of r){if(i&&!i.isAvailable(c.x,c.y,this.agentId))continue;if(o.x===c.x&&o.y===c.y)return i&&(i.release(this.agentId),i.reserve(c.x,c.y,this.agentId)),this.currentAnchor=c.name,!0;const l=s.findPath(o.x,o.y,c.x,c.y);if(l.length>1)return i&&(i.release(this.agentId),i.reserve(c.x,c.y,this.agentId)),this.currentAnchor=c.name,this.walkTo(l),!0}return!1}getCurrentAnchor(){return this.currentAnchor}updateIdleBehavior(t,e,s,i,a,n){if(this.idleBehaviorTimer+=t,this.idleBehaviorTimer<this.idleBehaviorInterval)return;if(this.idleBehaviorTimer=0,this.idleBehaviorInterval=5+Math.random()*8,i&&i.length>0){const c=["wander","social","utility"].filter(l=>i.some(h=>h.type===l&&(!n||!n.has(h.name)))).sort(()=>Math.random()-.5);for(const l of c)if(this.goToAnchorType(l,i,e,a,n))return}const r=Object.keys(s).sort(()=>Math.random()-.5),o=this.getTilePosition();for(const c of r){const l=s[c];if(a&&!a.isAvailable(l.x,l.y,this.agentId))continue;const h=e.findPath(o.x,o.y,l.x,l.y);if(h.length>1){a&&(a.release(this.agentId),a.reserve(l.x,l.y,this.agentId)),this.walkTo(h);return}}this.walkToRandomTile(e,a)}walkToRandomTile(t,e){const s=this.getTilePosition(),i=t.getWalkableTiles();if(i.length===0)return;const a=Math.min(10,i.length);for(let n=0;n<a;n++){const r=Math.floor(Math.random()*i.length),o=i[r];if(Math.abs(o.x-s.x)+Math.abs(o.y-s.y)<2||e&&!e.isAvailable(o.x,o.y,this.agentId))continue;const c=t.findPath(s.x,s.y,o.x,o.y);if(c.length>1){e&&(e.release(this.agentId),e.reserve(o.x,o.y,this.agentId)),this.walkTo(c);return}}}getSittingOffset(){return this.state==="working"||this.state==="sleeping"?this.tileHeight*1.2:0}isAnchored(){return this.state==="working"||this.state==="sleeping"}applySeparation(t,e){if(this.isAnchored()||!this.visible)return;const s=this.tileWidth*1.5;let i=0,a=0;for(const c of t){if(c===this||!c.visible)continue;const l=this.x-c.x,h=this.y-c.y,d=Math.sqrt(l*l+h*h);if(d<s&&d>.01){const f=(s-d)/s;i+=l/d*f,a+=h/d*f}else if(d<=.01){const f=Math.random()*Math.PI*2;i+=Math.cos(f)*.5,a+=Math.sin(f)*.5}}const n=60*e;this.separationX+=i*n,this.separationY+=a*n;const r=.9;this.separationX*=r,this.separationY*=r;const o=this.tileWidth*.5;this.separationX=Math.max(-o,Math.min(o,this.separationX)),this.separationY=Math.max(-o,Math.min(o,this.separationY))}draw(t){if(!this.visible)return;const e=this.isAnchored()?0:this.separationX,s=this.isAnchored()?0:this.separationY,i=this.x+(this.tileWidth-this.frameWidth)/2+e,a=this.y+(this.tileHeight-this.frameHeight)-this.getSittingOffset()+s;this.animator.draw(t,i,a)}containsPoint(t,e){const s=this.isAnchored()?0:this.separationX,i=this.isAnchored()?0:this.separationY,a=this.x+(this.tileWidth-this.frameWidth)/2+s,n=this.y+(this.tileHeight-this.frameHeight)+i;return t>=a&&t<=a+this.frameWidth&&e>=n&&e<=n+this.frameHeight}}class it{constructor(){this.order=12,this.citizens=[]}setCitizens(t){this.citizens=t}render(t,e){const s=this.citizens.filter(i=>i.visible&&(i.state==="working"||i.state==="sleeping")).sort((i,a)=>i.y-a.y);for(const i of s)i.draw(t)}}class at{constructor(){this.order=20,this.citizens=[]}setCitizens(t){this.citizens=t}render(t,e){const s=this.citizens.filter(i=>i.visible&&i.state!=="working"&&i.state!=="sleeping").sort((i,a)=>i.y-a.y);for(const i of s)i.draw(t)}}class nt{constructor(){this.order=10,this.below=new it,this.above=new at}setCitizens(t){this.below.setCitizens(t),this.above.setCitizens(t)}getLayers(){return[this.below,this.above]}render(t,e){}}class ot{constructor(t){this.active=!1,this.shakeTimer=0,this.glowing=!1,this.displayText="",this.config=t}activate(){this.active=!0,this.shakeTimer=1}deactivate(){this.active=!1,this.shakeTimer=0}setGlow(t){this.glowing=t}setText(t){this.displayText=t}isActive(){return this.active}containsPoint(t,e){const{x:s,y:i,width:a,height:n}=this.config;return t>=s&&t<=s+a&&e>=i&&e<=i+n}update(t){this.shakeTimer>0&&(this.shakeTimer-=t,this.shakeTimer<=0&&(this.active=!1))}draw(t){const{x:e,y:s,width:i,height:a,type:n}=this.config;let r=e;const o=s;switch(this.shakeTimer>0&&(r+=Math.sin(this.shakeTimer*30)*1),this.glowing&&(t.save(),t.shadowColor="#66aaff",t.shadowBlur=4,t.fillStyle="rgba(100, 170, 255, 0.15)",t.fillRect(r-1,o-1,i+2,a+2),t.restore()),t.save(),n){case"intercom":t.fillStyle="#666666",t.fillRect(r,o,i,a),t.fillStyle="#aaaaaa",t.fillRect(r+1,o+1,i-2,a-2),this.active&&(t.fillStyle="#ff4444",t.beginPath(),t.arc(r+i/2,o+4,3,0,Math.PI*2),t.fill());break;case"whiteboard":t.fillStyle="#eeeeee",t.fillRect(r,o,i,a),t.strokeStyle="#999999",t.lineWidth=.5,t.strokeRect(r,o,i,a),this.displayText&&(t.fillStyle="#333333",t.font="8px monospace",t.fillText(this.displayText.substring(0,20),r+4,o+a/2+2));break;case"coffee_machine":t.fillStyle="#8B4513",t.fillRect(r,o,i,a),t.fillStyle="#654321",t.fillRect(r+2,o+2,i-4,a-4);break;default:t.fillStyle="#888888",t.fillRect(r,o,i,a);break}t.restore()}}class rt{constructor(){this.order=20,this.particles=[]}emitZzz(t,e){this.particles.push({x:t+Math.random()*16,y:e,vx:.3+Math.random()*.4,vy:-.8-Math.random()*.4,life:2,maxLife:2,text:"Z",size:10+Math.random()*6,alpha:1})}emitExclamation(t,e){this.particles.push({x:t,y:e-8,vx:0,vy:-.4,life:1.5,maxLife:1.5,text:"!",size:14,alpha:1})}emitThought(t,e){this.particles.push({x:t+12,y:e-4,vx:0,vy:-.3,life:2,maxLife:2,text:"...",size:10,alpha:1})}update(t){for(const e of this.particles)e.x+=e.vx*t*10,e.y+=e.vy*t*10,e.life-=t,e.alpha=Math.max(0,e.life/e.maxLife);this.particles=this.particles.filter(e=>e.life>0)}render(t,e){this.update(e);for(const s of this.particles)t.save(),t.globalAlpha=s.alpha,t.fillStyle="#ffffff",t.strokeStyle="#000000",t.lineWidth=.5,t.font=`bold ${s.size}px monospace`,t.strokeText(s.text,s.x,s.y),t.fillText(s.text,s.x,s.y),t.restore()}}class ct{constructor(){this.order=25,this.bubbles=[]}show(t,e,s,i=3,a){a?this.bubbles=this.bubbles.filter(o=>o.target!==a):this.bubbles=this.bubbles.filter(o=>!(Math.abs(o.x-t)<1&&Math.abs(o.y-e)<1));const n=a?t-a.x:0,r=a?e-a.y:0;this.bubbles.push({x:t,y:e,text:s,life:i,maxLife:i,target:a,offsetX:n,offsetY:r})}clear(){this.bubbles=[]}render(t,e){for(const s of this.bubbles)s.life-=e;this.bubbles=this.bubbles.filter(s=>s.life>0);for(const s of this.bubbles){s.target&&(s.x=s.target.x+s.offsetX,s.y=s.target.y+s.offsetY-s.target.getSittingOffset());const i=Math.min(1,s.life/.5);t.save(),t.globalAlpha=i,t.font="9px monospace";const a=t.measureText(s.text),n=Math.min(a.width,120),r=6,o=n+r*2,c=18,l=s.x-o/2,h=s.y-c-8;t.fillStyle="#ffffff",t.strokeStyle="#333333",t.lineWidth=1,t.beginPath(),t.roundRect(l,h,o,c,4),t.fill(),t.stroke(),t.beginPath(),t.moveTo(s.x-4,h+c),t.lineTo(s.x,h+c+6),t.lineTo(s.x+4,h+c),t.fill(),t.fillStyle="#333333",t.fillText(s.text.substring(0,20),l+r,h+c-5),t.restore()}}}function q(p){return p.map(t=>({id:t.id??t.agent,name:t.name??t.id??t.agent,state:t.state??"idle",task:t.task??null,energy:t.energy??1,metadata:t.metadata}))}class lt{constructor(t){this.callbacks=[],this.eventCallbacks=[],this.messageCallbacks=[],this.intervalId=null,this.ws=null,this.config=t}onUpdate(t){this.callbacks.push(t)}onEvent(t){this.eventCallbacks.push(t)}onMessage(t){this.messageCallbacks.push(t)}sendAction(t,e){this.ws&&this.ws.readyState===WebSocket.OPEN&&this.ws.send(JSON.stringify({type:"action",agent:t,action:e}))}requestObserve(t,e){this.ws&&this.ws.readyState===WebSocket.OPEN&&this.ws.send(JSON.stringify({type:"observe",agent:t,since:e}))}emit(t){for(const e of this.callbacks)e(t)}emitEvent(t){for(const e of this.eventCallbacks)e(t)}emitMessage(t){for(const e of this.messageCallbacks)e(t)}start(){switch(this.config.type){case"rest":this.startPolling();break;case"websocket":this.startWebSocket();break;case"mock":this.startMock();break}}stop(){this.intervalId&&(clearInterval(this.intervalId),this.intervalId=null),this.ws&&(this.ws.close(),this.ws=null)}async startPolling(){const t=this.config.url,e=this.config.interval??3e3,s=async()=>{try{const i=await(await fetch(t)).json();this.emit(i.agents??[])}catch{}};await s(),this.intervalId=setInterval(s,e)}startWebSocket(){const t=this.config.url;this.ws=new WebSocket(t),this.ws.onmessage=e=>{try{const s=JSON.parse(e.data);if(s.type==="agents")this.emit(q(s.agents??[]));else if(s.type==="event"&&s.event)this.emitEvent(s.event);else if(s.type==="message"&&s.from&&s.message)this.emitMessage({from:s.from,message:s.message,channel:s.channel});else if(s.type==="world"&&s.snapshot&&(s.snapshot.agents&&this.emit(q(s.snapshot.agents)),s.snapshot.events))for(const i of s.snapshot.events)this.emitEvent(i)}catch{}},this.ws.onclose=()=>{setTimeout(()=>{this.ws&&this.startWebSocket()},5e3)}}startMock(){if(!this.config.mockData)return;const t=this.config.interval??3e3;this.emit(this.config.mockData()),this.intervalId=setInterval(()=>{this.emit(this.config.mockData())},t)}}const E={desk:[{ox:.5,oy:-1,type:"work"}],chair:[],couch:[{ox:.5,oy:0,type:"rest"},{ox:1.5,oy:0,type:"rest"}],coffee_machine:[{ox:.5,oy:1.8,type:"utility"}],whiteboard:[{ox:1,oy:1.5,type:"social"}],bookshelf:[],water_cooler:[{ox:0,oy:1.8,type:"utility"}],plant:[],lamp:[]};function ht(p){if(E[p])return E[p];for(const[t,e]of Object.entries(E))if(e.length>0&&p.includes(t))return e}function N(p,t){const e=ht(p.id);return!e||e.length===0?[]:e.map((s,i)=>({...s,oy:s.oy<0?p.h+Math.abs(s.oy)-1:s.oy,name:`${p.id}_${t}_${i}`}))}class dt{constructor(t,e){this.pieces=[],this.selected=new Set,this.images=new Map,this.imageSrcs=new Map,this.dragging=!1,this.dragOffsets=new Map,this.clipboard=[],this.onSaveCallback=null,this.deadspaceCheck=null,this.tileSize=t,this.scale=e,this.wanderPoints=[{name:"wander_center",x:7,y:6},{name:"wander_lounge",x:5,y:8}]}async loadSprite(t,e){const s=await new Promise((i,a)=>{const n=new Image;n.onload=()=>i(n),n.onerror=()=>a(new Error(`Failed to load sprite: ${e}`)),n.src=e});this.images.set(t,s),this.imageSrcs.set(t,e)}getImageSrcs(){return this.imageSrcs}getTileSize(){return this.tileSize}getScale(){return this.scale}setLayout(t){this.pieces=t.map((e,s)=>({...e,img:this.images.get(e.id),anchors:e.anchors??N(e,s)})).filter(e=>e.img)}getLayout(){return this.pieces.map(({id:t,x:e,y:s,w:i,h:a,layer:n,anchors:r})=>({id:t,x:e,y:s,w:i,h:a,layer:n,anchors:r.length>0?r:void 0}))}getLocations(){const t=[];for(const e of this.pieces)for(const s of e.anchors)t.push({name:s.name,x:Math.round(e.x+s.ox),y:Math.round(e.y+s.oy),type:s.type});for(const e of this.wanderPoints)t.push({name:e.name,x:e.x,y:e.y,type:"wander"});return t}getLocationMap(){const t={};for(const e of this.getLocations())t[e.name]={x:e.x,y:e.y,label:e.name};return t}onSave(t){this.onSaveCallback=t}setDeadspaceCheck(t){this.deadspaceCheck=t}occupiesTile(t,e){for(const s of this.pieces)if(t>=Math.floor(s.x)&&t<Math.ceil(s.x+s.w)&&e>=Math.floor(s.y)&&e<Math.ceil(s.y+s.h))return!0;return!1}overlapsDeadspace(t,e,s,i){if(!this.deadspaceCheck)return!1;const a=Math.floor(t),n=Math.floor(e),r=Math.ceil(t+s),o=Math.ceil(e+i);for(let c=n;c<o;c++)for(let l=a;l<r;l++)if(this.deadspaceCheck(l,c))return!0;return!1}getBlockedTiles(){const t=new Set;for(const e of this.pieces){const s=Math.floor(e.x),i=Math.floor(e.y),a=Math.ceil(e.x+e.w),n=Math.ceil(e.y+e.h);for(let r=i;r<n;r++)for(let o=s;o<a;o++)t.add(`${o},${r}`)}return t}setWanderPoints(t){this.wanderPoints=t}save(){var t;console.log("[props] Layout updated"),(t=this.onSaveCallback)==null||t.call(this)}addPiece(t){const e=this.images.get(t);if(!e)return null;const s=e.naturalWidth/e.naturalHeight,i=2,a=Math.round(i*s*10)/10;let n=6,r=5;if(this.overlapsDeadspace(n,r,a,i)){let l=!1;for(let h=1;h<20&&!l;h++)for(let d=1;d<20&&!l;d++)this.overlapsDeadspace(d,h,a,i)||(n=d,r=h,l=!0)}const o=this.pieces.length,c={id:t,img:e,x:n,y:r,w:a,h:i,layer:t==="chair"?"above":"below",anchors:N({id:t,h:i},o)};return this.pieces.push(c),c}removePiece(t){this.pieces=this.pieces.filter(e=>e!==t),this.selected.delete(t)}renderBelow(t){t.imageSmoothingEnabled=!1;const e=this.tileSize;for(const s of this.pieces)s.layer==="below"&&t.drawImage(s.img,s.x*e,s.y*e,s.w*e,s.h*e)}renderAbove(t){t.imageSmoothingEnabled=!1;const e=this.tileSize;for(const s of this.pieces)s.layer==="above"&&t.drawImage(s.img,s.x*e,s.y*e,s.w*e,s.h*e)}handleMouseDown(t,e,s=!1){const i=this.pieceAt(t,e);if(i){s?this.selected.has(i)?this.selected.delete(i):this.selected.add(i):this.selected.has(i)||(this.selected.clear(),this.selected.add(i)),this.dragging=!0,this.dragOffsets.clear();for(const a of this.selected)this.dragOffsets.set(a,{dx:t-a.x*this.tileSize,dy:e-a.y*this.tileSize});return!0}return s||this.selected.clear(),!1}handleMouseMove(t,e){if(!this.dragging||this.selected.size===0)return;const s=this.tileSize,i=[];for(const a of this.selected){const n=this.dragOffsets.get(a);if(!n)continue;const r=this.snap((t-n.dx)/s),o=this.snap((e-n.dy)/s);if(this.overlapsDeadspace(r,o,a.w,a.h))return;i.push({piece:a,nx:r,ny:o})}for(const a of i)a.piece.x=a.nx,a.piece.y=a.ny}handleMouseUp(){this.dragging=!1}handleKey(t){if((t.metaKey||t.ctrlKey)&&t.key==="c"&&this.selected.size>0)return this.clipboard=[...this.selected].map(e=>({id:e.id,w:e.w,h:e.h,layer:e.layer,anchors:e.anchors.map(s=>({...s}))})),!0;if((t.metaKey||t.ctrlKey)&&t.key==="v"&&this.clipboard.length>0){this.selected.clear();for(const e of this.clipboard){const s=this.images.get(e.id);if(!s)continue;const i=this.pieces.length,a={id:e.id,img:s,x:4+Math.random()*2,y:4+Math.random()*2,w:e.w,h:e.h,layer:e.layer,anchors:e.anchors.map((n,r)=>({...n,name:`${e.id}_${i}_${r}`}))};this.pieces.push(a),this.selected.add(a)}return!0}if(this.selected.size===0)return!1;if(t.key==="Delete"||t.key==="Backspace"){for(const e of this.selected)this.pieces=this.pieces.filter(s=>s!==e);return this.selected.clear(),!0}if(t.key==="l"||t.key==="L"){for(const e of this.selected)e.layer=e.layer==="below"?"above":"below";return!0}if(t.key.startsWith("Arrow")){const e=t.shiftKey?1:.25;let s=0,i=0;t.key==="ArrowLeft"&&(s=-e),t.key==="ArrowRight"&&(s=e),t.key==="ArrowUp"&&(i=-e),t.key==="ArrowDown"&&(i=e);for(const a of this.selected)if(this.overlapsDeadspace(a.x+s,a.y+i,a.w,a.h))return!0;for(const a of this.selected)a.x+=s,a.y+=i;return t.preventDefault(),!0}if(t.key==="="||t.key==="+"){for(const e of this.selected)e.w+=.1,e.h+=.1;return!0}if(t.key==="-"){for(const e of this.selected)e.w=Math.max(.5,e.w-.1),e.h=Math.max(.5,e.h-.1);return!0}return!1}pieceAt(t,e){const s=this.tileSize;for(let i=this.pieces.length-1;i>=0;i--){const a=this.pieces[i],n=a.x*s,r=a.y*s,o=a.w*s,c=a.h*s;if(t>=n&&t<=n+o&&e>=r&&e<=r+c)return a}return null}snap(t){return Math.round(t*4)/4}}const R=class D{constructor(t){this.citizens=[],this.objects=[],this.eventHandlers=new Map,this.particleTimers=new Map,this.typedLocations=[],this.reservation=new st,this.spawningAgents=new Set,this.autoSpawnIndex=0,this.lastTransitionTime=new Map,this.config=t;const e=t.scale??2,s=t.width??512,i=t.height??384;this.renderer=new Z(t.container,s,i,e),this.scene=new tt(t.sceneConfig??ft()),this.citizenLayer=new nt,this.particles=new rt,this.speechBubbles=new ct,this.signal=new lt(t.signal),this.renderer.addLayer(this.scene),this.renderer.addLayer({order:5,render:(a,n)=>{for(const r of this.objects)r.update(n),r.draw(a)}});for(const a of this.citizenLayer.getLayers())this.renderer.addLayer(a);if(this.renderer.addLayer(this.particles),this.renderer.addLayer(this.speechBubbles),this.renderer.addLayer({order:30,render:a=>{for(const n of this.citizens){if(!n.visible)continue;a.save(),a.font="8px monospace",a.fillStyle="rgba(0,0,0,0.6)";const r=a.measureText(n.name).width,o=n.x+(this.scene.config.tileWidth-r)/2,c=n.y-n.spriteSheet.config.frameHeight+this.scene.config.tileHeight-4-n.getSittingOffset();a.fillRect(o-2,c-8,r+4,12),a.fillStyle="#ffffff",a.fillText(n.name,o,c),a.restore()}}}),this.signal.onUpdate(a=>this.handleSignalUpdate(a)),this.signal.onEvent(a=>{var n,r;if(((n=a.action)==null?void 0:n.type)==="message"&&(r=a.action)!=null&&r.to){const o=this.citizens.find(l=>l.agentId===a.agentId),c=this.citizens.find(l=>l.agentId===a.action.to);if(o&&c&&o!==c){const l=o.getTilePosition(),h=c.getTilePosition(),d=[[-1,0],[1,0],[0,-1],[0,1]];let f=[];for(const[m,b]of d){const u=this.scene.pathfinder.findPath(l.x,l.y,h.x+m,h.y+b);u.length>1&&(f.length===0||u.length<f.length)&&(f=u)}f.length>1&&o.walkTo(f)}}}),this.renderer.canvas.addEventListener("click",a=>this.handleClick(a)),t.objects)for(const a of t.objects)this.objects.push(new ot(a));this.renderer.addLayer({order:-1,render:(a,n)=>{const r={};for(const[o,c]of Object.entries(this.scene.config.locations))r[o]={x:c.x,y:c.y};for(const o of this.citizens){const c=this.getOtherHomeAnchors(o.agentId);o.update(n,this.scene.pathfinder,r,this.typedLocations,this.reservation,c),o.applySeparation(this.citizens,n),this.updateCitizenEffects(o,n)}}})}async start(){var t;const e=this.config.worldBasePath??`worlds/${this.config.world}`;await this.scene.load(e);for(const s of this.config.citizens){const i=((t=this.config.spriteSheets)==null?void 0:t[s.sprite])??j(s.sprite),a=new H(i);await a.load(e);const n=new B(s,a,this.scene.config.tileWidth,this.scene.config.tileHeight),r=this.scene.getLocation(s.position);if(r)n.setTilePosition(r.x,r.y);else{const o=this.typedLocations.find(c=>c.name===s.position);o&&n.setTilePosition(o.x,o.y)}this.citizens.push(n)}this.citizenLayer.setCitizens(this.citizens),this.unstickCitizens(),this.signal.start(),this.renderer.start()}unstickCitizens(){var t;const e=this.scene.config.walkable,s=e.length,i=((t=e[0])==null?void 0:t.length)??0,a=[[0,-1],[0,1],[-1,0],[1,0]],n=this.typedLocations.filter(o=>o.type==="wander"||o.type==="social"||o.type==="utility").map(o=>({x:o.x,y:o.y})),r=(o,c)=>{let l=0;for(const[h,d]of a){const f=o+h,m=c+d;f>=0&&f<i&&m>=0&&m<s&&e[m][f]&&l++}return l};for(const o of this.citizens){const c=o.getTilePosition();if(n.some(f=>this.scene.pathfinder.findPath(c.x,c.y,f.x,f.y).length>1))continue;const l=new Set,h=[{x:c.x,y:c.y}];l.add(`${c.x},${c.y}`);let d=!1;for(;h.length>0;){const f=h.shift();for(const[m,b]of a){const u=f.x+m,v=f.y+b,S=`${u},${v}`;if(!(u<0||u>=i||v<0||v>=s)&&!l.has(S)){if(l.add(S),e[v][u]&&r(u,v)>=2&&n.some(w=>this.scene.pathfinder.findPath(u,v,w.x,w.y).length>1)){o.setTilePosition(u,v),console.log(`[miniverse] Unstuck "${o.agentId}" from (${c.x},${c.y}) to (${u},${v})`),d=!0;break}h.push({x:u,y:v})}}if(d)break}}}stop(){this.renderer.stop(),this.signal.stop()}getCanvas(){return this.renderer.canvas}addLayer(t){this.renderer.addLayer(t)}on(t,e){this.eventHandlers.has(t)||this.eventHandlers.set(t,new Set),this.eventHandlers.get(t).add(e)}off(t,e){var s;(s=this.eventHandlers.get(t))==null||s.delete(e)}emit(t,e){const s=this.eventHandlers.get(t);if(s)for(const i of s)i(e)}triggerEvent(t,e){if(t==="intercom"){for(const s of this.objects)s.config.type==="intercom"&&s.activate();for(const s of this.citizens)s.visible&&s.faceDirection("down");e!=null&&e.message&&this.speechBubbles.show(this.renderer.canvas.width/(2*(this.config.scale??2)),20,String(e.message),4),this.emit("intercom",e??{})}}setTypedLocations(t){this.typedLocations=t}resizeGrid(t,e){var s;const i=this.scene.config,a=i.walkable.length,n=((s=i.walkable[0])==null?void 0:s.length)??0;if(t<4||e<4)return;for(let l=0;l<e;l++){for(l>=a&&(i.walkable[l]=new Array(t).fill(!0));i.walkable[l].length<t;)i.walkable[l].push(!0);i.walkable[l].length=t}i.walkable.length=e;const r=Object.keys(i.tiles)[0]??"floor";for(const l of i.layers){for(let h=0;h<e;h++){for(h>=l.length&&(l[h]=new Array(t).fill(r));l[h].length<t;)l[h].push(r);l[h].length=t}l.length=e;for(let h=0;h<e;h++)for(let d=0;d<t;d++)(h>=a||d>=n)&&(l[h][d]=r)}const o=i.tileWidth,c=i.tileHeight;this.renderer.resize(t*o,e*c)}getGridSize(){var t;const e=this.scene.config.walkable;return{cols:((t=e[0])==null?void 0:t.length)??0,rows:e.length}}getFloorLayer(){return this.scene.config.layers[0]}setTile(t,e,s){const i=this.scene.config.layers[0];if(e>=0&&e<i.length&&t>=0&&t<i[0].length){i[e][t]=s;const a=this.scene.config.walkable;e<a.length&&t<a[0].length&&(a[e][t]=s!=="")}}getTiles(){return this.scene.config.tiles}getTileImages(){return this.scene.getTileImages()}addTile(t,e,s){this.scene.addTile(t,e),s&&(this.scene.config.tiles[t]=s)}updateWalkability(t){var e,s,i,a;const n=this.scene.config.walkable,r=n.length,o=((e=n[0])==null?void 0:e.length)??0,c=this.scene.config.layers[0];for(let h=0;h<r;h++)for(let d=0;d<o;d++){const f=h===0||h===r-1||d===0||d===o-1,m=((s=c==null?void 0:c[h])==null?void 0:s[d])==="";n[h][d]=!f&&!m}for(const h of t){const[d,f]=h.split(",").map(Number);f>=0&&f<r&&d>=0&&d<o&&(n[f][d]=!1)}const l=[[0,1],[0,-1],[1,0],[-1,0]];for(const h of this.typedLocations){h.y>=0&&h.y<r&&h.x>=0&&h.x<o&&((i=c==null?void 0:c[h.y])==null?void 0:i[h.x])!==""&&(n[h.y][h.x]=!0);let d=!1;for(const[f,m]of l){const b=h.x+f,u=h.y+m;if(b>0&&b<o-1&&u>0&&u<r-1&&n[u][b]){d=!0;break}}if(!d)for(const[f,m]of[[0,1],[1,0],[-1,0],[0,-1]]){const b=h.x+f,u=h.y+m;if(b>0&&b<o-1&&u>0&&u<r-1&&((a=c==null?void 0:c[u])==null?void 0:a[b])!==""){n[u][b]=!0;break}}}}getReservation(){return this.reservation}getCitizen(t){return this.citizens.find(e=>e.agentId===t)}getCitizens(){return[...this.citizens]}getSpriteSheetKeys(){return Object.keys(this.config.spriteSheets??{})}getSpriteSheetConfig(t){var e;return(e=this.config.spriteSheets)==null?void 0:e[t]}getBasePath(){return this.config.worldBasePath??`worlds/${this.config.world}`}async addCitizen(t,e){const s=e??j(t.sprite),i=new H(s),a=this.config.worldBasePath??`worlds/${this.config.world}`;await i.load(a);const n=new B(t,i,this.scene.config.tileWidth,this.scene.config.tileHeight),r=this.scene.getLocation(t.position);if(r)n.setTilePosition(r.x,r.y);else{const o=this.typedLocations.find(c=>c.name===t.position);o&&n.setTilePosition(o.x,o.y)}return this.citizens.push(n),this.citizenLayer.setCitizens(this.citizens),this.unstickCitizens(),n}removeCitizen(t){const e=this.citizens.findIndex(s=>s.agentId===t);e<0||(this.reservation.release(t),this.citizens.splice(e,1),this.citizenLayer.setCitizens(this.citizens))}handleSignalUpdate(t){for(const e of t){const s=this.citizens.find(a=>a.agentId===e.id);if(!s){this.config.autoSpawn!==!1&&e.state!=="offline"&&!this.spawningAgents.has(e.id)&&this.autoSpawnCitizen(e);continue}if(s.isNpc)continue;const i=s.state;if(s.updateState(e.state,e.task,e.energy),i!==e.state){const a=Date.now(),n=this.lastTransitionTime.get(s.agentId)??0;(a-n>=D.TRANSITION_DEBOUNCE_MS||e.state==="working"||e.state==="offline"||i==="offline"||!s.isMoving())&&(this.handleStateTransition(s,i,e.state),this.lastTransitionTime.set(s.agentId,a))}for(const a of this.objects)a.config.type==="monitor"&&a.config.id===`monitor_${e.id}`&&a.setGlow(e.state==="working")}}autoSpawnCitizen(t){const e=this.config.defaultSprites??["nova","rio","dexter","morty"],s=e[this.autoSpawnIndex%e.length];this.autoSpawnIndex++;let i=[...this.typedLocations.filter(n=>n.type==="wander")].sort(()=>Math.random()-.5).find(n=>this.reservation.isAvailable(n.x,n.y,t.id))??null;!i&&this.typedLocations.length>0&&(i=[...this.typedLocations].sort(()=>Math.random()-.5).find(n=>this.reservation.isAvailable(n.x,n.y,t.id))??null);let a;if(i)a=i.name,this.reservation.reserve(i.x,i.y,t.id);else{const n=this.scene.pathfinder.getWalkableTiles();let r;if(n.length>0){const o=Math.max(1,Math.floor(n.length/8)),c=this.autoSpawnIndex*o%n.length;for(let l=0;l<n.length;l++){const h=(c+l)%n.length,d=n[h];if(this.reservation.isAvailable(d.x,d.y,t.id)){r=d;break}}r=r??n[c]}r?(a=`_spawn_${r.x}_${r.y}`,this.scene.config.locations[a]={x:r.x,y:r.y,label:a},this.reservation.reserve(r.x,r.y,t.id)):a="center"}this.spawningAgents.add(t.id),this.addCitizen({agentId:t.id,name:t.name,sprite:s,position:a}).then(n=>{n.updateState(t.state,t.task,t.energy)}).catch(()=>{}).finally(()=>{this.spawningAgents.delete(t.id)})}getOtherHomeAnchors(t){const e=new Set;for(const s of this.citizens)s.agentId!==t&&e.add(s.getHomePosition());return e}handleStateTransition(t,e,s){const i=this.getOtherHomeAnchors(t.agentId);if(this.typedLocations.length>0)if(s==="working"){const a=t.getHomePosition();this.typedLocations.find(n=>n.name===a),t.goToAnchor(a,this.typedLocations,this.scene.pathfinder,this.reservation)||t.goToAnchorType("work",this.typedLocations,this.scene.pathfinder,this.reservation,i)}else s==="sleeping"?t.goToAnchorType("rest",this.typedLocations,this.scene.pathfinder,this.reservation,i):s==="speaking"?t.isMoving()||t.goToAnchorType("social",this.typedLocations,this.scene.pathfinder,this.reservation,i):s==="thinking"&&t.goToAnchorType("utility",this.typedLocations,this.scene.pathfinder,this.reservation,i);s==="working"&&t.task?this.speechBubbles.show(t.x+16,t.y-8,t.task,4,t):s==="error"?this.particles.emitExclamation(t.x+16,t.y-t.getSittingOffset()):s==="speaking"&&t.task&&this.speechBubbles.show(t.x+16,t.y-8,t.task,5,t)}updateCitizenEffects(t,e){const s=t.agentId,i=(this.particleTimers.get(s)??0)+e;this.particleTimers.set(s,i),t.state==="sleeping"&&i>1.5&&(this.particleTimers.set(s,0),this.particles.emitZzz(t.x+16,t.y)),t.state==="thinking"&&i>2&&(this.particleTimers.set(s,0),this.particles.emitThought(t.x+16,t.y)),t.state==="error"&&i>2&&(this.particleTimers.set(s,0),this.particles.emitExclamation(t.x+16,t.y))}handleClick(t){const e=this.renderer.screenToWorld(t.offsetX,t.offsetY);for(const s of this.citizens)if(s.containsPoint(e.x,e.y)){this.emit("citizen:click",{agentId:s.agentId,name:s.name,state:s.state,task:s.task,energy:s.energy});return}for(const s of this.objects)if(s.containsPoint(e.x,e.y)){this.emit("object:click",{id:s.config.id,type:s.config.type});return}}};R.TRANSITION_DEBOUNCE_MS=8e3;let pt=R;function ft(){const p=[],t=[];for(let e=0;e<12;e++){p[e]=[],t[e]=[];for(let s=0;s<16;s++)e===0||e===11||s===0||s===15?(p[e][s]="floor",t[e][s]=!1):(p[e][s]="floor",t[e][s]=!0)}return t[2][2]=!1,t[2][3]=!1,t[2][6]=!1,t[2][7]=!1,{name:"main",tileWidth:32,tileHeight:32,layers:[p],walkable:t,locations:{desk_1:{x:3,y:3,label:"Desk 1"},desk_2:{x:7,y:3,label:"Desk 2"},coffee_machine:{x:12,y:2,label:"Coffee Machine"},couch:{x:10,y:8,label:"Couch"},whiteboard:{x:7,y:1,label:"Whiteboard"},intercom:{x:1,y:1,label:"Intercom"},center:{x:7,y:6,label:"Center"}},tiles:{floor:"tiles/office.png"}}}function j(p){return{sheets:{walk:`/universal_assets/citizens/${p}_walk.png`,actions:`/universal_assets/citizens/${p}_actions.png`},animations:{idle_down:{sheet:"actions",row:3,frames:4,speed:.5},idle_up:{sheet:"actions",row:3,frames:4,speed:.5},walk_down:{sheet:"walk",row:0,frames:4,speed:.15},walk_up:{sheet:"walk",row:1,frames:4,speed:.15},walk_left:{sheet:"walk",row:2,frames:4,speed:.15},walk_right:{sheet:"walk",row:3,frames:4,speed:.15},working:{sheet:"actions",row:0,frames:4,speed:.3},sleeping:{sheet:"actions",row:1,frames:2,speed:.8},talking:{sheet:"actions",row:2,frames:4,speed:.15}},frameWidth:64,frameHeight:64}}const Y="cozy-startup",W=`/worlds/${Y}`;function gt(p,t,e,s){var r;const i=e??Array.from({length:t},()=>Array(p).fill("")),a=[];for(let o=0;o<t;o++){a[o]=[];for(let c=0;c<p;c++)a[o][c]=(((r=i[o])==null?void 0:r[c])??"")!==""}const n={...s??{}};for(const[o,c]of Object.entries(n)){if(/^(blob:|data:|https?:\/\/)/.test(c))continue;const l=c.startsWith("/")?c.slice(1):c;n[o]=`${W}/${l}`}return{name:"main",tileWidth:32,tileHeight:32,layers:[i],walkable:a,locations:{},tiles:n}}const ut=["morty","dexter","nova","rio"];function mt(){if(document.getElementById("cc-styles"))return;const p=document.createElement("style");p.id="cc-styles",p.textContent=`
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=IBM+Plex+Mono:wght@400;500&display=swap');

.cc-fab {
  position: fixed;
  top: 16px;
  right: 16px;
  z-index: 60;
  border: 0;
  border-radius: 999px;
  padding: 10px 16px;
  background: linear-gradient(135deg, #0f766e 0%, #f59e0b 100%);
  color: #111827;
  font: 700 13px/1 'Space Grotesk', sans-serif;
  letter-spacing: 0.04em;
  cursor: pointer;
  box-shadow: 0 10px 30px rgba(15, 118, 110, 0.35);
}

.cc-shell {
  position: fixed;
  inset: 0;
  z-index: 70;
  display: none;
  background:
    radial-gradient(1200px 500px at 100% 0%, rgba(245, 158, 11, 0.16), transparent 60%),
    radial-gradient(900px 500px at 0% 100%, rgba(20, 184, 166, 0.18), transparent 55%),
    rgba(3, 7, 18, 0.78);
  backdrop-filter: blur(6px);
}

.cc-shell.open {
  display: block;
}

.cc-panel {
  position: absolute;
  inset: 40px;
  border-radius: 24px;
  border: 1px solid rgba(245, 158, 11, 0.32);
  background: linear-gradient(180deg, rgba(10, 14, 24, 0.94), rgba(8, 12, 20, 0.96));
  color: #f3f4f6;
  overflow: hidden;
  font-family: 'Space Grotesk', sans-serif;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.45);
  animation: cc-fade-in .28s ease;
}

@keyframes cc-fade-in {
  from { transform: translateY(8px); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}

.cc-grid {
  display: grid;
  grid-template-columns: 1.2fr 1fr;
  gap: 14px;
  height: calc(100% - 86px);
  padding: 14px;
}

.cc-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  background: linear-gradient(90deg, rgba(245, 158, 11, 0.14), rgba(13, 148, 136, 0.14));
}

.cc-title {
  margin: 0;
  font-size: 22px;
  letter-spacing: 0.02em;
}

.cc-subtitle {
  margin: 4px 0 0;
  font-size: 12px;
  opacity: 0.85;
}

.cc-close {
  border: 0;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.12);
  color: #f3f4f6;
  font: 600 12px/1 'IBM Plex Mono', monospace;
  padding: 10px 12px;
  cursor: pointer;
}

.cc-card {
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.03);
  padding: 14px;
}

.cc-actions {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  margin-top: 10px;
}

.cc-btn {
  border: 0;
  border-radius: 10px;
  padding: 10px 12px;
  color: #111827;
  font: 700 12px/1 'Space Grotesk', sans-serif;
  cursor: pointer;
}

.cc-btn.pause {
  background: #f59e0b;
}

.cc-btn.resume {
  background: #14b8a6;
}

.cc-btn.save {
  background: #93c5fd;
}

.cc-btn.secondary {
  background: rgba(255, 255, 255, 0.16);
  color: #f3f4f6;
}

.cc-agent-list {
  margin-top: 10px;
  display: grid;
  gap: 8px;
}

.cc-agent {
  display: grid;
  grid-template-columns: 1fr auto;
  align-items: center;
  gap: 8px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 10px;
  background: rgba(255, 255, 255, 0.02);
}

.cc-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  border-radius: 999px;
  font: 600 11px/1 'IBM Plex Mono', monospace;
  padding: 6px 8px;
  background: rgba(20, 184, 166, 0.2);
}

.cc-badge.paused {
  background: rgba(245, 158, 11, 0.25);
}

.cc-input,
.cc-select,
.cc-textarea {
  width: 100%;
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.16);
  background: rgba(0, 0, 0, 0.35);
  color: #f3f4f6;
  font: 500 13px/1.4 'IBM Plex Mono', monospace;
  padding: 10px;
  box-sizing: border-box;
}

.cc-textarea {
  min-height: 94px;
  resize: vertical;
}

.cc-log {
  margin-top: 10px;
  max-height: 230px;
  overflow: auto;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(2, 6, 23, 0.6);
  padding: 8px;
  font: 500 12px/1.4 'IBM Plex Mono', monospace;
}

.cc-log-item {
  border-bottom: 1px dashed rgba(255, 255, 255, 0.12);
  padding: 8px 6px;
}

.cc-log-item:last-child {
  border-bottom: 0;
}

.cc-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-top: 8px;
}

.cc-kpis {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 8px;
  margin-top: 10px;
}

.cc-kpi {
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.03);
  padding: 8px;
}

.cc-kpi-label {
  font: 500 11px/1 'IBM Plex Mono', monospace;
  opacity: 0.8;
}

.cc-kpi-value {
  margin-top: 4px;
  font: 700 20px/1 'Space Grotesk', sans-serif;
}

.cc-chip-row {
  margin-top: 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.cc-chip {
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 999px;
  padding: 6px 10px;
  font: 600 11px/1 'IBM Plex Mono', monospace;
  background: rgba(255, 255, 255, 0.06);
}

.cc-chip.ok {
  border-color: rgba(20, 184, 166, 0.5);
  background: rgba(20, 184, 166, 0.2);
}

.cc-chip.warn {
  border-color: rgba(245, 158, 11, 0.5);
  background: rgba(245, 158, 11, 0.22);
}

@media (max-width: 1040px) {
  .cc-panel {
    inset: 10px;
  }

  .cc-grid {
    grid-template-columns: 1fr;
    height: calc(100% - 80px);
    overflow: auto;
  }

  .cc-actions {
    grid-template-columns: 1fr;
  }

  .cc-kpis {
    grid-template-columns: 1fr;
  }
}
`,document.head.appendChild(p)}function yt(){mt();const p=document.createElement("button");p.className="cc-fab",p.type="button",p.textContent="Centro de Comando";const t=document.createElement("div");t.className="cc-shell",t.innerHTML=`
    <section class="cc-panel" aria-label="Centro de Comando">
      <header class="cc-header">
        <div>
          <h2 class="cc-title">Centro de Comando de Agentes</h2>
          <p class="cc-subtitle">Control táctico, conversaciones multiagente y snapshots en tiempo real</p>
        </div>
        <button type="button" class="cc-close">ESC / Cerrar</button>
      </header>
      <div class="cc-grid">
        <div class="cc-card">
          <div id="cc-status-badge" class="cc-badge">Estado: cargando</div>
          <div class="cc-kpis">
            <div class="cc-kpi"><div class="cc-kpi-label">Tareas totales</div><div id="cc-kpi-total" class="cc-kpi-value">0</div></div>
            <div class="cc-kpi"><div class="cc-kpi-label">Completadas</div><div id="cc-kpi-completed" class="cc-kpi-value">0</div></div>
            <div class="cc-kpi"><div class="cc-kpi-label">En revisión</div><div id="cc-kpi-review" class="cc-kpi-value">0</div></div>
            <div class="cc-kpi"><div class="cc-kpi-label">Agentes activos</div><div id="cc-kpi-active" class="cc-kpi-value">0</div></div>
            <div class="cc-kpi"><div class="cc-kpi-label">Durmiendo</div><div id="cc-kpi-sleep" class="cc-kpi-value">0</div></div>
          </div>
          <div class="cc-chip-row">
            <span id="cc-chip-learner" class="cc-chip">Learner: --</span>
            <span id="cc-chip-autochat" class="cc-chip">Auto chat: --</span>
            <span id="cc-chip-updated" class="cc-chip">Sync: --</span>
          </div>
          <div class="cc-actions">
            <button type="button" class="cc-btn pause" data-action="pause_all">Pausar Todo + Guardar</button>
            <button type="button" class="cc-btn resume" data-action="resume_all">Reanudar Todo</button>
            <button type="button" class="cc-btn save" data-action="save_snapshot">Guardar Snapshot</button>
          </div>
          <div id="cc-agent-list" class="cc-agent-list"></div>
        </div>
        <div class="cc-card">
          <label for="cc-target">Objetivo</label>
          <select id="cc-target" class="cc-select">
            <option value="boss">Boss (orquestación)</option>
            <option value="accountant">Contador</option>
            <option value="librarian">Bibliotecaria</option>
            <option value="auditor">Auditor</option>
          </select>
          <div class="cc-row">
            <div>
              <label for="cc-poll">pollSec</label>
              <input id="cc-poll" class="cc-input" type="number" min="0.5" step="0.5" placeholder="3" />
            </div>
            <div>
              <label for="cc-heartbeat">heartbeatSec</label>
              <input id="cc-heartbeat" class="cc-input" type="number" min="3" step="1" placeholder="20" />
            </div>
          </div>
          <div class="cc-row">
            <div>
              <label for="cc-visual">visualInterval</label>
              <input id="cc-visual" class="cc-input" type="number" min="1" step="1" placeholder="15" />
            </div>
            <div>
              <label for="cc-conv-interval">conversationSec</label>
              <input id="cc-conv-interval" class="cc-input" type="number" min="10" step="5" placeholder="90" />
            </div>
          </div>
          <div class="cc-row">
            <div>
              <label for="cc-auto-conv">Auto conversación</label>
              <select id="cc-auto-conv" class="cc-select">
                <option value="0">Desactivada</option>
                <option value="1">Activada</option>
              </select>
            </div>
            <div>
              <label>&nbsp;</label>
              <button id="cc-apply-params" type="button" class="cc-btn secondary" style="width:100%">Aplicar Parámetros</button>
            </div>
          </div>
          <label for="cc-message" style="display:block;margin-top:10px">Instrucción</label>
          <textarea id="cc-message" class="cc-textarea" placeholder="Escribe una orden o tarea..."></textarea>
          <div class="cc-actions" style="margin-top:8px">
            <button id="cc-send" type="button" class="cc-btn resume">Enviar Instrucción</button>
            <button id="cc-pause-agent" type="button" class="cc-btn pause">Pausar Objetivo</button>
            <button id="cc-resume-agent" type="button" class="cc-btn secondary">Reanudar Objetivo</button>
          </div>
          <label for="cc-conv-topic" style="display:block;margin-top:10px">Tema conversación</label>
          <input id="cc-conv-topic" class="cc-input" type="text" placeholder="coordinación operativa, revisión financiera, etc." />
          <div class="cc-actions" style="margin-top:8px">
            <button id="cc-spark-conv" type="button" class="cc-btn save">Iniciar Conversación</button>
          </div>
          <div id="cc-log" class="cc-log"></div>
        </div>
      </div>
    </section>
  `,document.body.appendChild(p),document.body.appendChild(t);const e=t.querySelector(".cc-close"),s=t.querySelector("#cc-status-badge"),i=t.querySelector("#cc-agent-list"),a=t.querySelector("#cc-log"),n=t.querySelector("#cc-kpi-total"),r=t.querySelector("#cc-kpi-completed"),o=t.querySelector("#cc-kpi-review"),c=t.querySelector("#cc-kpi-active"),l=t.querySelector("#cc-kpi-sleep"),h=t.querySelector("#cc-chip-learner"),d=t.querySelector("#cc-chip-autochat"),f=t.querySelector("#cc-chip-updated"),m=t.querySelector("#cc-target"),b=t.querySelector("#cc-message"),u=t.querySelector("#cc-poll"),v=t.querySelector("#cc-heartbeat"),S=t.querySelector("#cc-visual"),w=t.querySelector("#cc-conv-interval"),T=t.querySelector("#cc-auto-conv"),M=t.querySelector("#cc-conv-topic"),L=g=>{t.classList.toggle("open",g)},X=new URLSearchParams(location.search).has("cc");L(X),p.addEventListener("click",()=>{L(!t.classList.contains("open"))}),e.addEventListener("click",()=>L(!1)),document.addEventListener("keydown",g=>{g.key==="Escape"&&L(!1),g.ctrlKey&&g.shiftKey&&g.key.toLowerCase()==="k"&&(g.preventDefault(),L(!t.classList.contains("open")))});const C=async(g,y={})=>{const x={action:g,source:"command-center-ui",...y},k=await fetch("/api/command-center/command",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(x)});if(!k.ok){const P=await k.text();throw new Error(P||`HTTP ${k.status}`)}return k.json()},U=(g=[])=>{if(!g.length){a.innerHTML='<div class="cc-log-item">Sin respuestas todavía.</div>';return}a.innerHTML=g.slice().reverse().map(y=>`<div class="cc-log-item"><strong>${y.ok===!1?"ERROR":"OK"}</strong> ${y.kind||"runtime"}<br/>${y.message||""}<br/><small>${y.at||""}</small></div>`).join("")},G=(g=[])=>{i.innerHTML=g.map(y=>{const x=!!y.paused,k=x?"cc-badge paused":"cc-badge",P=x?"sleeping":y.state||"idle";return`
          <div class="cc-agent">
            <div>
              <div style="font-weight:700">${y.name}</div>
              <div style="font-size:12px;opacity:.85">${y.task||"Sin tarea"}</div>
            </div>
            <div style="display:flex;gap:8px;align-items:center">
              <span class="${k}">${P}</span>
              <button type="button" class="cc-btn secondary" data-agent-toggle="${y.key}|${x?"resume_agent":"pause_agent"}">${x?"Reanudar":"Pausar"}</button>
            </div>
          </div>
        `}).join(""),i.querySelectorAll("[data-agent-toggle]").forEach(y=>{y.addEventListener("click",async()=>{const[x,k]=y.getAttribute("data-agent-toggle").split("|");try{await C(k,{target:x})}catch(P){console.error(P)}})})},I=async()=>{var g,y;try{const x=await fetch("/api/command-center/status").then(z=>z.json()),k=x.runtime||{},P=!!k.pausedAll;s.className=P?"cc-badge paused":"cc-badge",s.textContent=P?"Estado: PAUSA GLOBAL":"Estado: OPERATIVO";const O=((g=x.tasks)==null?void 0:g.byStatus)||{};n.textContent=String(((y=x.tasks)==null?void 0:y.total)||0),r.textContent=String(O.completed||0),o.textContent=String(O.needs_revision||0);const $=x.agents||[],F=$.filter(z=>!z.paused).length,K=$.filter(z=>z.paused||z.state==="sleeping").length;c.textContent=String(F),l.textContent=String(K);const A=k.parameters||{};u.value=A.pollSec||u.value||"",v.value=A.heartbeatSec||v.value||"",S.value=A.visualInterval||S.value||"",w.value=A.conversationIntervalSec||w.value||"",T.value=A.autoConversation?"1":"0",h.className=`cc-chip ${k.librarianLearnerActive?"ok":"warn"}`,h.textContent=`Learner: ${k.librarianLearnerActive?"activo":"apagado"}`,d.className=`cc-chip ${A.autoConversation?"ok":"warn"}`,d.textContent=`Auto chat: ${A.autoConversation?"encendido":"apagado"}`,f.className="cc-chip",f.textContent=`Sync: ${String(x.updatedAt||"--").replace("T"," ").slice(0,19)}Z`,G($),U(x.responses||[])}catch{s.className="cc-badge paused",s.textContent="Estado: sin conexión"}};t.querySelectorAll("[data-action]").forEach(g=>{g.addEventListener("click",async()=>{const y=g.getAttribute("data-action");try{await C(y,y==="pause_all"?{params:{saveSnapshot:!0}}:{}),await I()}catch(x){console.error(x)}})}),t.querySelector("#cc-send").addEventListener("click",async()=>{const g=b.value.trim();if(g)try{await C("dispatch",{target:m.value,message:g}),b.value="",await I()}catch(y){console.error(y)}}),t.querySelector("#cc-pause-agent").addEventListener("click",async()=>{try{await C("pause_agent",{target:m.value}),await I()}catch(g){console.error(g)}}),t.querySelector("#cc-resume-agent").addEventListener("click",async()=>{try{await C("resume_agent",{target:m.value}),await I()}catch(g){console.error(g)}}),t.querySelector("#cc-apply-params").addEventListener("click",async()=>{const g={};if(u.value&&(g.pollSec=Number(u.value)),v.value&&(g.heartbeatSec=Number(v.value)),S.value&&(g.visualInterval=Number(S.value)),w.value&&(g.conversationIntervalSec=Number(w.value)),g.autoConversation=T.value==="1",!!Object.keys(g).length)try{await C("set_params",{params:g}),await I()}catch(y){console.error(y)}}),t.querySelector("#cc-spark-conv").addEventListener("click",async()=>{const g=M.value.trim()||"coordinación operativa";try{await C("spark_conversation",{message:g}),await I()}catch(y){console.error(y)}}),I(),setInterval(I,2e3)}async function bt(){const p=document.getElementById("world"),t=await fetch(`${W}/world.json`).then(d=>d.json()).catch(()=>null),e=(t==null?void 0:t.gridCols)??16,s=(t==null?void 0:t.gridRows)??12,i=gt(e,s,t==null?void 0:t.floor,t==null?void 0:t.tiles),a=32,r=`${location.protocol==="https:"?"wss:":"ws:"}//${location.host}/ws`,o=new pt({container:p,world:Y,scene:"main",signal:{type:"websocket",url:r},citizens:[],defaultSprites:ut,scale:2,width:e*a,height:s*a,sceneConfig:i,objects:[]}),c=new dt(a,2),l=(t==null?void 0:t.propImages)??{};await Promise.all(Object.entries(l).map(([d,f])=>{const m=f.startsWith("/")?f:"/"+f;return c.loadSprite(d,`${W}${m}`)})),c.setLayout((t==null?void 0:t.props)??[]),t!=null&&t.wanderPoints&&c.setWanderPoints(t.wanderPoints),c.setDeadspaceCheck((d,f)=>{var b;const m=o.getFloorLayer();return((b=m==null?void 0:m[f])==null?void 0:b[d])===""});const h=()=>{o.setTypedLocations(c.getLocations()),o.updateWalkability(c.getBlockedTiles())};h(),c.onSave(h),await o.start(),o.addLayer({order:5,render:d=>c.renderBelow(d)}),o.addLayer({order:15,render:d=>c.renderAbove(d)}),yt()}bt().catch(console.error);
