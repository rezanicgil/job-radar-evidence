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
  let translations=[];
  function compareLanguages(card,row){
    const views=translations.filter(v=>v.family===row.family&&v.label===row.label);
    const original=views.find(v=>v.original);
    if(views.length!==4||!original)return;
    const panel=write(card,"details","");
    write(panel,"summary","Compare Turkish and English versions");
    function languagePicker(title,initial){
      const select=write(write(panel,"label",title+" "),"select","");
      select.add(new Option("English","en"));select.add(new Option("Türkçe","tr"));
      select.value=initial;
      return select;
    }
    const job=languagePicker("Job language",original.job_language);
    const cv=languagePicker("CV language",original.cv_language);
    const result=write(panel,"div","");
    result.setAttribute("aria-live","polite");
    function show(){
      const view=views.find(v=>v.job_language===job.value&&v.cv_language===cv.value);
      result.replaceChildren();
      write(result,"p","Job requirement · "+view.requirement);
      write(result,"p","CV passage · "+view.cv_passage);
      write(result,"strong","Model: "+view.prediction+" · Reference: "+view.label);
      const message=view.original?"Original wording.":view.prediction===original.prediction?
        "Same prediction as the original wording.":"Prediction changed from "+original.prediction+" to "+view.prediction+".";
      write(result,"p",message);
    }
    job.onchange=show;cv.onchange=show;show();
  }
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
      compareLanguages(card,row);
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
  try{
    const res=await fetch("model-languages.json");
    if(!res.ok)throw Error();
    const report=await res.json();
    if(report.model!==model)throw Error();
    translations=report.records;
    el("language-note").textContent="Predictions varied across translations in "+report.changed_across_translations+" of "+report.unique_pairs+" cases. Open a passage to compare its four recorded language combinations. Filters use original wording.";
    render();
  }catch{el("language-note").textContent="Translation comparisons are unavailable."}
}catch{el("score").textContent="Model results unavailable. Reload to retry."}
