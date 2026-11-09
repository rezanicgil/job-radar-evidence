"""Find local CV evidence for an applicant-selected requirement."""

import argparse
from functools import lru_cache
from pathlib import Path
import re
import sys
from threading import Lock

import torch
from transformers import AutoModel, AutoTokenizer
from train_smoke import BASE, REVISION

_MODEL_LOAD_LOCK = Lock()


@lru_cache(maxsize=1)
def load_encoder():
    tokenizer = AutoTokenizer.from_pretrained(BASE, revision=REVISION)
    model = AutoModel.from_pretrained(BASE, revision=REVISION).eval()
    return tokenizer, model


SECTION_TITLE = re.compile(
    r"(?:(?:professional |work |relevant )?experience|(?:technical )?skills|"
    r"(?:professional )?summary|education(?: & additional)?|projects|certifications|"
    r"languages|iş deneyimi|deneyim|eğitim|projeler|teknik beceriler|yetenekler|özet|diller)\s*:?",
    re.IGNORECASE,
)


def cv_page_chunks(page, is_pdf):
    current = ""
    for raw in page.splitlines():
        line = raw.strip()
        if not line or SECTION_TITLE.fullmatch(line):
            if current:
                yield current
            current = ""
            continue
        content = re.sub(r"^(?:[•▪●]\s*|[-–]\s+)", "", line)
        if not content:
            continue
        if is_pdf and current and content == line and content[0].islower() and current[-1] not in ".!?:":
            current += " " + content
        else:
            if current:
                yield current
            current = content
    if current:
        yield current


def read_passages(path, *, posting=False):
    if path.suffix.lower() == ".pdf":
        from pypdf import PdfReader
        pages = [page.extract_text() or "" for page in PdfReader(path).pages]
    elif path.suffix.lower() == ".txt":
        pages = [path.read_text(encoding="utf-8-sig")]
    else:
        raise ValueError("Choose a text PDF or a UTF-8 TXT file.")
    passages = [(number, sentence.strip()) for number, page in enumerate(pages, 1)
                for chunk in (page.splitlines() if posting else cv_page_chunks(page, path.suffix.lower() == ".pdf"))
                for sentence in re.split(r"(?<=[.!?])\s+", chunk) if sentence.strip()]
    if not passages:
        raise ValueError("No readable text found. Export a text PDF or paste the CV into a TXT file.")
    return passages


def rank_passages(passages, requirements):
    with _MODEL_LOAD_LOCK:
        tokenizer, model = load_encoder()
    texts = requirements + [line for _, line in passages]
    vectors = []
    with torch.inference_mode():
        for start in range(0,len(texts),16):
            batch = tokenizer(texts[start:start+16], padding=True, truncation=True,
                              max_length=128, return_tensors="pt")
            mask = batch.attention_mask.unsqueeze(-1)
            vectors.extend((model(**batch).last_hidden_state * mask).sum(1) / mask.sum(1))
        normalized = torch.nn.functional.normalize(torch.stack(vectors))
        scores = normalized[:len(requirements)] @ normalized[len(requirements):].T
    return [[passages[i] for i in row.argsort(descending=True).tolist()[:3]] for row in scores]


def review_posting(passages, path):
    statements = list(dict.fromkeys(line for _, line in read_passages(path, posting=True)))
    ranked = rank_passages(passages, statements)
    confirmed = required = 0
    for statement, candidates in zip(statements, ranked, strict=True):
        print("\nPosting:", statement)
        for page, text in candidates:
            print(f"[Page {page}] {text}")
        print("For a required technical condition, choose supported, partial or unverified.")
        print("Choose skip for preferences, context or other text.")
        while True:
            choice = input("Review [s/p/u/skip]: ").strip().lower()
            if choice in {"s","p","u","skip"}:
                break
            print("Enter s, p, u or skip.")
        if choice != "skip":
            required += 1
            confirmed += choice == "s"
    if required:
        print(f"Reviewer-confirmed coverage: {confirmed}/{required} ({confirmed/required:.0%}).")
    else:
        print("No required technical conditions selected.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cv", type=Path)
    parser.add_argument("requirement", nargs="?")
    parser.add_argument("--posting", type=Path, help="Review a full posting in TXT or text PDF format.")
    args = parser.parse_args()
    if bool(args.requirement and args.requirement.strip()) == bool(args.posting):
        parser.error("Supply either one requirement or --posting PATH.")
    torch.set_num_threads(4)
    try:
        passages = read_passages(args.cv)
        if args.posting:
            sys.stdout.reconfigure(encoding="utf-8")
            review_posting(passages, args.posting)
            return
    except (ValueError, OSError) as error:
        parser.exit(2, f"{error}\n")
    sys.stdout.reconfigure(encoding="utf-8")
    print("Requirement:", args.requirement)
    print("Candidate passages · review for evidence")
    for page, text in rank_passages(passages, [args.requirement])[0]:
        print(f"[Page {page}] {text}")


if __name__ == "__main__":
    main()
