export function durationConstraintNote(text){
  const amount=String.raw`(?:\d+(?:[.,]\d+)?|one|two|three|four|five|six|ten|bir|iki|üç|dört|beş|altı|on)`;
  const unit=String.raw`(?:years?|months?|yıl(?:lık)?|sene|ay(?:lık)?)`;
  const recent=new RegExp(String.raw`(?<![\p{L}\d])(?:in (?:the )?(?:past|last) ${amount}\s+(?:days?|weeks?|months?)|son\s+${amount}\s+(?:gün|hafta|ay)(?:de|da|te|ta|\s+içinde)?)(?!\p{L})`,"iu").exec(text);
  if(recent && /\b(?:deployed|released|shipped|delivered)\b|yay[ıi]mlad|yay[ıi]nlad|üretime (?:al|çık)|canlıya (?:al|çık)/iu.test(text))
    return "Recent work · "+recent[0]+". Cite a dated example of the requested action. This window is not a minimum length of experience. Review any other time condition separately.";
  if(!/experience|deneyim|tecrübe/iu.test(text))return null;
  const range=new RegExp(String.raw`(?<![\p{L}\d])${amount}\s*(?:[-–—]|to|ile|ila)\s*${amount}\s+${unit}(?!\p{L})`,"iu").exec(text);
  if(range)return "Experience range · "+range[0]+". The higher endpoint is not the minimum. Check which experience counts, including any internship wording.";
  const upper=new RegExp(String.raw`(?<![\p{L}\d])(?:(?:up to|at most|no more than|en fazla)\s+${amount}\s+${unit}|${amount}\s+(?:yıla|aya|seneye)\s+kadar)(?!\p{L})`,"iu").exec(text);
  const amounts=[...text.matchAll(new RegExp(String.raw`(?<![\p{L}\d])${amount}\+?\s+${unit}(?!\p{L})`,"giu"))];
  if(amounts.length>1)return "Multiple durations · "+amounts.map(m=>m[0]).join(" / ")+". Check what each duration refers to. If they describe separate requirements, enter each on its own line with its scope; overlapping periods can count toward both.";
  return upper?"Upper limit · "+upper[0]+". Do not treat this as a minimum. Check whether the condition is required or preferred.":null;
}
