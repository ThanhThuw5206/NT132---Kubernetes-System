#!/usr/bin/env python3
"""Repeat laptop checks without contacting Google Cloud or changing cluster state."""
import argparse
import datetime as dt
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]


def run_check(name, argv, report_dir, env=None, timeout=120):
    try:
        result = subprocess.run(argv, cwd=ROOT, env=env, capture_output=True, text=True,
                                encoding="utf-8", errors="replace", timeout=timeout)
        code, output = result.returncode, result.stdout + result.stderr
    except (OSError, subprocess.TimeoutExpired) as exc:
        code, output = 1, str(exc)
    (report_dir / (name + ".txt")).write_text(output, encoding="utf-8")
    print(name + ": " + ("PASS" if code == 0 else "FAIL"), flush=True)
    return {"name": name, "passed": code == 0, "exit_code": code, "log": name + ".txt"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=pathlib.Path, help="New directory; defaults to .generated/laptop-check-*")
    args = parser.parse_args()
    if args.output:
        report_dir = args.output.resolve()
        report_dir.mkdir(parents=True, exist_ok=False)
    else:
        generated = ROOT / ".generated"
        generated.mkdir(exist_ok=True)
        report_dir = pathlib.Path(tempfile.mkdtemp(prefix="laptop-check-", dir=generated))
    report = {"time": dt.datetime.now(dt.timezone(dt.timedelta(hours=7))).isoformat(timespec="seconds"),
              "scope": "Laptop validation only; mocks and loopback HTTP are not cloud acceptance",
              "python": sys.version.split()[0], "checks": []}
    report["checks"].append(run_check("unit-tests", [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], report_dir))
    report["checks"].append(run_check("bookinfo-source", [sys.executable, "scripts/prepare-bookinfo.py",
                                                        "--output", str(report_dir / "bookinfo-baseline")], report_dir))
    report["checks"].append(run_check("bookinfo-render", [sys.executable, "scripts/tv3.py", "render",
                                                        "apps/bookinfo/application.bookinfo.json",
                                                        "--output", str(report_dir / "bookinfo-integration")], report_dir))
    bash = shutil.which("bash")
    if not bash and os.name == "nt":
        candidate = pathlib.Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Git/bin/bash.exe"
        if candidate.is_file():
            bash = str(candidate)
    report["checks"].append(run_check("bash-syntax", [bash or "bash", "-c", 'for file in scripts/*.sh; do bash -n "$file" || exit; done'], report_dir))
    if os.name == "nt":
        check_env = dict(os.environ, TV3_CHECK_ROOT=str(ROOT))
        ps = """$ErrorActionPreference='Stop'; Get-ChildItem -LiteralPath (Join-Path $env:TV3_CHECK_ROOT 'scripts') -Filter '*.ps1' | ForEach-Object {
$tv3Tokens=$null; $tv3Errors=$null
[void][System.Management.Automation.Language.Parser]::ParseFile($_.FullName,[ref]$tv3Tokens,[ref]$tv3Errors)
if($tv3Errors.Count -gt 0){ throw ($tv3Errors | Out-String) }
}; Write-Output 'All PowerShell scripts parsed.'"""
        report["checks"].append(run_check("powershell-syntax", ["powershell", "-NoProfile", "-Command", ps], report_dir, check_env))
        report["checks"].append(run_check("gcloud-version", ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                                                                      "-File", "scripts/gcloud-local.ps1", "--version"], report_dir, timeout=60))
    report["all_passed"] = all(c["passed"] for c in report["checks"])
    (report_dir / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(report_dir)
    return 0 if report["all_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
