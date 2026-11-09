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
