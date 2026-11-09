import {hasTechnology} from "./technology-wording.js";
import {counts} from "./review-counts.js";
import {sourceUrl} from "./job-source.js";
const inputs=[document.getElementById("first"),document.getElementById("second")];
const result=document.getElementById("comparison");
const message=document.getElementById("message");
let version=0;

function add(parent,tag,text){
  const node=document.createElement(tag);
  node.textContent=text;
  parent.append(node);
  return node;
}
function wording(text){return text.normalize("NFC").trim().replace(/\s+/gu," ")}
async function read(file){
  const data=JSON.parse(await file.text());
  if(data?.format!=="job-radar-review-v1"||!Array.isArray(data.conditions)||!data.conditions.length||
     !data.conditions.every(r=>typeof r?.condition==="string"&&r.condition.trim()&&
       ["supported","partial","unverified","skip"].includes(r.label))){
    throw Error("Choose a JSON report downloaded from CV review.");
  }
  const summary=counts(data.conditions.map(r=>r.label));
  if(Object.entries(summary).some(([k,v])=>v!==data.coverage?.[k])){
    throw Error("The summary in "+file.name+" differs from its condition decisions. Export the review again.");
  }
  const indexed=new Map(data.conditions.map(row=>[wording(row.condition),row]));
  if(indexed.size!==data.conditions.length)throw Error(file.name+" repeats a condition. Export the review again.");
  return {data,summary,file,indexed};
}
function show({data,summary,file}){
  const card=add(result,"article","");
  add(card,"h2",data.job?.title||file.name);
  const url=sourceUrl(data.job?.url);
  if(url){
    const link=add(card,"a","Open source posting");
    link.href=url;link.referrerPolicy="no-referrer";
  }
  add(card,"strong",summary.percentage===null?"No required conditions":summary.percentage+"% coverage").className="metric";
  add(card,"p",summary.supported+" of "+summary.required+" required conditions fully supported.");
  add(card,"p",summary.partial+" partial · "+summary.unverified+" unverified · "+summary.excluded+" excluded");
  const gaps=data.conditions.filter(r=>r.label==="partial"||r.label==="unverified");
  if(gaps.length){
    const panel=add(card,"details","");
    add(panel,"summary","Conditions to revisit ("+gaps.length+")");
    const list=add(panel,"ul","");
    for(const row of gaps){
      const item=add(list,"li",row.condition);
      add(item,"small",row.label==="partial"?"Partially supported":"Unverified");
      if(row.missing)add(item,"small","Wording to demonstrate: "+row.missing);
      if(row.next_edit||row.note)add(item,"small","Next CV edit: "+(row.next_edit||row.note));
    }
  }
}
const labels={supported:"Fully supported",partial:"Partially supported",unverified:"Unverified",skip:"Excluded"};
function showConditionComparison(first,second){
  const panel=add(result,"section","");
  panel.className="alignment";
  add(panel,"h2","Compare individual conditions");
  const shared=[...first.indexed.keys()].filter(key=>second.indexed.has(key));
  const changed=shared.filter(key=>first.indexed.get(key).label!==second.indexed.get(key).label);
  add(panel,"p",shared.length+(shared.length===1?" condition":" conditions")+" with matching wording · "+changed.length+" assessed differently. Matching preserves the original language and ignores spacing.");
  function group(title,keys){
    if(!keys.length)return;
    const details=add(panel,"details","");
    add(details,"summary",title+" ("+keys.length+")");
    const list=add(details,"ul","");
    for(const key of keys){
      const item=add(list,"li",key);
      for(const [name,review] of [["First",first],["Second",second]]){
        const row=review.indexed.get(key);
        if(!row)continue;
        add(item,"small",name+" review · "+labels[row.label]);
        if(Array.isArray(row.quotes))for(const quote of row.quotes){
          const passage=quote?.excerpt||quote?.passage;
          if(typeof passage==="string"&&passage.trim())add(item,"blockquote",passage);
        }
      }
    }
  }
  group("Different assessments",changed);
  group("Same assessments",shared.filter(key=>first.indexed.get(key).label===second.indexed.get(key).label));
  group("Only in the first review",[...first.indexed.keys()].filter(key=>!second.indexed.has(key)));
  group("Only in the second review",[...second.indexed.keys()].filter(key=>!first.indexed.has(key)));
}
function showSharedTechnologies(first,second,names){
  const pairs=names.map(name=>({name,rows:[first,second].map(review=>
    review.data.conditions.filter(row=>hasTechnology(row.condition,name)))}))
    .filter(pair=>pair.rows.every(rows=>rows.length)&&
      pair.rows.some((rows,i)=>rows.some(row=>!pair.rows[1-i].some(other=>wording(other.condition)===wording(row.condition)))));
  if(!pairs.length)return;
  const panel=add(result,"section","");
  panel.className="alignment technologies";
  add(panel,"h2","Shared technologies in different conditions");
  add(panel,"p","Compare the original requirements for each technology. Each review keeps its own assessments and coverage.");
  for(const {name,rows} of pairs){
    const details=add(panel,"details","");
    add(details,"summary",name);
    rows.forEach((conditions,i)=>{
      add(details,"strong",i===0?"First review":"Second review");
      const list=add(details,"ul","");
      for(const row of conditions)add(list,"li",row.condition+" · "+labels[row.label]);
    });
  }
}
const technologyNames=fetch("technologies.json").then(response=>response.ok?response.json():[]).catch(()=>[]);
async function compare(){
  const request=++version;
  result.replaceChildren();
  const files=inputs.map(input=>input.files[0]);
  if(files.some(f=>!f)){message.textContent="Choose both reports to compare.";return}
  message.textContent="Reading reviews…";
  try{
    const reviews=await Promise.all(files.map(read));
    const names=await technologyNames;
    if(request!==version)return;
    const hashes=reviews.map(r=>r.data.cv?.sha256);
    const valid=hashes.every(h=>typeof h==="string"&&/^[0-9a-f]{64}$/i.test(h));
    message.textContent=!valid?"These reports do not both identify the CV input. Check the CV versions before comparing.":
      hashes[0]===hashes[1]?"Both reports used the same CV input.":"These reports used different CV inputs. Differences may reflect changes to the CV as well as the job.";
    reviews.forEach(show);
    showConditionComparison(...reviews);
    showSharedTechnologies(...reviews,names);
  }catch(error){
    if(request===version)message.textContent=error instanceof SyntaxError?"Choose valid review JSON files.":error.message;
  }
}
inputs.forEach(input=>input.onchange=compare);
