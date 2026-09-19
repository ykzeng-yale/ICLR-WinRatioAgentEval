#!/usr/bin/env python3
"""Build the named preprint from the frozen scientific paper; never publishes.

Only arxiv/ and work/arxiv_build/ are written. Numerical observations, the
original paper/ sources and the historical ICLR submission remain untouched.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "arxiv"
WORK = ROOT / "work" / "arxiv_build"
SOURCE = OUT / "source"
TITLE = "Guarded Win Statistics for Continuous Agent Evaluation"
AUTHOR = "Yukang Zeng"
EMAIL = "yukang.zeng@yale.edu"
BASELINE = "45e8ee2715f148c81db7f6510d66677f57e03f0a"
TEXBIN = Path.home() / "Library/TinyTeX/bin/universal-darwin"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def run(args, cwd, log):
    env = dict(os.environ)
    env["PATH"] = str(TEXBIN) + os.pathsep + env.get("PATH", "")
    with log.open("a") as output:
        subprocess.run(args, cwd=cwd, env=env, stdout=output,
                       stderr=subprocess.STDOUT, check=True)


def prepare_sources():
    SOURCE.mkdir(parents=True, exist_ok=True)
    (SOURCE / "figures").mkdir(exist_ok=True)
    original = (ROOT / "paper/main.tex").read_text()
    main = original.replace(
        r"\documentclass{article}" + "\n" + r"\usepackage{iclr2027_conference,times}",
        r"""\documentclass[11pt,letterpaper]{article}
\usepackage[margin=1in]{geometry}
\usepackage{times,natbib}
\setcitestyle{authoryear,round,citesep={;},aysep={,},yysep={;}}
\setlength{\emergencystretch}{2em}
\renewcommand{\topfraction}{0.95}
\renewcommand{\textfraction}{0.05}""", 1)
    main = main.replace(r"\usepackage{hyperref,url}", r"\usepackage[hidelinks]{hyperref}" + "\n" + r"\usepackage{url}", 1)
    main = main.replace(r"\author{Anonymous authors}",
        r"\author{Yukang Zeng\\\texttt{yukang.zeng@yale.edu}}" + "\n"
        + r"\date{Preprint---September 2026}" + "\n"
        + r"\hypersetup{pdftitle={" + TITLE + r"},pdfauthor={Yukang Zeng},pdfsubject={Research preprint}}", 1)
    main = main.replace(r"\bibliographystyle{iclr2027_conference}", r"\bibliographystyle{plainnat}", 1)
    main = main.replace(r"\appendix", r"\clearpage" + "\n" + r"\appendix" + "\n" + r"\label{arxiv:appendix_start}", 1)
    old = "Historical comparisons also expose success losses\nhidden by aggregate wins. These\nresults support explicit decisions for a specified workload and\npreference rule, with unresolved outcomes retained in the analysis."
    new = "Two local open-weight studies add 1,182 coding episodes and 196 planned\nairline records, with descriptive same-task contrasts and explicitly\nqualified replay inference."
    if original.count(old) != 1:
        raise ValueError("Frozen abstract anchor changed; review before rebuilding")
    main = main.replace(old, new, 1)
    # The canonical PDF contains the complete supplement; the split copies are
    # conveniences, not a second separately submitted paper.
    main = main.replace(
        "The supplementary code contains the comparator, monitoring procedures,",
        "The accompanying reproducibility code contains the comparator, monitoring procedures,", 1)
    main = main.replace(
        "Internal protocol amendments are distinguished from public preregistration.",
        "Internal protocol amendments are distinguished from public preregistration.\n"
        r"The full preprint includes all supplementary proofs and results after the references. "
        r"Code and versioned evidence are available at "
        r"\url{https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval}; "
        "the accompanying archive records the exact released files.", 1)
    changes = []
    for p in sorted((ROOT / "paper").glob("*.tex")):
        text = main if p.name == "main.tex" else p.read_text()
        if p.name == "asynchronous.tex":
            text = text.replace(r"\label{cor:async_envelope}" + "\nDefine",
                                r"\label{cor:async_envelope}" + "\n" + r"\leavevmode\par" + "\nDefine", 1)
        for fig in re.findall(r"\\includegraphics(?:\[[^]]*\])?\{([^}]+)\}", text):
            src = (p.parent / fig).resolve()
            if not src.is_file():
                raise FileNotFoundError(src)
            dst = SOURCE / "figures" / src.name
            if dst.exists() and dst.read_bytes() != src.read_bytes():
                raise ValueError("Figure basename collision: " + src.name)
            shutil.copy2(src, dst)
            text = text.replace("{" + fig + "}", "{figures/" + src.name + "}")
        (SOURCE / p.name).write_text(text)
        changes.append({"path": p.name, "original_sha256": digest(p.read_bytes()),
                        "preprint_sha256": digest(text.encode())})
    shutil.copy2(ROOT / "paper/references.bib", SOURCE / "references.bib")
    abstract = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", main, re.S).group(1)
    abstract = " ".join(abstract.replace(r"\%", "%").split())
    (OUT / "abstract.txt").write_text(abstract + "\n")
    return changes, abstract


def build_pdf():
    WORK.mkdir(parents=True, exist_ok=True)
    compile_dir = WORK / "compile"
    if compile_dir.exists():
        shutil.rmtree(compile_dir)
    shutil.copytree(SOURCE, compile_dir)
    log = WORK / "latexmk.log"
    log.write_text("")
    run(["latexmk", "-pdf", "-interaction=nonstopmode", "-halt-on-error", "main.tex"], compile_dir, log)
    texlog = (compile_dir / "main.log").read_text(errors="replace")
    if "There were undefined references" in texlog or "undefined citations" in texlog:
        raise ValueError("Unresolved reference/citation; inspect build log")
    shutil.copy2(compile_dir / "main.pdf", OUT / "paper.pdf")
    shutil.copy2(compile_dir / "main.bbl", SOURCE / "main.bbl")
    aux = (compile_dir / "main.aux").read_text()
    match = re.search(r"\\newlabel\{arxiv:appendix_start\}\{\{[^}]*\}\{(\d+)\}", aux)
    if not match:
        raise ValueError("Missing appendix page marker")
    import fitz
    reader = fitz.open(OUT / "paper.pdf")
    first = int(match.group(1))
    for filename, start, end, subtitle in [
        ("main_paper.pdf", 0, first - 1, "Main paper and references"),
        ("supplement.pdf", first - 1, len(reader), "Supplementary proofs and results")]:
        writer = fitz.open()
        # Static reading extracts avoid dangling destinations into the omitted
        # part. The canonical full PDF preserves all live cross-references.
        writer.insert_pdf(reader, from_page=start, to_page=end - 1, links=False)
        writer.set_metadata({"title": TITLE + " — " + subtitle, "author": AUTHOR,
                             "subject": "Reading extract from the complete preprint"})
        writer.save(OUT / filename, garbage=4, deflate=True)
        writer.close()
    pages = len(reader)
    reader.close()
    return pages, first


def build_archives(changes, pages, first):
    # Start from the already audited privacy-filtered evidence supplement.
    # Preserve all scientific/code/data payload bytes, replacing only the paper
    # directory and explicit package-level documentation/provenance.
    with zipfile.ZipFile(ROOT / "submission/anonymous_code.zip") as z:
        payload = {n: z.read(n) for n in z.namelist()
                   if not n.startswith("paper/") and n not in ("README.md", "package_manifest.json")}
    for p in SOURCE.rglob("*"):
        if p.is_file():
            payload["paper/" + str(p.relative_to(SOURCE))] = p.read_bytes()
    payload["paper/manuscript.pdf"] = (OUT / "paper.pdf").read_bytes()
    provenance = {"baseline_scientific_commit": BASELINE,
        "historical_code_archive_sha256": digest((ROOT / "submission/anonymous_code.zip").read_bytes()),
        "source_transformations": changes,
        "scope": "Formatting, authorized author identity, bounded abstract update and public code link only; original numerical records preserved.",
        "commercial_model_execution": "prohibited"}
    payload["arxiv_source_provenance.json"] = (json.dumps(provenance, indent=2) + "\n").encode()
    readme = """# Guarded Win Statistics: reproducibility supplement

Author: Yukang Zeng. Start with REPRODUCIBILITY.md and `python reproduce.py`.
`python reproduce.py --coding --airline` reconstructs the open-weight summaries
from archived metric projections without running any model or candidate code.
`python reproduce.py --build-pdf` rebuilds the named preprint in paper/.

The full paper is paper/manuscript.pdf; it includes all proof and result
appendices. The historical anonymous-provenance map remains because it records
privacy-preserving transformations of immutable contributed observations.
Legacy ICLR/review references in historical protocols describe their collection
history, not a conference submission or acceptance for this preprint.

No new commercial/proprietary experimental agents, simulators, judges or
fallbacks are authorized. Historical commercial collection scripts are evidence
of past collection only and must not be rerun. Default reproduction verifies
saved results; optional simulation commands are explicitly documented.

This release does not claim human scientific signoff, arXiv submission,
endorsement, moderation acceptance or production validation. Future-study
issues are separate from the evidence included in this first preprint.
"""
    payload["README.md"] = readme.encode()
    bad = re.compile(rb"/Users/|sk-(?:proj-|ant-api\d\d-)?[A-Za-z0-9_-]{20,}", re.I)
    for name, data in payload.items():
        if Path(name).suffix not in (".pdf", ".png") and bad.search(data):
            raise ValueError("Private path or credential-like content: " + name)
    manifest = {"status": "Preprint preparation; author review and publication decisions pending",
                "files": [{"path": n, "bytes": len(d), "sha256": digest(d)} for n, d in sorted(payload.items())]}
    payload["package_manifest.json"] = (json.dumps(manifest, indent=2) + "\n").encode()
    with zipfile.ZipFile(OUT / "reproducibility_code.zip", "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name, data in sorted(payload.items()):
            z.writestr(name, data)
    # A single root main.tex, supported figure PDFs, BibTeX sources and matching
    # main.bbl; no generated paper PDF or second document in the arXiv upload.
    with tarfile.open(OUT / "arxiv_source.tar.gz", "w:gz") as tar:
        for p in sorted(SOURCE.rglob("*")):
            if p.is_file():
                tar.add(p, arcname=str(p.relative_to(SOURCE)), recursive=False)
    result = {"baseline_scientific_commit": BASELINE, "title": TITLE, "authors": [AUTHOR],
              "pages": pages, "main_pages": first - 1, "supplement_pages": pages - first + 1,
              "appendix_first_page": first, "source_files": len(list(SOURCE.rglob("*.*"))),
              "code_payload_files": len(manifest["files"]), "source_transformations": changes,
              "artifacts": [{"path": n, "bytes": (OUT / n).stat().st_size,
                             "sha256": digest((OUT / n).read_bytes())}
                            for n in ["paper.pdf", "main_paper.pdf", "supplement.pdf", "arxiv_source.tar.gz", "reproducibility_code.zip"]]}
    (OUT / "package_manifest.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sources-only", action="store_true")
    args = ap.parse_args()
    changes, abstract = prepare_sources()
    if args.sources_only:
        print("Prepared source files; abstract characters:", len(abstract))
        return
    pages, first = build_pdf()
    result = build_archives(changes, pages, first)
    print(json.dumps({k: result[k] for k in ["pages", "main_pages", "supplement_pages", "source_files", "code_payload_files"]}))


if __name__ == "__main__":
    main()
