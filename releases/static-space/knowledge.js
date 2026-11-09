const el=id=>document.getElementById(id);
function add(parent,tag,text){
  const node=document.createElement(tag);
  node.textContent=text;
  parent.append(node);
  return node;
}
function highlight(parent,title,text,spans){
  add(parent,"strong",title+" · "+spans.length+" phrase"+(spans.length===1?"":"s"));
  const paragraph=add(parent,"p","");
  const chars=Array.from(text);
  let start=0;
  for(const span of spans){
    paragraph.append(chars.slice(start,span.start).join(""));
    add(paragraph,"mark",chars.slice(span.start,span.end).join(""));
    start=span.end;
  }
  paragraph.append(chars.slice(start).join(""));
}
try{
  const response=await fetch("knowledge-examples.json");
  if(!response.ok)throw Error("Examples unavailable");
  const rows=await response.json();
  const names={"android":"Android","ios":"iOS","firmware":"Firmware","toolchain":"Development tools","mobile":"Mobile apps",
    "visualization":"Data visualization","systems":"Systems programming","open-list":"Language alternatives",
    "benefits":"Employee benefits","location":"Work location"};
  for(const family of new Set(rows.map(r=>r.family)))el("knowledgeFamily").add(new Option(names[family]||family,family));
  function show(){
    const row=rows.find(r=>r.family===el("knowledgeFamily").value&&r.language===el("knowledgeLanguage").value);
    const panel=el("knowledgeResult");
    panel.replaceChildren();
    highlight(panel,"Job Radar MiniLM",row.text,row.predicted);
    highlight(panel,"Published JobBERT",row.text,row.jobbert);
    highlight(panel,"Reference",row.text,row.knowledge_spans);
    if(row.source_url)add(panel,"a","Employer posting").href=row.source_url;
  }
  el("knowledgeFamily").onchange=show;
  el("knowledgeLanguage").onchange=show;
  show();
}catch{el("knowledgeResult").textContent="Knowledge examples are unavailable."}
