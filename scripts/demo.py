"""English CV evidence review demo. Run with python scripts/demo.py."""

import os
import logging
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from flask import Flask, render_template, request
from pypdf.errors import PdfReadError
from waitress import serve
import torch

from review_cv import read_passages, rank_passages
from market_inventory import PATTERNS

# Malformed PDFs can include applicant bytes in parser diagnostics.
pdf_logger = logging.getLogger("pypdf")
pdf_logger.addHandler(logging.NullHandler())
pdf_logger.propagate = False

app = Flask(__name__, template_folder="../templates")
app.config["MAX_CONTENT_LENGTH"] = 3 * 1024 * 1024
EXAMPLE_CV = "I deployed the billing API to production with Docker.\nI wrote SQL reports for the support team."
EXAMPLE_JOB = "Production experience with Docker is required.\nExperience with Kubernetes is preferred."


@app.after_request
def private_response(response):
    response.headers["Cache-Control"] = "no-store"
    return response


@app.route("/", methods=["GET", "POST"])
def review():
    cv = request.form.get("cv", EXAMPLE_CV)
    posting = request.form.get("posting", EXAMPLE_JOB)
    matches = []
    error = None
    if request.method == "POST":
        try:
            with TemporaryDirectory() as directory:
                upload = request.files.get("file")
                if upload and upload.filename:
                    suffix = Path(upload.filename).suffix.lower()
                    if suffix not in {".pdf",".txt"}:
                        raise ValueError("Choose a text PDF or TXT file.")
                    path = Path(directory) / ("cv" + suffix)
                    upload.save(path)
                else:
                    path = Path(directory) / "cv.txt"
                    path.write_text(cv, encoding="utf-8")
                passages = read_passages(path)
            statements = list(dict.fromkeys(s.strip() for s in posting.splitlines() if s.strip()))
            if not statements or len(statements) > 50 or len(passages) > 800:
                raise ValueError("Use 1–50 posting lines and up to 800 CV passages.")
            matches = list(zip(statements,rank_passages(passages,statements),strict=True))
        except (ValueError, PdfReadError, OSError):
            error = "Check the file is readable and enter 1–50 posting lines. Scanned PDFs need a text export."
    return render_template("review.html",cv=cv,posting=posting,matches=matches,error=error), 422 if error else 200


@app.get("/market")
def market():
    folder = Path(__file__).resolve().parents[1] / "reports"
    path = max(folder.glob("skill-mentions-*.json"), default=None)
    if path is None:
        return "No market snapshot available.", 503
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    area = request.args.get("area", "")
    if area and area not in PATTERNS:
        return "Unknown role family.", 400
    selected = [p for p in snapshot["postings"] if not area or area in p["areas"]]
    readable = [p for p in selected if p["status"] == "readable"]
    groups = {}
    for posting in readable:
        for skill in set(posting["skills"]):
            groups.setdefault(skill, []).append(posting)
    skills = sorted(groups.items(), key=lambda pair: (-len(pair[1]),pair[0]))
    return render_template("market.html",date=snapshot["collected_at"][:10],areas=PATTERNS,area=area,
                           total=len(selected),readable=len(readable),skills=skills)


if __name__ == "__main__":
    torch.set_num_threads(4)
    serve(app, host=os.getenv("HOST","127.0.0.1"),port=int(os.getenv("PORT","7860")),threads=2)
