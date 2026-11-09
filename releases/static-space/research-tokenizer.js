export function researchTokenizer(tokenizer){
  tokenizer.model_max_length=128;
  return (texts,options)=>{
    const batch=tokenizer(texts,options);
    // Transformers.js v2 slices away the separator on long inputs. Python retains it.
    const [rows,width]=batch.input_ids.dims;
    if(width===128)for(let i=0;i<rows;i++){
      const end=(i+1)*width-1;
      if(batch.attention_mask.data[end])batch.input_ids.data[end]=BigInt(tokenizer.sep_token_id);
    }
    return batch;
  };
}

export function passageWindows(text,tokenizer){
  const fits=s=>tokenizer.encode(s).length<=128;
  if(text.length<=768&&fits(text))return [text];
  const chars=Array.from(text);
  const windows=[];
  let start=0;
  while(start<chars.length){
    let lo=start+1,hi=Math.min(start+768,chars.length);
    while(lo<hi){
      const mid=Math.ceil((lo+hi)/2);
      if(fits(chars.slice(start,mid).join("")))lo=mid;
      else hi=mid-1;
    }
    let end=lo;
    if(end<chars.length){
      for(let j=end;j>start+(end-start)/2;j--){
        if(/\s/u.test(chars[j])){end=j;break}
      }
    }
    const piece=chars.slice(start,end).join("").trim();
    if(piece)windows.push(piece);
    if(end===chars.length)break;
    start=end-Math.floor((end-start)/4);
  }
  if(windows.length>1){
    for(const clause of text.split(/[,;:]/u).map(s=>s.trim())){
      if(clause.split(/\s+/u).length>=4&&clause.length<=768&&fits(clause))windows.push(clause);
    }
  }
  return [...new Set(windows)];
}
