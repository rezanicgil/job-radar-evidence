const el=id=>document.getElementById(id);
const add=(parent,tag,text)=>{const node=document.createElement(tag);node.textContent=text;parent.append(node);return node};
const words=text=>new Set(text.toLocaleLowerCase().match(/[\p{L}\p{N}+#]+/gu)||[]);
let encoder;
let vocabulary;
let sentenceModel;
const selectedPreferences=new Set();
const downloadReview=document.createElement("button");
downloadReview.type="button";
downloadReview.textContent="Download review (.txt)";
downloadReview.hidden=true;
el("status").after(downloadReview);
let reviewVersion=0;
const jobOrigin=document.createElement("p");
el("job").parentElement.before(jobOrigin);
function clearJobOrigin(){jobOrigin.replaceChildren()}
el("job").addEventListener("input",()=>{
  clearJobOrigin();
  const present=new Set(el("job").value.split(/\n/).map(s=>s.trim()));
  for(const s of selectedPreferences)if(!present.has(s))selectedPreferences.delete(s);
});
function offerReviewedConditions(card,posting,conditions){
  const button=add(card,"button","Review these conditions with my CV");
  button.type="button";
  const replace=add(card,"div","");
  replace.hidden=true;
  add(replace,"p","Replacing the job conditions will clear the current review. Your CV stays in the form.");
  const accept=add(replace,"button","Replace conditions");
  const cancel=add(replace,"button","Keep current review");
  accept.type=cancel.type="button";
  cancel.onclick=()=>{replace.hidden=true;button.focus()};
  function usePosting(){
    const text=conditions.join("\n");
    replace.hidden=true;
    el("job").value=text;
    selectedPreferences.clear();
    clearJobOrigin();
    jobOrigin.append("Selected requirements from ");
    add(jobOrigin,"a",posting.employer+" · "+posting.title).href=posting.source_url;
    jobOrigin.append(". Coverage applies only to the conditions below.");
    el("posting").value="";
    el("candidates").replaceChildren();
    el("append").hidden=true;
    invalidateReview();
    location.hash="review";
    if(el("cv").value.trim()||el("file").files.length)el("find").focus();
    else el("cv").focus();
  }
  accept.onclick=usePosting;
  button.onclick=()=>{
    if(el("job").value.trim()||el("posting").value.trim()){
      replace.hidden=false;cancel.focus();
    }else usePosting();
  };
}
function invalidateReview(){
  reviewVersion++;
  downloadReview.hidden=true;
  el("example").hidden=Boolean(el("cv").value||el("job").value||el("file").files.length||el("posting").value);
  const hasReview=el("results").children.length||el("find").disabled;
  el("source").textContent="";
  el("results").replaceChildren();
  el("status").textContent=hasReview?"Inputs changed. Find evidence again to update the review.":"";
}
for(const id of ["cv","job"])el(id).addEventListener("input",invalidateReview);
el("method").addEventListener("change",invalidateReview);
el("file").onchange=()=>{
  const usingFile=Boolean(el("file").files[0]);
  el("cv").disabled=usingFile;
  el("removeFile").hidden=!usingFile;
  invalidateReview();
};
el("removeFile").onclick=()=>{el("file").value="";el("file").onchange()};
el("posting").oninput=()=>{el("candidates").replaceChildren();el("append").hidden=true;el("example").hidden=Boolean(el("cv").value||el("job").value||el("file").files.length||el("posting").value)};
el("postingLanguage").onchange=()=>el("posting").oninput();
function turkishCandidates(text){
  let section="unknown";
  const candidates=new Map();
  for(const raw of text.split(/\r?\n/)){
    const line=raw.trim().replace(/^[•*–-]\s*/,"");
    if(!line)continue;
    const key=line.toLocaleLowerCase("tr").replace(/[:?]\s*$/,"").trim();
    if(/^(genel nitelikler(?: ve iş tanımı)?|aranan (?:nitelikler|özellikler)|(?:asgari|minimum|teknik) (?:nitelikler|gereksinimler)|gereksinimler|yetkinlikler)$/.test(key)){section="qualification";continue}
    if(/^(?:tercihen|tercih edilen (?:nitelikler|özellikler)|tercih nedeni olabilecek ek nitelikler|ek nitelikler)$/.test(key)){section="preference";continue}
    if(/^(?:iş tanımı|görev tanımı|sorumluluklar|görev ve sorumluluklar|seni neler bekliyor|biz kimiz|yan haklar|sunduğumuz olanaklar|başvur(?:u)?|başvuru süreci|iletişim|iletişime geçin|hakkımızda)$/.test(key)||line.endsWith(":")){section="other";continue}
    if(/^(?:çalışma yeri|pozisyonun lokasyonu)\s/.test(key) ||
       (/@/.test(key) && /gönder|başvur|ilet/.test(key)))continue;
    const optional=/tercihen|tercih (?:sebebi|nedenidir|edilir)|artı (?:olur|sayılır)/.test(key);
    if(section==="other" || (section==="unknown" && !optional && !/deneyim|tecrüb|hakimiyet|hâkimiyet|bilgi sahibi|zorunlu|aranmaktadır/.test(key)))continue;
    candidates.set(line,optional||section==="preference");
  }
  return candidates;
}
el("example").onclick=()=>{
  el("cv").value="C++ ile 30 ay boyunca motor kontrol yazılımı geliştirdim.\nPython ile test raporları hazırladım.";
  el("job").value="At least 36 months developing control software with C++.\nWrite test reports using Python.";
  invalidateReview();
  el("form").requestSubmit();
};
el("suggest").onclick=async()=>{
  const output=el("candidates");
  output.replaceChildren();
  el("append").hidden=true;
  const text=el("posting").value.trim();
  const language=el("postingLanguage").value;
  if(!text || text.length>100000){output.textContent="Enter a posting of up to 100,000 characters.";return}
  el("suggest").disabled=true;
  try{
    if(language==="en" && !sentenceModel){
      const response=await fetch("skill-sentences.json");
      if(!response.ok)throw Error();
      sentenceModel=await response.json();
    }
    if(el("posting").value.trim()!==text||el("postingLanguage").value!==language)return;
    const suggestions=language==="tr"?turkishCandidates(text):new Map();
    if(language==="en")for(const sentence of new Set(text.split(/\n+|(?<=[.!?])\s+/).map(s=>s.trim()).filter(Boolean))){
      const terms=sentence.toLowerCase().match(/[\p{L}\p{N}_+#]+/gu)||[];
      const value=terms.reduce((sum,term)=>sum+(Object.hasOwn(sentenceModel.weights,term)?sentenceModel.weights[term]:0),sentenceModel.bias);
      if(value<sentenceModel.threshold)continue;
      suggestions.set(sentence,false);
    }
    for(const [sentence,optional] of suggestions){
      const label=add(output,"label","");
      const input=add(label,"input","");input.type="checkbox";input.value=sentence;
      input.dataset.preference=String(optional);
      label.append((optional?" Preference · ":" ")+sentence);
    }
    el("append").hidden=!output.children.length;
    if(!output.children.length)output.textContent="No suggestions found. Enter conditions below.";
  }catch{output.textContent="Suggestions unavailable. Enter conditions below."}
  finally{el("suggest").disabled=false}
};
el("append").onclick=()=>{
  const fields=el("job");
  const prior=fields.value.split(/\n/).map(s=>s.trim()).filter(Boolean);
  const checked=[...el("candidates").querySelectorAll(":checked")];
  const selected=checked.map(input=>input.value);
  if(!selected.length)return;
  const combined=new Set([...(fields.value===fields.defaultValue?[]:prior),...selected]);
  if(combined.size>50){el("status").textContent="Select up to 50 conditions.";return}
  for(const input of checked){
    if(input.dataset.preference==="true")selectedPreferences.add(input.value);
    else selectedPreferences.delete(input.value);
  }
  fields.value=[...combined].join("\n");
  clearJobOrigin();
  invalidateReview();
};
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
const numberWords=new Map(Object.entries({
  one:1,two:2,three:3,four:4,five:5,six:6,ten:10,thirty:30,
  bir:1,iki:2,"üç":3,"dört":4,"beş":5,"altı":6,on:10,otuz:30
}));
function statedDuration(text){
  // Skip ranges, approximations and compound amounts rather than picking one endpoint.
  if(/\d\s*[-–]\s*\d|\b(?:about|nearly|almost|roughly|approximately|between|less than|up to)\b|yaklaşık|yaklasik|arasında|en fazla/i.test(text))return null;
  const pattern=/(?<![\p{L}\p{N}.,])([\p{L}]+|\d+(?:[.,]\d+)?)(\s+(?:buçuk|and a half))?\s*\+?\s+(years?|months?|yıl(?:lık)?|sene(?:lik)?|ay(?:lık)?)(?!\p{L})/giu;
  const matches=[...text.matchAll(pattern)];
  if(matches.length!==1)return null;
  const [match]=matches;
  const word=match[1].toLowerCase();
  const preceding=text.slice(0,match.index).trimEnd().split(/\s+/).pop()?.toLowerCase();
  if(numberWords.has(preceding)||/(?:[-–]|\b(?:twenty|thirty|forty|fifty|sixty|yirmi|kırk|elli)|\d+\s+to)\s*$/iu.test(text.slice(0,match.index)))return null;
  const value=numberWords.get(word)??Number(word.replace(",","."));
  if(!Number.isFinite(value)||value<=0)return null;
  const years=/^(year|yıl|sene)/iu.test(match[3]);
  return {phrase:match[0],months:Math.round((value+(match[2]?0.5:0))*(years?12:1)*100)/100};
}
function durationComparison(card,condition,lines){
  const target=statedDuration(condition);
  if(!target)return;
  const matches=lines.filter(line=>!/(?:\d\s*\+|\bat least\b|\bmore than\b|en az|üzeri(?!\p{L})|yılı aşkın)/iu.test(line.text))
    .map(line=>({line,duration:statedDuration(line.text)})).filter(x=>x.duration);
  if(!matches.length)return;
  const panel=add(card,"details","");
  add(panel,"summary","Compare stated durations");
  add(panel,"p","Use this comparison when the condition specifies a minimum. Choose a CV passage about the same work.");
  const picker=add(add(panel,"label","CV passage "),"select","");
  picker.add(new Option("Select a passage",""));
  matches.forEach(({line},i)=>picker.add(new Option("Page "+line.page+" · "+line.text,String(i))));
  const output=add(panel,"p","");output.className="duration-result";output.setAttribute("aria-live","polite");
  picker.onchange=()=>{
    if(!picker.value){output.textContent="";return}
    const {line,duration}=matches[Number(picker.value)];
    const gap=Math.round((duration.months-target.months)*100)/100;
    output.textContent="Page "+line.page+" · "+line.text+" | CV: "+duration.months+" months · minimum: "+target.months+" months · "+
      (gap===0?"equal duration":Math.abs(gap)+" months "+(gap<0?"below":"above")+" the minimum")+".";
  };
}
function addEvidencePicker(card,lines,suggestions){
  const panel=add(card,"div","");
  panel.hidden=true;
  add(panel,"p","Select the CV passage or passages that support this assessment.");
  function addChoice(parent,line){
    const label=add(parent,"label","");
    const input=add(label,"input","");
    input.type="checkbox";
    input.className="evidence";
    input.value="Page "+line.page+" · "+line.text;
    label.append(" "+input.value);
    input.onchange=coverage;
  }
  for(const line of suggestions)addChoice(panel,line);
  const others=lines.filter(line=>!suggestions.includes(line));
  if(others.length){
    const details=add(panel,"details","");
    add(details,"summary","Browse "+others.length+" other CV passages");
    details.ontoggle=()=>{
      if(!details.open)return;
      details.ontoggle=null;
      for(const line of others)addChoice(details,line);
    };
  }
  return panel;
}
function assessmentRows(){
  return [...el("results").querySelectorAll("article")].map(card=>{
    const label=card.querySelector(".assessment").value;
    const quotes=[...card.querySelectorAll(".evidence:checked")].map(input=>input.value);
    const needsQuote=label==="partial"||label==="supported";
    const note=card.querySelector(".gap-note");
    return {condition:card.querySelector("h3").textContent,label,quotes,
            note:note.disabled?"":note.value.trim(),duration:card.querySelector(".duration-result")?.textContent||"",
            complete:Boolean(label)&&(!needsQuote||quotes.length>0)};
  });
}
downloadReview.onclick=()=>{
  const rows=assessmentRows();
  if(!rows.length||rows.some(row=>!row.complete))return;
  const heading=[...el("status").children].map(child=>child.textContent).join("\n")||el("status").textContent;
  const origin=jobOrigin.querySelector("a");
  const context=origin?"Selected requirements from "+origin.textContent+"\n"+origin.href+"\nCoverage applies only to the selected conditions.":"";
  const body=["Job Radar Evidence",el("source").textContent,context,heading,...rows.map(row=>
    [row.condition,"Assessment: "+row.label,...row.quotes,row.duration,
     row.note?"Next CV edit: "+row.note:""].filter(Boolean).join("\n"))].join("\n\n");
  const url=URL.createObjectURL(new Blob([body+"\n"],{type:"text/plain;charset=utf-8"}));
  const link=document.createElement("a");
  link.href=url;link.download="job-radar-review.txt";link.click();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
};
function coverage(){
  const rows=assessmentRows();
  const values=rows.map(row=>row.complete?row.label:"");
  downloadReview.hidden=!values.length||values.includes("");
  const status=el("status");
  status.replaceChildren();
  if(values.includes("")){
    const completed=values.filter(Boolean).length;
    add(status,"strong",Math.round(100*completed/values.length)+"% reviewed");
    add(status,"span",completed+" of "+values.length+" conditions reviewed. Choose an assessment and attach evidence for supported or partial conditions.");
    return;
  }
  const n=values.filter(v=>v!=="skip").length,s=values.filter(v=>v==="supported").length;
  if(!n){status.textContent="No required conditions selected.";return}
  add(status,"strong",Math.round(100*s/n)+"% coverage");
  add(status,"span",s+" of "+n+" required conditions fully supported by your CV, as reviewed.");
  add(status,"span",values.filter(v=>v==="partial").length+" partial · "+values.filter(v=>v==="unverified").length+" unverified · "+(values.length-n)+" excluded");
}
el("form").onsubmit=async event=>{
  event.preventDefault();el("find").disabled=true;el("results").replaceChildren();
  downloadReview.hidden=true;
  const version=++reviewVersion;
  const file=el("file").files[0];
  el("source").textContent="";
  el("status").textContent="Reading CV…";
  try{
    const pages=await readPages(file);
    if(version!==reviewVersion)return;
    const isPdf=/\.pdf$/i.test(file?.name || "");
    const lines=pages.flatMap((p,i)=>pagePassages(p,isPdf).map(text=>({text,page:i+1})));
    const job=[...new Set(el("job").value.split(/[\r\n]+/).map(x=>x.trim()).filter(Boolean))];
    if(!lines.length)throw Error("Enter CV text or choose a PDF with selectable text.");
    if(!job.length||job.length>50)throw Error("Enter 1–50 distinct conditions, one per line.");
    if(lines.length>800)throw Error("Use a shorter CV with up to 800 passages.");
    el("status").textContent="Finding passages…";
    const semantic=el("method").value==="semantic";
    const vec=semantic?await vectors([...job,...lines.map(x=>x.text)]):null;
    if(semantic && !vocabulary){
      const response=await fetch("technologies.json");
      if(response.ok)vocabulary=await response.json();
    }
    if(version!==reviewVersion)return;
    el("source").textContent=(file?file.name:"Pasted CV")+" · "+job.length+" job condition"+(job.length===1?"":"s")+" · "+(semantic?"Semantic search":"Shared terms");
    job.forEach((condition,i)=>{
      const terms=words(condition);
      const ranked=lines.map((line,j)=>({line,score:semantic?vec[i].reduce((s,v,k)=>s+v*vec[job.length+j][k],0):[...words(line.text)].filter(t=>terms.has(t)).length}))
        .filter(x=>semantic||x.score>0).sort((a,b)=>b.score-a.score).slice(0,3);
      const card=add(el("results"),"article","");add(card,"h3",condition);
      const visible=ranked.map(item=>item.line);
      for(const {line} of ranked)add(card,"p","Page "+line.page+" · "+line.text);
      if(semantic){
        const requested=(vocabulary||[]).filter(name=>hasTechnology(condition,name));
        for(const name of requested){
          if(visible.some(line=>hasTechnology(line.text,name)))continue;
          const mention=lines.find(line=>hasTechnology(line.text,name));
          if(!mention)continue;
          add(card,"small",name+" mentioned on page "+mention.page+" · "+mention.text);
          visible.push(mention);
        }
      }
      if(!ranked.length)add(card,"p","No shared terms found. Review the CV directly.");
      durationComparison(card,condition,lines);
      const select=add(add(card,"label","Assessment "),"select","");
      select.className="assessment";
      for(const [value,label] of [["","Choose"],["supported","Required · supported"],["partial","Required · partial"],["unverified","Required · unverified"],["skip","Exclude from required coverage"]])select.add(new Option(label,value));
      if(selectedPreferences.has(condition))select.value="skip";
      const picker=addEvidencePicker(card,lines,visible);
      const advice=add(card,"small","");
      const noteLabel=add(card,"label","What could you clarify in your CV? (optional)");
      const note=add(noteLabel,"textarea","");note.className="gap-note";
      noteLabel.hidden=true;note.disabled=true;
      select.onchange=()=>{
        picker.hidden=!(select.value==="supported"||select.value==="partial");
        if(picker.hidden)for(const input of picker.querySelectorAll(":checked"))input.checked=false;
        noteLabel.hidden=!(select.value==="partial"||select.value==="unverified");
        note.disabled=noteLabel.hidden;
        advice.textContent=({partial:"Identify which part your CV demonstrates and which part needs an example.",unverified:"If you have relevant experience, describe the work you personally did."})[select.value]||"";
        coverage();
      };
    });coverage();
  }catch(error){if(version===reviewVersion){el("results").replaceChildren();el("source").textContent="";el("status").textContent=error.message}}
  finally{el("find").disabled=false}
};
try{
  const market=await (await fetch("market.json")).json();
  if(market.boards){
    const boards=market.boards;
    const details=document.createElement("details");
    el("scope").after(details);
    add(details,"summary",boards.filter(board=>board.available).length+" of "+boards.length+" tracked employer boards responded");
    for(const board of boards)add(details,"div",board.employer+" · "+(board.available?"responded":"unavailable"));
  }
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
        offerReviewedConditions(card,review,[review.requirement_evidence]);
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
        if(row.minimum_technical?.length)add(card,"p","Selected minimum qualifications: "+row.minimum_technical.join("; "));
        if(row.preferred_technical?.length)add(card,"p","Selected preferences: "+row.preferred_technical.join("; "));
        if(row.minimum_technical?.length)offerReviewedConditions(card,row,row.minimum_technical);
      }
    }
    el("scope").textContent=market.collected_at.slice(0,10)+" · "+records.length+" readable descriptions of "+group.length+" selected postings. Counts include mentions in preferences and company context.";
    const skills=new Map();
    for(const p of records)for(const s of new Set(p.skills)){if(!skills.has(s))skills.set(s,[]);skills.get(s).push(p)}
    el("counts").replaceChildren();
    for(const [s,ps] of [...skills].sort((a,b)=>b[1].length-a[1].length||a[0].localeCompare(b[0]))){
      const d=add(el("counts"),"details","");
      const share=Math.round(1000*ps.length/records.length)/10;
      const summary=add(d,"summary",s+" · "+share+"% · "+ps.length+"/"+records.length+" postings · "+new Set(ps.map(p=>p.employer)).size+" employers");
      const bar=add(summary,"progress","");bar.max=records.length;bar.value=ps.length;bar.setAttribute("aria-hidden","true");
      for(const p of ps){const a=add(add(d,"p",""),"a",p.employer+" · "+p.title);if(p.url.startsWith("https://"))a.href=p.url}
    }
    if(!skills.size)add(el("counts"),"p","No tracked mentions in this selection.");
  }el("area").onchange=render;render();
}catch{el("scope").textContent="Market snapshot unavailable."}
try{
  const history=await (await fetch("market-history.json")).json();
  const container=el("history");
  add(container,"h2","Daily observations · all tracked roles");
  add(container,"p",history.length===1?"One collection date is available.":"Each date uses the last collection that day in Türkiye. Source coverage can change between dates.");
  const picker=add(add(container,"label","Technology "),"select","");
  const technologies=[...new Set(history.flatMap(day=>Object.keys(day.mentions)))].sort();
  for(const name of technologies)picker.add(new Option(name,name));
  if(technologies.includes("Python"))picker.value="Python";
  const days=add(container,"div","");
  function showHistory(){
    days.replaceChildren();
    for(const day of [...history].reverse()){
      const count=day.mentions[picker.value]||0;
      const share=day.readable?(100*count/day.readable).toFixed(1)+"%":"Unavailable";
      const row=add(days,"article","");
      add(row,"strong",day.date+" · "+share+" · "+count+"/"+day.readable+" readable postings");
      add(row,"p",day.employers+" employers represented · "+day.boards_ok+"/"+day.boards_total+" boards responded · "+day.readable+"/"+day.selected+" descriptions readable");
      add(row,"a","Inspect source records").href="https://github.com/rezanicgil/job-radar-evidence/blob/main/reports/"+encodeURIComponent(day.file);
    }
  }
  picker.onchange=showHistory;showHistory();
}catch{el("history").textContent="Daily observations unavailable."}
