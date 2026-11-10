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

export const reviewVocabulary=names=>[...new Set([...names,"Node.js",".NET","CI/CD","RabbitMQ","ORM","Prisma","TypeORM","Mongoose","Sequelize","GORM","gRPC"])];
const technologyPatterns=new Map();
export function hasTechnology(text,name){
  if(!name.trim())return false;
  if(!technologyPatterns.has(name)){
    const literal=name.trim().split(/\s+/u).map(x=>x.replace(/[.*+?^\x24{}()|[\]\\]/g,"\\$&")).join("\\s+");
    technologyPatterns.set(name,new RegExp("(?<![\\p{L}\\p{N}_+#])"+literal+"(?![\\p{L}\\p{N}_+#])","iu"));
  }
  return technologyPatterns.get(name).test(text.normalize("NFC"));
}

export function skillsListMention(text){
  const match=/^(?:technical skills|skills|technologies|system design & data|languages & backend|cloud & delivery|ai & tools|teknik beceriler|beceriler|teknolojiler)\s*:\s*(.+)$/iu.exec(text.trim());
  if(!match)return false;
  const items=match[1].replace(/[,;.]$/u,"").split(/[,;]/u).map(s=>s.trim());
  return items.length>=2 && items.every(s=>s.length>0 && s.split(/\s+/u).length<=3);
}
