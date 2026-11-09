const el=id=>document.getElementById(id);
function write(parent,tag,text){
  const child=document.createElement(tag);
  child.textContent=text;parent.append(child);return child;
}
try{
  const response=await fetch("model-examples.json");
  if(!response.ok)throw Error();
  const {examples,model}=await response.json();
  const [repo,revision]=model.split("@");
  el("model").href="https://huggingface.co/"+repo+"/tree/"+revision;
  const correct=examples.filter(r=>r.prediction===r.label).length;
  el("score").textContent=correct+"/"+examples.length+" predictions matched the reference label ("+(100*correct/examples.length).toFixed(1)+"%) on this synthetic development set.";
  function filtered(){
    const kind=el("filter").value;
    return examples.filter(r=>kind==="all"||(kind==="false"&&r.prediction==="supported"&&r.label!=="supported")
      ||(kind==="partial"&&r.label==="partial"&&r.prediction!==r.label)||(kind==="correct"&&r.prediction===r.label));
  }
  function render(){
    const rows=filtered();
    const selected=rows.filter(r=>r.family===el("family").value);
    const section=el("examples");
    section.replaceChildren();
    write(section,"p",rows.length+" of "+examples.length+" examples match this filter.");
    if(!selected.length)return;
    write(section,"h2",selected[0].requirement);
    write(section,"a",selected[0].source.employer+" · "+selected[0].source.title).href=selected[0].source.url;
    for(const row of selected){
      const card=write(section,"article","");
      write(card,"p",row.cv_passage);
      write(card,"strong","Model: "+row.prediction+" · Reference: "+row.label);
    }
  }
  function update(){
    const previous=el("family").value;
    const families=new Map(filtered().map(r=>[r.family,r]));
    el("family").replaceChildren();
    for(const [family,row] of families)el("family").add(new Option(row.source.employer+" · "+row.requirement,family));
    if(families.has(previous))el("family").value=previous;
    render();
  }
  el("filter").onchange=update;el("family").onchange=render;update();
}catch{el("score").textContent="Model results unavailable. Reload to retry."}
