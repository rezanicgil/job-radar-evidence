const el=id=>document.getElementById(id);
const examples=["We require [three years] of backend experience.","Taşınma için [iki gün] izin sunuyoruz.","Our company has built web applications for [ten years]."];
let encoder,head;
el("examples").onchange=e=>{el("sentence").value=examples[e.target.selectedIndex];el("result").textContent="Ready."};
el("sentence").oninput=()=>el("result").textContent="Ready.";
el("go").onclick=async()=>{
 const match=/^([^\[\]]*)\[([^\[\]]+)\]([^\[\]]*)$/su.exec(el("sentence").value);
 if(!match||!match[2].trim()){el("result").textContent="Mark exactly one duration in square brackets.";return}
 const words=s=>s.toLowerCase().match(/[\p{L}\p{N}_]+/gu)||[];
 const text=[...words(match[1]).slice(-10),"<duration>",...words(match[3]).slice(0,10)].join(" ");
 for(const id of ["go","examples","sentence"])el(id).disabled=true;
 try{
 el("result").textContent="Loading model and classifying…";
 const {pipeline,env}=await import("https://cdn.jsdelivr.net/npm/@xenova/transformers@2.17.2/dist/transformers.min.js");env.allowLocalModels=false;
 head??=await fetch("duration-head.json").then(r=>{if(!r.ok)throw Error();return r.json()});
 encoder??=await pipeline("feature-extraction","Xenova/paraphrase-multilingual-MiniLM-L12-v2",{revision:"2c4055b12046f11709e9df2c122e59ffbdc2f900",quantized:true});
 const v=(await encoder(text,{pooling:"mean",normalize:true})).data;
 if(v.length!==head.weight.length)throw Error();
 const score=v.reduce((sum,x,i)=>sum+x*head.weight[i],head.bias);
 if(!Number.isFinite(score))throw Error();
 el("result").textContent=score>=0?"Prediction: prior experience":"Prediction: other duration";
 }catch{el("result").textContent="Could not load or run the model. Check your connection and retry."}
 finally{for(const id of ["go","examples","sentence"])el(id).disabled=false}
};
