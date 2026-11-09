"""Export exact replacement tensors for the fine-tuned research classifier."""

from safetensors.torch import save_file
import torch
from transformers import AutoModelForSequenceClassification

from train_pair_encoder import BASE, REVISION, ROOT


def main():
    base = AutoModelForSequenceClassification.from_pretrained(BASE, revision=REVISION)
    adapted = AutoModelForSequenceClassification.from_pretrained(ROOT / "runs/pair-mentions-v3")
    original = base.state_dict()
    changed = {name: tensor for name, tensor in adapted.state_dict().items()
               if not torch.equal(original[name], tensor)}
    if not changed or not all(name.startswith(("roberta.encoder.layer.5.", "classifier.")) for name in changed):
        raise ValueError("Unexpected trained layers")
    original.update(changed)
    base.load_state_dict(original, strict=True)
    folder = ROOT / "runs/research-release"
    folder.mkdir(exist_ok=True)
    save_file(changed, folder / "trained_layers.safetensors")
    print(f"Exported {len(changed)} tensors")


if __name__ == "__main__":
    main()
