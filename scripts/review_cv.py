"""Find local CV evidence for an applicant-selected requirement."""

import argparse
from functools import lru_cache
from pathlib import Path
import re
import sys
from threading import Lock

import torch
from market_skills import PATTERNS as MARKET_PATTERNS
from transformers import AutoModel, AutoTokenizer
from train_smoke import BASE, REVISION

# CV evidence vocabulary is broader than the versioned market denominator.
REVIEW_PATTERNS = {**MARKET_PATTERNS, **{
    name: re.compile(r"(?<![\w+#])"+re.escape(name)+r"(?![\w+#])", re.I)
    for name in ("Node.js", ".NET", "CI/CD", "RabbitMQ", "ORM", "Prisma", "TypeORM",
                 "Mongoose", "Sequelize", "GORM", "gRPC")
}}
_MODEL_LOAD_LOCK = Lock()
ENCODERS = {
    "base": (BASE, REVISION),
    "fine-tuned": ("rezanicgil/python-tr-en-retriever","5621cc7f11eac83bb1be35b849797e5dba153218"),
}


@lru_cache(maxsize=1)
def load_encoder(encoder="base"):
    repo,revision=ENCODERS[encoder]
    tokenizer = AutoTokenizer.from_pretrained(repo, revision=revision)
    model = AutoModel.from_pretrained(repo, revision=revision).eval()
    return tokenizer, model


SECTION_TITLE = re.compile(
    r"(?:(?:professional |work |relevant )?experience|(?:technical )?skills|"
    r"(?:professional )?summary|education(?: & additional)?|projects|certifications|"
    r"languages|iş deneyimi|deneyim|eğitim|projeler|teknik beceriler|yetenekler|özet|diller)\s*:?",
    re.IGNORECASE,
)


# Keep only known multiword names across uppercase PDF line breaks; a new
# bullet, heading or TXT line must still start a new passage.
WRAPPED_NAMES = (("GitHub", "Actions"), ("Jetpack", "Compose"), ("React", "Native"),
                 ("Android", "SDK"), ("Unreal", "Engine"), ("Amazon", "SQS"))

def wraps_name(previous, following):
    return any(re.search(r"(?<!\w)"+left+r"$", previous, re.I) and
               re.match(right+r"(?!\w)", following, re.I) for left,right in WRAPPED_NAMES)


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
        if is_pdf and current and content == line and (content[0].islower() or wraps_name(current,content)) and current[-1] not in ".!?:":
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


def passage_windows(text,tokenizer):
    def fits(piece):
        return len(tokenizer.encode(piece,verbose=False))<=128
    if len(text)<=768 and fits(text):
        return [text]
    windows=[]
    start=0
    while start<len(text):
        lo,hi=start+1,min(start+768,len(text))
        while lo<hi:
            mid=(lo+hi+1)//2
            if fits(text[start:mid]):
                lo=mid
            else:
                hi=mid-1
        end=lo
        if end<len(text):
            end=next((j for j in range(end,start+(end-start)//2,-1) if text[j].isspace()),end)
        piece=text[start:end].strip()
        if piece:
            windows.append(piece)
        if end==len(text):
            break
        start=end-(end-start)//4
    if len(windows)>1:
        for part in re.split(r"[,;:]",text):
            clause=part.strip()
            if len(clause.split())>=4 and len(clause)<=768 and fits(clause):
                windows.append(clause)
    return list(dict.fromkeys(windows))


def rank_passages(passages, requirements, encoder="base"):
    # Rank each distinct passage once and cite the page where it first appears.
    first_by_text = {}
    for page, text in passages:
        first_by_text.setdefault(" ".join(text.split()), (page, text))
    passages = list(first_by_text.values())
    with _MODEL_LOAD_LOCK:
        tokenizer, model = load_encoder(encoder)
    texts = requirements + [line for _, line in passages]
    groups=[passage_windows(text,tokenizer) for text in texts] if encoder=="fine-tuned" else [[text] for text in texts]
    flattened=[w for group in groups for w in group]
    texts=list(dict.fromkeys(flattened))
    lookup={text:i for i,text in enumerate(texts)}
    vectors = []
    with torch.inference_mode():
        for start in range(0,len(texts),16):
            batch = tokenizer(texts[start:start+16], padding=True, truncation=True,
                              max_length=128, return_tensors="pt")
            mask = batch.attention_mask.unsqueeze(-1)
            vectors.extend((model(**batch).last_hidden_state * mask).sum(1) / mask.sum(1))
        normalized = torch.nn.functional.normalize(torch.stack(vectors))
        normalized=normalized[[lookup[text] for text in flattened]]
        sizes=[len(g) for g in groups]
        if max(sizes)==1:
            scores=normalized[:len(requirements)] @ normalized[len(requirements):].T
        else:
            chunks=normalized.split(sizes)
            scores=torch.stack([torch.stack([(query @ candidate.T).max(dim=1).values.mean()
                                for candidate in chunks[len(requirements):]]) for query in chunks[:len(requirements)]])
    results = []
    for requirement, row in zip(requirements, scores, strict=True):
        ranked = [passages[i] for i in row.argsort(descending=True).tolist()]
        selected = ranked[:3]
        # Reserve one suggestion for a full CV sentence naming the requested technology.
        # This surfaces negative statements too; reviewers still decide support.
        terms = [pattern for pattern in REVIEW_PATTERNS.values() if pattern.search(requirement)]
        if terms and selected:
            sentence = next((item for item in ranked if len(item[1].split()) >= 6
                             and item[1].endswith((".", "!", "?"))
                             and any(pattern.search(item[1]) for pattern in terms)), None)
            if sentence is None and not any(pattern.search(text) for _, text in selected for pattern in terms):
                # Skill-list evidence is still reviewable, even without a final period.
                sentence = next((item for item in ranked if any(pattern.search(item[1]) for pattern in terms)), None)
            if sentence is not None and sentence not in selected:
                selected[-1] = sentence
        results.append(selected)
    return results


def review_posting(passages, path, encoder="base"):
    statements = list(dict.fromkeys(line for _, line in read_passages(path, posting=True)))
    ranked = rank_passages(passages, statements,encoder)
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
    parser.add_argument("--encoder", choices=ENCODERS, default="base",
                        help="Choose the base encoder or the research retriever adapted on Python translations.")
    args = parser.parse_args()
    if bool(args.requirement and args.requirement.strip()) == bool(args.posting):
        parser.error("Supply either one requirement or --posting PATH.")
    torch.set_num_threads(4)
    try:
        passages = read_passages(args.cv)
        sys.stdout.reconfigure(encoding="utf-8")
        repo,revision=ENCODERS[args.encoder]
        print(f"Passage encoder: {repo} at {revision}")
        if args.posting:
            review_posting(passages, args.posting,args.encoder)
        else:
            print("Requirement:", args.requirement)
            print("Candidate passages · review for evidence")
            for page, text in rank_passages(passages, [args.requirement],args.encoder)[0]:
                print(f"[Page {page}] {text}")
    except (ValueError, OSError) as error:
        parser.exit(2, f"{error}\n")


if __name__ == "__main__":
    main()
