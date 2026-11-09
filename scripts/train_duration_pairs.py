"""Check whether bilingual, rule-labeled duration contrasts transfer to existing development sets."""

import hashlib
import json

import torch
from train_pair_encoder import BASE, REVISION, ROOT, AutoTokenizer, run


def duration_rows():
    for skill in ("Kotlin","Swift","Zephyr","Rust","Elixir","Dart","OpenCV","Qt"):
        for required in (2,3,5):
            for months in (12,24,36,60):
                for job_lang in ("en","tr"):
                    requirement = (f"At least {required} years developing software with {skill}."
                                   if job_lang=="en" else f"{skill} ile en az {required} yıl yazılım geliştirme deneyimi.")
                    for cv_lang in ("tr","en"):
                        experience = (f"{months} ay boyunca {skill} kullanarak yazılım geliştirdim." if cv_lang=="tr"
                                      else f"I developed software using {skill} for {months} months.")
                        unrelated = (f"{months} ay boyunca {skill} kurslarının faturalarını düzenledim." if cv_lang=="tr"
                                     else f"I processed invoices for {skill} courses for {months} months.")
                        for passage,label in ((experience,"supported" if months>=12*required else "partial"),
                                              (unrelated,"unverified")):
                            yield dict(family=f"duration-{skill}",requirement=requirement,cv_passage=passage,
                                       label=label,job_language=job_lang,cv_language=cv_lang)


def main():
    torch.set_num_threads(4)
    root=ROOT/"releases/match-pilot"
    paths={name:root/(name+".jsonl") for name in ("train","validation","source_validation")}
    rows={name:[json.loads(s) for s in p.read_text(encoding="utf-8").splitlines()] for name,p in paths.items()}
    generated=list(duration_rows())
    payload="".join(json.dumps(r,ensure_ascii=False)+"\n" for r in generated).encode("utf-8")
    (ROOT/"data/match_duration_weak.jsonl").write_bytes(payload)
    train=rows["train"]+generated
    eval_rows=rows["validation"]+rows["source_validation"]
    for field in ("family","cv_passage","requirement"):
        assert {r[field] for r in train}.isdisjoint(r[field] for r in eval_rows)
    tokenizer=AutoTokenizer.from_pretrained(BASE,revision=REVISION)
    result=run(train,eval_rows,tokenizer,True,"duration-weak")
    report=dict(base=BASE,revision=REVISION,seed=17,epochs=6,batch_size=6,
                generated_pairs=len(generated),training_pairs=len(train),
                generated_sha256=hashlib.sha256(payload).hexdigest(),
                file_hashes={name:hashlib.sha256(p.read_bytes()).hexdigest() for name,p in paths.items()},
                splits={})
    offset=0
    for name in ("validation","source_validation"):
        examples=rows[name]
        predictions=result["predictions"][offset:offset+len(examples)]
        pairs=[(r["label"],p) for r,p in zip(examples,predictions,strict=True)]
        metrics=dict(correct=sum(a==p for a,p in pairs),total=len(pairs),
                     partial_found=pairs.count(("partial","partial")),
                     false_support=sum(a!="supported" and p=="supported" for a,p in pairs))
        report["splits"][name]=dict(**metrics,predictions=predictions)
        offset+=len(examples)
        print(name,metrics)
    (ROOT/"reports/duration-weak.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")


if __name__=="__main__":
    main()
