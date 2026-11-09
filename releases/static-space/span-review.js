const el=id=>document.getElementById(id);
const digest=async bytes=>Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",bytes)),
  n=>n.toString(16).padStart(2,"0")).join("");
const normalize=text=>text.replace(/\u200b/gu,"").trim().replace(/\s+/gu," ");
let packet,packetHash,available=[],marks=[],saved={},dirty=false,loadVersion=0;
const selected=()=>available[Number(el("bullet").value)];
const storageKey=()=>"job-radar-turkish-spans-v1-"+packetHash;
function progress(){
  const n=Object.keys(saved).length;
  el("progress").textContent=n+" of "+packet.length+" distinct bullets saved.";
  el("download").disabled=!n||dirty;
}
function draw(){
  el("marks").replaceChildren();
  const chars=Array.from(el("text").value);
  for(const [i,[start,end]] of marks.entries()){
    const item=document.createElement("li");
    item.textContent=chars.slice(start,end).join("");
    const remove=document.createElement("button");
    remove.textContent="Remove";
    remove.onclick=()=>{marks.splice(i,1);dirty=true;draw()};
    item.append(remove);
    el("marks").append(item);
  }
  el("none").disabled=marks.length>0;
  el("save").disabled=!marks.length&&!el("none").checked;
  progress();
}
function pick(){
  const row=selected();
  el("text").value=row.text;
  marks=(saved[row.id]?.spans||[]).map(span=>[...span]);
  el("none").checked=Boolean(saved[row.id]&&!marks.length);
  dirty=false;draw();
}
function allowChange(){return !dirty||window.confirm("Discard unsaved changes to this bullet?")}
el("bullet").onchange=()=>{
  if(!allowChange()){el("bullet").value=el("bullet").dataset.current;return}
  el("bullet").dataset.current=el("bullet").value;pick();
};
function clearPosting(){
  available=[];marks=[];dirty=false;el("review").hidden=true;el("status").textContent="";
  el("source").href=el("posting").value;el("source").hidden=false;progress();
}
el("posting").onchange=()=>{
  if(!allowChange()){el("posting").value=el("posting").dataset.current;return}
  ++loadVersion;
  el("posting").dataset.current=el("posting").value;
  el("load").disabled=false;clearPosting();
};
async function sourceLines(url){
  const path=new URL(url).pathname.split("/").filter(Boolean);
  const roof=new URL(url).hostname==="jobs.lever.co";
  const api=roof?"https://api.lever.co/v0/postings/roofstacks/"+path.at(-1):
    "https://api.smartrecruiters.com/v1/companies/CRENNO/postings/"+path.at(-1);
  const response=await fetch(api,{credentials:"omit",referrerPolicy:"no-referrer"});
  if(!response.ok)throw Error();
  const job=await response.json();
  if(roof)return job.descriptionPlain.split(/\r?\n/).map(normalize);
  const html=job.jobAd.sections.qualifications.text;
  return [...html.matchAll(/<li\b[^>]*>([\s\S]*?)<\/li>/giu)].map(match=>
    normalize(new DOMParser().parseFromString(match[1].replace(/<[^>]+>/gu," "),"text/html").documentElement.textContent));
}
el("load").onclick=async()=>{
  if(!allowChange())return;
  const version=++loadVersion;
  const url=el("posting").value;
  clearPosting();el("load").disabled=true;el("status").textContent="Matching source fingerprints…";
  try{
    const lines=[...new Set(await sourceLines(url))];
    const found=new Map(await Promise.all(lines.map(async text=>[await digest(new TextEncoder().encode(text)),text])));
    if(version!==loadVersion)return;
    const expected=packet.filter(row=>row.sources.includes(url));
    available=expected.filter(row=>found.has(row.id)).map(row=>({...row,text:found.get(row.id)}));
    el("status").textContent=available.length+" of "+expected.length+" indexed bullets matched the current posting.";
    if(!available.length)return;
    el("bullet").replaceChildren(...available.map((row,i)=>new Option((i+1)+" · "+row.text.slice(0,90),i)));
    el("bullet").dataset.current="0";el("review").hidden=false;pick();
  }catch{if(version===loadVersion)el("status").textContent="The employer text could not be loaded. Try another posting or retry."}
  finally{if(version===loadVersion)el("load").disabled=false}
};
el("add").onclick=()=>{
  const field=el("text");
  const a=Array.from(field.value.slice(0,field.selectionStart)).length;
  const b=Array.from(field.value.slice(0,field.selectionEnd)).length;
  const phrase=field.value.slice(field.selectionStart,field.selectionEnd);
  if(!phrase||phrase.trim()!==phrase||marks.some(([start,end])=>a<end&&b>start)){
    el("status").textContent="Select a non-overlapping phrase without outer spaces.";return;
  }
  marks.push([a,b]);marks.sort((x,y)=>x[0]-y[0]);el("none").checked=false;
  dirty=true;el("status").textContent="Unsaved selection.";draw();
};
el("none").onchange=()=>{dirty=true;draw()};
el("save").onclick=()=>{
  const row=selected();
  if(!row||(!marks.length&&!el("none").checked))return;
  saved[row.id]={format:"job-radar-knowledge-review-v1",packet_sha256:packetHash,id:row.id,spans:marks.map(s=>[...s])};
  dirty=false;
  try{localStorage.setItem(storageKey(),JSON.stringify(saved));el("status").textContent="Completed bullet saved."}
  catch{el("status").textContent="Saved in this tab. Download your decisions before closing."}
  progress();
};
el("download").onclick=()=>{
  const data=Object.values(saved).map(row=>JSON.stringify(row)).join("\n")+"\n";
  const url=URL.createObjectURL(new Blob([data],{type:"application/x-ndjson"}));
  const link=document.createElement("a");link.href=url;link.download="turkish-knowledge-review.jsonl";link.click();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
};
try{
  const response=await fetch("span-review-packet.json");
  if(!response.ok)throw Error();
  const bytes=await response.arrayBuffer();packetHash=await digest(bytes);packet=JSON.parse(new TextDecoder().decode(bytes));
  try{saved=JSON.parse(localStorage.getItem(storageKey())||"{}")||{}}catch{saved={}}
  const urls=[...new Set(packet.flatMap(row=>row.sources))].sort();
  el("posting").replaceChildren(...urls.map(url=>new Option(new URL(url).pathname.slice(1),url)));
  el("posting").dataset.current=el("posting").value;el("posting").disabled=false;el("load").disabled=false;
  clearPosting();
}catch{el("status").textContent="The source index is unavailable."}
