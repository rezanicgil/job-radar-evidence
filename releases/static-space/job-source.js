export function sourceUrl(value){
  if(typeof value!=="string"||!value.trim())return null;
  try{
    const url=new URL(value.trim());
    return ["http:","https:"].includes(url.protocol)&&!url.username&&!url.password?url.href:null;
  }catch{return null}
}
