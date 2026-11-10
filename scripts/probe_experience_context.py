"""Paired duration probe: does a frozen tagger prefer experience to unrelated time?"""
import json
import re
from train_knowledge_spans import ROOT, AutoTokenizer, AutoModelForTokenClassification, torch
from evaluate_job_ner_experience import REPO, REV, hf_hub_download, pq

# Brackets mark the same duration in a requirement and a non-experience context.
CASES = [
 ("android","en","Our Android role requires [three years] writing Kotlin applications.","Our Android team offers a warranty of [three years] for this device."),
 ("android","tr","Android rolümüz Kotlin uygulamaları geliştirmede [üç yıl] deneyim gerektiriyor.","Android ekibimiz bu cihaz için [üç yıl] garanti sunuyor."),
 ("network","en","Candidates should have spent [18 months] maintaining network switches.","Replacement parts remain available for [18 months] after network switches ship."),
 ("network","tr","Ağ anahtarlarının bakımında [18 ay] çalışmış adaylar arıyoruz.","Ağ anahtarları gönderildikten sonra yedek parçalar [18 ay] temin edilebilir."),
 ("data","en","We prefer [two years] administering warehouses with PostgreSQL.","We retain warehouse logs in PostgreSQL for [two years] before deletion."),
 ("data","tr","PostgreSQL ile veri ambarı yönetiminde [iki yıl] deneyim tercih edilir.","Veri ambarı kayıtlarını silmeden önce PostgreSQL üzerinde [iki yıl] tutuyoruz."),
 ("firmware","en","The firmware engineer needs [six months] developing bootloaders.","The firmware team ships a bootloader every [six months] on average."),
 ("firmware","tr","Ürün yazılımı mühendisi için önyükleyici geliştirmede [altı ay] deneyim gerekiyor.","Ürün yazılımı ekibi yeni önyükleyiciyi ortalama [altı ay] arayla yayımlıyor."),
]

def normalize(text):
    return ''.join(re.findall(r'\w+',text.casefold()))

@torch.inference_mode()
def main():
    torch.set_num_threads(4)
    path=ROOT/'runs/job-ner-experience'
    model=AutoModelForTokenClassification.from_pretrained(path).eval()
    tok=AutoTokenizer.from_pretrained(path)
    train=pq.read_table(hf_hub_download(REPO,'data/train-00000-of-00001.parquet',repo_type='dataset',revision=REV),columns=['tokens']).to_pylist()
    seen={normalize(' '.join(r['tokens'])) for r in train}
    def score(source):
        pre,span,post=re.fullmatch(r'(.*?)\[([^\]]+)\](.*)',source).groups()
        text=pre+span+post
        assert normalize(text) not in seen
        words=text.split(); a=len(pre.split()); b=a+len(span.split())
        assert ' '.join(words[a:b])==span
        x=tok(words,is_split_into_words=True,return_tensors='pt')
        probs=model(**x).logits.softmax(-1)[0]
        ids=x.word_ids()
        return float(torch.stack([probs[ids.index(i),1:].sum() for i in range(a,b)]).mean())
    results=[]
    for family,lang,pos,neg in CASES:
        a,b=score(pos),score(neg)
        results.append(dict(family=family,language=lang,experience=a,unrelated=b,correct_order=a>b))
    report=dict(metric="Mean probability of B or I at first subtoken of marked duration words; strict paired comparison",cases=results)
    (ROOT/'reports/experience-context-probe.json').write_text(json.dumps(report,indent=2)+'\n','utf8')
    print({lang:sum(r['correct_order'] for r in results if r['language']==lang) for lang in ('en','tr')})

if __name__=='__main__': main()
