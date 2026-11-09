const el=id=>document.getElementById(id);
const radios=[...document.querySelectorAll("input[name=label]")];
const labels=new Set(radios.map(r=>r.value));
const gitPacket=new URLSearchParams(location.search).get("packet")==="git";
el("packetTitle").textContent=gitPacket?"Cross-language Git evidence":"Source-grounded CV evidence";
const response=await fetch(gitPacket?"git-review-packet.jsonl":"review-packet.jsonl");
if(!response.ok)throw Error(el("progress").textContent="Examples are unavailable. Reload to retry.");
const bytes=await response.arrayBuffer();
const hash=[...new Uint8Array(await crypto.subtle.digest("SHA-256",bytes))].map(n=>n.toString(16).padStart(2,"0")).join("");
const rows=new TextDecoder().decode(bytes).trim().split(/\r?\n/).map(line=>JSON.parse(line));
const key="job-radar-review-"+hash;
let stored={};
try{stored=JSON.parse(localStorage.getItem(key)||"{}")||{}}catch{}
const decisions=new Map();
function valid(row,answer){
  return answer?.id===row.id && answer.packet_sha256===hash && labels.has(answer.label) &&
    ((answer.evidence===null && answer.label==="unverified") ||
     (typeof answer.evidence==="string" && answer.evidence.trim() && row.cv_passage.includes(answer.evidence)));
}
for(const row of rows)if(valid(row,stored[row.id]))decisions.set(row.id,stored[row.id]);
// Mix families and passage types without displaying model predictions.
for(let i=rows.length-1;i>0;i--){
  const j=Math.floor(Math.random()*(i+1));
  [rows[i],rows[j]]=[rows[j],rows[i]];
}
let index=Math.max(0,rows.findIndex(row=>!decisions.has(row.id)));
const requested=rows.findIndex(row=>row.id===new URLSearchParams(location.search).get("case"));
if(requested>=0)index=requested;
function render(){
  const row=rows[index],answer=decisions.get(row.id);
  el("case").hidden=false;
  el("condition").textContent=row.requirement;
  el("passage").textContent=row.cv_passage;
  for(const r of radios)r.checked=r.value===answer?.label;
  el("quote").value=answer?.evidence||"";
  el("progress").textContent="Example "+(index+1)+" of "+rows.length+" · "+decisions.size+" saved";
  el("previous").disabled=index===0;
  el("next").disabled=index===rows.length-1;
  el("export").disabled=decisions.size===0;
  el("export").textContent="Download "+decisions.size+" saved decision"+(decisions.size===1?"":"s");
  const link=new URL(location.href);
  link.searchParams.set("case",row.id);
  el("caseLink").href=link.href;
}
function move(step){
  const answer=decisions.get(rows[index].id);
  const changed=(radios.find(r=>r.checked)?.value||"")!==(answer?.label||"") || el("quote").value.trim()!==(answer?.evidence||"");
  if(changed){el("message").textContent="Save your changes before moving to another example.";return}
  index+=step;el("message").textContent="";render();
}
el("previous").onclick=()=>move(-1);
el("next").onclick=()=>move(1);
el("case").oninput=()=>{el("export").disabled=true;el("message").textContent="Unsaved decision."};
el("save").onclick=()=>{
  const row=rows[index];
  const answer={id:row.id,label:radios.find(r=>r.checked)?.value,evidence:el("quote").value.trim()||null,packet_sha256:hash};
  if(!valid(row,answer)){el("message").textContent="Choose a label and copy the deciding words exactly from the passage.";return}
  decisions.set(row.id,answer);
  el("message").textContent="Decision saved.";
  try{localStorage.setItem(key,JSON.stringify(Object.fromEntries(decisions)))}catch{el("message").textContent="Saved in this tab only. Keep it open until you download the file."}
  const pending=rows.findIndex(r=>!decisions.has(r.id));
  if(pending>=0)index=pending;
  render();
};
el("export").onclick=()=>{
  const body=[...decisions.values()].map(answer=>JSON.stringify(answer)).join("\n")+"\n";
  const url=URL.createObjectURL(new Blob([body],{type:"application/x-ndjson"}));
  const a=document.createElement("a");a.href=url;a.download=(gitPacket?"job-radar-git-review-":"job-radar-review-")+decisions.size+"-of-"+rows.length+".jsonl";a.click();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
};
render();
