"""Measure zero-shot evidence classification under two label orders."""

import json
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


ROOT = Path(__file__).resolve().parents[1]
MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
REVISION = "7ae557604adf67be50417f59c2c2f167def9a775"
DEFINITIONS = {
    "supported": "The applicant's own work demonstrates the entire requirement.",
    "partial": "The applicant demonstrates some but not all of the requirement.",
    "unverified": "The passage gives no evidence of the applicant meeting this requirement.",
}


@torch.inference_mode()
def main():
    torch.set_num_threads(4)
    rows = [json.loads(line) for line in (ROOT / "data/match_source_dev.jsonl").read_text(
        encoding="utf-8").splitlines()]
    tokenizer = AutoTokenizer.from_pretrained(MODEL, revision=REVISION)
    model = AutoModelForCausalLM.from_pretrained(MODEL, revision=REVISION, torch_dtype=torch.float32).eval()
    tokenizer.pad_token = tokenizer.eos_token
    letters = "ABC"
    tokens = [tokenizer.encode(letter, add_special_tokens=False) for letter in letters]
    assert all(len(ids) == 1 for ids in tokens)
    predictions = []
    for order in [list(DEFINITIONS), list(reversed(DEFINITIONS))]:
        options = "\n".join(f"{letter}. {DEFINITIONS[label]}" for letter, label in zip(letters, order))
        answers = []
        for start in range(0, len(rows), 4):
            prompts = []
            for row in rows[start:start+4]:
                prompt = (f"Classify the CV evidence for this job requirement. Answer A, B or C.\n{options}"
                          f"\nRequirement: {row['requirement']}\nCV: {row['cv_passage']}")
                prompts.append(tokenizer.apply_chat_template([{"role":"user","content":prompt}],
                              tokenize=False, add_generation_prompt=True))
            inputs = tokenizer(prompts, return_tensors="pt", padding=True, add_special_tokens=False)
            logits = model(**inputs).logits[torch.arange(len(prompts)), inputs.attention_mask.sum(1)-1]
            answers.extend(order[i] for i in logits[:, [ids[0] for ids in tokens]].argmax(1).tolist())
        predictions.append(answers)
    result = {"model":MODEL,"revision":REVISION,"orders":[list(DEFINITIONS),list(reversed(DEFINITIONS))],
              "correct":[sum(pred==row["label"] for pred,row in zip(run,rows)) for run in predictions],
              "changed":sum(a!=b for a,b in zip(*predictions)),
              "cases":[{"source_fingerprint":row["source_fingerprint"],"expected":row["label"],
                        "predictions":list(pair)} for row,pair in zip(rows,zip(*predictions))]}
    (ROOT / "reports/instruction-baseline.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(result["correct"],result["changed"])


if __name__ == "__main__":
    main()
