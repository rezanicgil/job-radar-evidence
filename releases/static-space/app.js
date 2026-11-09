const el=id=>document.getElementById(id);
const add=(parent,tag,text)=>{const node=document.createElement(tag);node.textContent=text;parent.append(node);return node};
const words=text=>new Set(text.toLocaleLowerCase().match(/[\p{L}\p{N}+#]+/gu)||[]);
let encoder;
let vocabulary;
function hasTechnology(text,name){
  const tokens=text.toLowerCase().match(/[\p{L}\p{N}_+#]+/gu)||[];
  return (" "+tokens.join(" ")+" ").includes(" "+name.toLowerCase()+" ");
}
async function vectors(texts){
  const {pipeline,env}=await import("https://cdn.jsdelivr.net/npm/@xenova/transformers@2.17.2/dist/transformers.min.js");
  env.allowLocalModels=false;
  encoder??=await pipeline("feature-extraction","Xenova/paraphrase-multilingual-MiniLM-L12-v2",{revision:"2c4055b12046f11709e9df2c122e59ffbdc2f900"});
  const all=[];
  for(let i=0;i<texts.length;i+=8)all.push(...(await encoder(texts.slice(i,i+8),{pooling:"mean",normalize:true})).tolist());
  return all;
}
async function readPages(file){
  if(!file)return [el("cv").value];
  if(file.size>3*1024*1024)throw Error("Choose a file smaller than 3 MB.");
  if(/\.txt$/i.test(file.name))return [await file.text()];
  if(!/\.pdf$/i.test(file.name))throw Error("Choose a text PDF or TXT file.");
  const pdf=await import("https://cdn.jsdelivr.net/npm/pdfjs-dist@4.10.38/build/pdf.min.mjs");
  pdf.GlobalWorkerOptions.workerSrc="https://cdn.jsdelivr.net/npm/pdfjs-dist@4.10.38/build/pdf.worker.min.mjs";
  const doc=await pdf.getDocument({data:await file.arrayBuffer(),isEvalSupported:false}).promise;
  const pages=[];
  try{
    for(let i=1;i<=doc.numPages;i++){
      const page=await doc.getPage(i),content=await page.getTextContent();
      pages.push(content.items.map(x=>(x.str||"")+(x.hasEOL?"\n":" ")).join(""));
    }
  }finally{await doc.destroy()}
  return pages;
}
const sectionTitle=/^(?:(?:professional |work |relevant )?experience|(?:technical )?skills|(?:professional )?summary|education|projects|certifications|languages|iş deneyimi|deneyim|eğitim|projeler|teknik beceriler|yetenekler|özet|diller)\s*:?$/iu;
function pagePassages(page,isPdf){
  const chunks=[];
  let previous="";
  function flush(){
    if(previous)chunks.push(previous);
    previous="";
  }
  for(const raw of page.split(/\r?\n/)){
    const line=raw.trim();
    if(!line || sectionTitle.test(line)){flush();continue}
    const bullet=/^[•▪●]|^[-–]\s/.test(line);
    const content=line.replace(/^[•▪●]\s*|^[-–]\s+/,"");
    // A PDF line break before lowercase text commonly wraps the same sentence.
    const wraps=isPdf && !bullet && /^\p{Ll}/u.test(content) && !/[.!?:]$/.test(previous);
    if(!wraps)flush();
    previous=previous ? previous+" "+content : content;
  }
  flush();
  return chunks.flatMap(chunk=>chunk.split(/(?<=[.!?])\s+/)).filter(text=>!sectionTitle.test(text));
}
function coverage(){
  const values=[...el("results").querySelectorAll("select")].map(s=>s.value);
  if(values.includes("")){el("status").textContent=values.filter(v=>!v).length+" conditions awaiting review.";return}
  const n=values.filter(v=>v!=="skip").length,s=values.filter(v=>v==="supported").length;
  el("status").textContent=n?"Reviewer-confirmed coverage: "+s+"/"+n+" ("+Math.round(100*s/n)+"%).":"No required conditions selected.";
}
el("form").onsubmit=async event=>{
  event.preventDefault();el("find").disabled=true;el("results").replaceChildren();
  try{
    const pages=await readPages(el("file").files[0]);
    const isPdf=/\.pdf$/i.test(el("file").files[0]?.name || "");
    const lines=pages.flatMap((p,i)=>pagePassages(p,isPdf).map(text=>({text,page:i+1})));
    const job=[...new Set(el("job").value.split(/[\r\n]+/).map(x=>x.trim()).filter(Boolean))];
    if(!lines.length||!job.length||job.length>50||lines.length>800)throw Error("Use a readable CV and 1–50 conditions.");
    el("status").textContent="Finding passages…";
    const semantic=el("method").value==="semantic";
    const vec=semantic?await vectors([...job,...lines.map(x=>x.text)]):null;
    if(semantic && !vocabulary){
      const response=await fetch("technologies.json");
      if(response.ok)vocabulary=await response.json();
    }
    job.forEach((condition,i)=>{
      const terms=words(condition);
      const ranked=lines.map((line,j)=>({line,score:semantic?vec[i].reduce((s,v,k)=>s+v*vec[job.length+j][k],0):[...words(line.text)].filter(t=>terms.has(t)).length}))
        .filter(x=>semantic||x.score>0).sort((a,b)=>b.score-a.score).slice(0,3);
      const card=add(el("results"),"article","");add(card,"h3",condition);
      for(const {line} of ranked)add(card,"p","Page "+line.page+" · "+line.text);
      if(semantic){
        const requested=(vocabulary||[]).filter(name=>hasTechnology(condition,name));
        const visible=ranked.map(item=>item.line);
        for(const name of requested){
          if(visible.some(line=>hasTechnology(line.text,name)))continue;
          const mention=lines.find(line=>hasTechnology(line.text,name));
          if(!mention)continue;
          add(card,"small",name+" mentioned on page "+mention.page+" · "+mention.text);
          visible.push(mention);
        }
      }
      if(!ranked.length)add(card,"p","No shared terms found. Review the CV directly.");
      const select=add(add(card,"label","Assessment "),"select","");
      for(const [value,label] of [["","Choose"],["supported","Required · supported"],["partial","Required · partial"],["unverified","Required · unverified"],["skip","Exclude from required coverage"]])select.add(new Option(label,value));
      select.onchange=coverage;
    });coverage();
  }catch(error){el("status").textContent=error.message+" If semantic search is unavailable, choose Shared terms."}
  finally{el("find").disabled=false}
};
try{
  const market=await (await fetch("market.json")).json();
  el("area").add(new Option("All tracked roles",""));
  for(const a of market.areas)el("area").add(new Option(a,a));
  function render(){
    const group=market.postings.filter(p=>!el("area").value||p.areas.includes(el("area").value));
    const records=group.filter(p=>p.status==="readable");
    const urls=new Set(group.map(posting=>posting.url));
    const reviewed=(market.reviews||[]).filter(review=>urls.has(review.source_url));
    const evidence=el("verified");
    evidence.replaceChildren();
    if(reviewed.length){
      add(evidence,"h2","Reviewed requirements");
      for(const review of reviewed){
        const card=add(evidence,"article","");
        const link=add(card,"a",review.employer+" · "+review.title);
        link.href=review.source_url;
        add(card,"p",review.required_skills.join(review.skill_relation==="all_of"?" + ":" or "));
        add(card,"blockquote",review.requirement_evidence);
      }
    }
    const direct=el("direct");
    direct.replaceChildren();
    const openings=(market.direct||[]).filter(row=>!el("area").value||row.areas.includes(el("area").value));
    if(openings.length){
      add(direct,"h2","Direct employer observations");
      add(direct,"p","Shown separately from the technology mention counts.");
      for(const row of openings){
        const card=add(direct,"article","");
        add(card,"a",row.employer+" · "+row.title).href=row.source_url;
        add(card,"p",row.location+" · Observed "+row.observed_on);
      }
    }
    el("scope").textContent=market.collected_at.slice(0,10)+" · "+records.length+" readable descriptions of "+group.length+" selected postings. Counts include mentions in preferences and company context.";
    const skills=new Map();
    for(const p of records)for(const s of new Set(p.skills)){if(!skills.has(s))skills.set(s,[]);skills.get(s).push(p)}
    el("counts").replaceChildren();
    for(const [s,ps] of [...skills].sort((a,b)=>b[1].length-a[1].length||a[0].localeCompare(b[0]))){
      const d=add(el("counts"),"details","");add(d,"summary",s+" · "+ps.length+"/"+records.length+" postings · "+new Set(ps.map(p=>p.employer)).size+" employers");
      for(const p of ps){const a=add(add(d,"p",""),"a",p.employer+" · "+p.title);if(p.url.startsWith("https://"))a.href=p.url}
    }
    if(!skills.size)add(el("counts"),"p","No tracked mentions in this selection.");
  }el("area").onchange=render;render();
}catch{el("scope").textContent="Market snapshot unavailable."}
