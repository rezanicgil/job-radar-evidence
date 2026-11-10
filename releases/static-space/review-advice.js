import {hasTechnology,skillsListMention} from "./technology-wording.js";

export function nextEdit(row,names=[]){
  if(!["partial","unverified"].includes(row.label))return "";
  if(row.note)return row.note;
  const gap=row.missing||row.condition||"this requirement";
  if(row.label==="unverified")return "If you have done work relevant to “"+gap+"”, describe one task you personally completed. Otherwise leave this condition unverified.";
  const quotes=row.quotes||[];
  if(quotes.length && quotes.every(q=>skillsListMention(q.passage))){
    const shared=names.filter(n=>hasTechnology(row.condition||"",n)&&quotes.some(q=>hasTechnology(q.excerpt||q.passage,n)));
    return "Your selected evidence is a skills list. If applicable, add a project bullet describing how you used "+(shared.join(" / ")||"the listed skill")+" and what your work produced.";
  }
  return row.missing?"If you can document “"+gap+"”, add the specific task or result that demonstrates it.":"Clarify the part your evidence does not cover.";
}
