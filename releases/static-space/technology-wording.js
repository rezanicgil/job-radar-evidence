// Match explicit lists in simple requirement wording. Leave mixed or open-ended lists to the reviewer.
export function technologyWording(condition,vocabulary){
  const names=[...new Set([...vocabulary,"RabbitMQ","TensorFlow","C"])].sort((a,b)=>b.length-a.length);
  const term=names.map(s=>s.replace(/[.*+?^${}()|[\]\\]/g,"\\$&")).join("|");
  const group=new RegExp("(?<![\\p{L}\\p{N}+#])(?:"+term+")(?:(?:\\s*,\\s*(?:(?:and|or|veya|ve|ya da)\\s+)?|\\s+(?:and|or|veya|ve|ya da)\\s+)(?:"+term+"))+(?![\\p{L}\\p{N}+#])","iu");
  const text=condition.normalize("NFC").trim().replace(/\s+/gu," ");
  const match=group.exec(text);
  if(!match)return null;
  const prefix=text.slice(0,match.index).trim();
  const suffix=text.slice(match.index+match[0].length).replace(/[.!]?$/u,"").trim();
  const en=/^(?:(?:hands-on |production )?(?:experience|familiarity|proficiency|knowledge) (?:with|in|of)|android development using|build ios screens with)$/iu.test(prefix)
    && /^(?:(?:is|are) (?:required|essential))?$/iu.test(suffix);
  const tr=!prefix&&/^(?:(?:ile|üzerinde) [\p{L} ]+ deneyimi|kullanım deneyimi|bilgisi|deneyimi)$/iu.test(suffix)
    && !/ (?:ve|veya|ya da) /iu.test(" "+suffix+" ");
  if(!en&&!tr&&(prefix||suffix))return null;
  const joins=match[0].match(/\s(?:and|or|veya|ve|ya da)\s/giu)||[];
  const modes=new Set(joins.map(s=>/^(?:or|veya|ya da)$/iu.test(s.trim())?"any":"all"));
  if(modes.size!==1)return null;
  const items=match[0].split(/(?:\s*,\s*(?:(?:and|or|veya|ve|ya da)\s+)?|\s+(?:and|or|veya|ve|ya da)\s+)/iu);
  return {mode:[...modes][0],items};
}

export function hasTechnology(text,name){
  const tokens=text.toLowerCase().match(/[\p{L}\p{N}_+#]+/gu)||[];
  return (" "+tokens.join(" ")+" ").includes(" "+name.toLowerCase()+" ");
}
