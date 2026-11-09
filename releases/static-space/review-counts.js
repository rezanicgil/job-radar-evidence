export function counts(values){
  const required=values.filter(v=>v!=="skip").length;
  const supported=values.filter(v=>v==="supported").length;
  return {required,supported,partial:values.filter(v=>v==="partial").length,
          unverified:values.filter(v=>v==="unverified").length,excluded:values.length-required,
          percentage:required?Math.round(100*supported/required):null};
}
