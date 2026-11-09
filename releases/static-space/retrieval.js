const family=document.getElementById("retrievalFamily");
const languages=document.getElementById("retrievalLanguage");
const result=document.getElementById("retrievalResult");

function add(parent,tag,text){
  const element=document.createElement(tag);
  element.textContent=text;
  parent.append(element);
  return element;
}

try{
  const response=await fetch("retrieval-examples.json");
  if(!response.ok)throw Error();
  const data=await response.json();
  const params=new URLSearchParams(location.search);
  for(const key of Object.keys(data).sort()){
    family.add(new Option(key.replaceAll("-"," "),key));
  }
  family.value=Object.hasOwn(data,params.get("retrieval"))?params.get("retrieval"):"database-stores";
  const view=params.get("view");
  languages.value=Object.hasOwn(data[family.value],view)?view:"tr-tr";
  function render(){
    const row=data[family.value][languages.value];
    result.replaceChildren();
    add(result,"h3","Job requirement");
    add(result,"p",row.requirement);
    add(result,"h3","Reference passage");
    add(result,"p",row.target);
    const grid=add(result,"div","");
    grid.className="rank-grid";
    for(const [key,title] of [["before","Base encoder"],["after","Fine-tuned encoder"]]){
      const card=add(grid,"article","");
      add(card,"h3",title);
      add(card,"p","Reference rank "+row[key].rank+" of 30");
      const list=add(card,"ol","");
      for(const text of row[key].top3){
        const entry=add(list,"li",text);
        if(text===row.target)add(entry,"strong","Reference passage");
      }
    }
    const url=new URL(location.pathname,location.origin);
    url.search=new URLSearchParams({retrieval:family.value,view:languages.value});
    url.hash="retrieval";
    add(result,"a","Link to this comparison").href=url.href;
  }
  family.onchange=languages.onchange=render;
  render();
}catch{result.textContent="Recorded rankings are unavailable. Reload to retry."}
