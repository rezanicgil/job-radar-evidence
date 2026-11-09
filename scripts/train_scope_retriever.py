"""One fixed contrastive adaptation on six technologies outside the scope evaluation."""
import random

import torch
import torch.nn.functional as F


def training_examples():
    for skill in ("Redis", "Zephyr", "Terraform", "Swift", "Docker", "Kafka"):
        for years in (2, 4):
            queries = (f"We require {years} years working with {skill}.",
                       f"{skill} kullanarak {years} yıl çalışma deneyimi arıyoruz.")
            for query in queries:
                yield (query, f"I used {skill} to troubleshoot releases for 18 months.",
                       f"I translated books on working with {skill} for {years} years.")
                yield (query, f"18 ay boyunca sürüm sorunlarını {skill} kullanarak giderdim.",
                       f"{years} yıl boyunca {skill} kullanımı hakkındaki kitapları çevirdim.")
                yield (query, f"For 30 months I resolved incidents using {skill}.",
                       f"I spent {years} years managing incidents with Ruby and attended a {skill} talk.")
                yield (query, f"30 ay boyunca sorunları {skill} ile çözdüm.",
                       f"{years} yıl Ruby ile sorun çözdüm ve bir {skill} sunumuna katıldım.")


def adapt_last_layer(model, tokenizer):
    torch.manual_seed(17)
    model.requires_grad_(False)
    model.encoder.layer[-1].requires_grad_(True)
    optimizer = torch.optim.AdamW(model.encoder.layer[-1].parameters(), lr=2e-5)
    examples = list(training_examples())
    random.Random(17).shuffle(examples)
    model.train()
    for start in range(0, len(examples), 8):
        batch = examples[start:start+8]
        texts = [text for triple in batch for text in triple]
        encoded = tokenizer(texts, padding=True, truncation=True, max_length=128, return_tensors="pt")
        mask = encoded.attention_mask.unsqueeze(-1)
        pooled = (model(**encoded).last_hidden_state * mask).sum(1) / mask.sum(1)
        query, direct, unrelated = F.normalize(pooled).reshape(len(batch), 3, -1).unbind(1)
        loss = F.relu(0.2 + (query * unrelated).sum(1) - (query * direct).sum(1)).mean()
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
    model.eval()
