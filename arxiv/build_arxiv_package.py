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
    main = main.replace(r"\end{document}", r"\input{t1_validation.tex}" + "\n" + r"\end{document}", 1)
    changes = []
    addition = OUT / "additions/t1_validation.tex"
    (SOURCE / addition.name).write_bytes(addition.read_bytes())
    changes.append({"path": addition.name, "addition": "Accepted bounded T1 replay calibration, reviewed at 97ad956", "preprint_sha256": digest(addition.read_bytes())})
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


def build_archives(changes, pages, first, code_only=False):
    # Start from the already audited privacy-filtered evidence supplement.
    # Preserve numerical payload bytes. The one recorded code transformation
    # removes a dependency on an excluded module from the accepted CPU runner.
    with zipfile.ZipFile(ROOT / "submission/anonymous_code.zip") as z:
        payload = {n: z.read(n) for n in z.namelist()
                   if not n.startswith("paper/") and n not in ("README.md", "package_manifest.json")}
    runner = "experiments/ustat_reference/run_ustat_reference.py"
    original_runner = payload[runner]
    old_imports = "from run_simulations import exact_targets\nfrom run_online_methods import SCENARIOS, THRESHOLDS"
    standalone_config = """from run_simulations import exact_targets, SCENARIOS as BASE_SCENARIOS
# Release-only dependency repair: these immutable values and insertion order
# match the accepted run_online_methods configuration, without importing wincs.
SCENARIOS = dict(BASE_SCENARIOS)
SCENARIOS.update({
    'tie_heavy_null': (.995, .995, .30, .30, 1.),
    'tie_heavy_efficiency': (.995, .995, .30, .30, .55),
})
THRESHOLDS = [0., -.03, -.01]"""
    runner_text = original_runner.decode()
    if runner_text.count(old_imports) != 1:
        raise ValueError("Frozen extension runner import block changed")
    payload[runner] = runner_text.replace(old_imports, standalone_config).encode()
    code_changes = [{"path": runner, "original_sha256": digest(original_runner),
                     "release_sha256": digest(payload[runner]),
                     "reason": "Inline unchanged scenario/threshold constants to remove the excluded wincs import dependency; numerical algorithm and saved results unchanged."}]
    for p in SOURCE.rglob("*"):
        if p.is_file():
            payload["paper/" + str(p.relative_to(SOURCE))] = p.read_bytes()
    payload["paper/manuscript.pdf"] = (OUT / "paper.pdf").read_bytes()
    t1 = ROOT / "results/live_ab_validation_v2/t1_run_20260921"
    accepted = json.loads((t1 / "T1_ANALYSIS.json").read_text())
    t1_manifest = {"accepted_snapshot": "35ab9d111123382db8997d4a0ccf4d5e36dbc876", "review_commit": "97ad9562e68305d6b668630fb512d9d2eafc6bef", "scope": "Unchanged primary records and saved-record table reproduction only; full original provenance and reference records at exact Git snapshot. No latent/native rerun.", "primary_files": [], "expected": {}}
    for f in sorted(t1.glob("shard_*/primary_rows.csv.gz")):
        name = f"data/{f.parent.name}.csv.gz"
        data = f.read_bytes()
        frozen = subprocess.check_output(["git", "show", t1_manifest["accepted_snapshot"] + ":" + str(f.relative_to(ROOT))], cwd=ROOT)
        if data != frozen:
            raise ValueError("T1 raw record differs from accepted snapshot: " + str(f))
        payload["t1_validation/" + name] = data
        t1_manifest["primary_files"].append({"path": name, "sha256": digest(data)})
    for r in accepted["rows"]:
        t1_manifest["expected"].setdefault(r["cell"], {})[r["construction"]] = {"trials": r["trials"], "errors": r["trial_any_error"]["k"], "hierarchy_miscoverage": r["miscover_h_twosided"]["k"], **r["decisions"]}
    payload["t1_validation/manifest.json"] = (json.dumps(t1_manifest, indent=2) + "\n").encode()
    payload["t1_validation/reproduce_t1.py"] = (OUT / "additions/reproduce_t1.py").read_bytes()
    provenance = {"baseline_scientific_commit": BASELINE,
        "historical_code_archive_sha256": digest((ROOT / "submission/anonymous_code.zip").read_bytes()),
        "source_transformations": changes,
        "code_transformations": code_changes,
        "scope": "Preprint formatting/metadata, recorded CPU dependency repair, and accepted T1 replay appendix with unchanged primary records and saved-record table reproduction; historical baseline preserved.",
        "commercial_model_execution": "prohibited"}
    payload["arxiv_source_provenance.json"] = (json.dumps(provenance, indent=2) + "\n").encode()
    readme = """# Guarded Win Statistics: reproducibility supplement

Author: Yukang Zeng. Start with REPRODUCIBILITY.md and `python reproduce.py`.
Run `python t1_validation/reproduce_t1.py` to reproduce the added T1 table from
unchanged primary records. Complete original provenance/reference records are at
https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/tree/35ab9d111123382db8997d4a0ccf4d5e36dbc876/results/live_ab_validation_v2/t1_run_20260921 .
This separate check does not rerun latent paths or native reference computations.
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
The accepted U-statistic runner uses the same scenario values/order and gate
thresholds without importing the excluded generic wincs module. The release-only
dependency repair is recorded in arxiv_source_provenance.json.

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
    if not code_only:
        with tarfile.open(OUT / "arxiv_source.tar.gz", "w:gz") as tar:
            for p in sorted(SOURCE.rglob("*")):
                if p.is_file():
                    tar.add(p, arcname=str(p.relative_to(SOURCE)), recursive=False)
    result = {"baseline_scientific_commit": BASELINE, "title": TITLE, "authors": [AUTHOR],
              "pages": pages, "main_pages": first - 1, "supplement_pages": pages - first + 1,
              "appendix_first_page": first, "source_files": len(list(SOURCE.rglob("*.*"))),
              "code_payload_files": len(manifest["files"]), "source_transformations": changes,
              "code_transformations": code_changes,
              "artifacts": [{"path": n, "bytes": (OUT / n).stat().st_size,
                             "sha256": digest((OUT / n).read_bytes())}
                            for n in ["paper.pdf", "main_paper.pdf", "supplement.pdf", "arxiv_source.tar.gz", "reproducibility_code.zip"]]}
    (OUT / "package_manifest.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sources-only", action="store_true")
    ap.add_argument("--code-only", action="store_true", help="Repair/repackage code while preserving all PDFs and the source-upload archive")
    args = ap.parse_args()
    if args.code_only:
        if args.sources_only:
            ap.error("--code-only and --sources-only are mutually exclusive")
        previous = json.loads((OUT / "package_manifest.json").read_text())
        result = build_archives(previous["source_transformations"], previous["pages"], previous["appendix_first_page"], code_only=True)
        print(json.dumps({"code_payload_files": result["code_payload_files"], "code_transformations": result["code_transformations"]}))
        return
    changes, abstract = prepare_sources()
    if args.sources_only:
        print("Prepared source files; abstract characters:", len(abstract))
        return
    pages, first = build_pdf()
    result = build_archives(changes, pages, first)
    print(json.dumps({k: result[k] for k in ["pages", "main_pages", "supplement_pages", "source_files", "code_payload_files"]}))


if __name__ == "__main__":
    main()
