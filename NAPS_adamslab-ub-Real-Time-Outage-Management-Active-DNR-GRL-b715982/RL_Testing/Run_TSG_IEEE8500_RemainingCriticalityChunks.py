"""Run remaining IEEE 8500 full criticality chunks and merge completed outputs.

The full IEEE 8500 criticality plan is chunked one target at a time. This
utility reads the generated batch manifest, skips chunks whose case-summary
CSV already exists, runs only the missing chunks, and optionally executes the
manifest merge commands when a study is complete.
"""

import argparse
import csv
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_MANIFEST = (
    BASE_DIR
    / "paper_results"
    / "tsg_ieee8500"
    / "full_criticality_batches"
    / "ieee8500_full_criticality_batch_manifest.json"
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Resume missing IEEE 8500 action-mask/branchflow criticality chunks."
    )
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument(
        "--study",
        choices=["action_mask", "branchflow", "all"],
        default="all",
    )
    parser.add_argument("--max-chunks", type=int, default=0)
    parser.add_argument("--no-merge", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--log-dir",
        default=(
            "paper_results/tsg_ieee8500/full_criticality_batches/resume_logs"
        ),
    )
    return parser.parse_args()


def resolve_path(path_text):
    path = Path(path_text)
    if path.is_absolute():
        return path
    return BASE_DIR / path


def load_manifest(path_text):
    path = resolve_path(path_text)
    return json.loads(path.read_text(encoding="utf-8-sig"))


def chunk_key(study):
    return "{}_chunks".format(study)


def planned_studies(args):
    if args.study == "all":
        return ["action_mask", "branchflow"]
    return [args.study]


def chunk_done(chunk):
    return resolve_path(chunk["case_summary"]).exists()


def missing_chunks(manifest, study):
    return [
        chunk
        for chunk in manifest.get(chunk_key(study), [])
        if not chunk_done(chunk)
    ]


def all_chunks_done(manifest, study):
    return all(chunk_done(chunk) for chunk in manifest.get(chunk_key(study), []))


def log_paths(args):
    log_dir = resolve_path(args.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    return {
        "log_dir": log_dir,
        "status_csv": log_dir / "ieee8500_remaining_criticality_status.csv",
        "summary_json": log_dir / "ieee8500_remaining_criticality_summary.json",
    }


def append_status(status_csv, row):
    fieldnames = [
        "timestamp",
        "event",
        "study",
        "target_start_index",
        "target_end_index_exclusive",
        "output_dir",
        "returncode",
        "duration_seconds",
        "message",
    ]
    exists = status_csv.exists()
    with status_csv.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if not exists:
            writer.writeheader()
        writer.writerow({field: row.get(field, "") for field in fieldnames})


def run_command(command, cwd, log_file):
    with log_file.open("w", encoding="utf-8", errors="replace") as handle:
        handle.write("command: {}\n\n".format(" ".join(command)))
        handle.flush()
        return subprocess.run(
            command,
            cwd=str(cwd),
            stdout=handle,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        ).returncode


def chunk_log_name(chunk):
    return "{}_chunk_{:04d}_{:04d}.log".format(
        chunk["study"],
        int(chunk["target_start_index"]),
        int(chunk["target_end_index_exclusive"]) - 1,
    )


def run_missing_chunks(args, manifest, study, paths):
    chunks = missing_chunks(manifest, study)
    if int(args.max_chunks) > 0:
        chunks = chunks[: int(args.max_chunks)]
    print(
        "{}: running {} missing chunks".format(study, len(chunks)),
        flush=True,
    )
    if args.dry_run:
        for chunk in chunks:
            print(
                "dry-run {} target_start={}".format(
                    study, chunk["target_start_index"]
                ),
                flush=True,
            )
        return []

    failures = []
    for index, chunk in enumerate(chunks, start=1):
        start = datetime.now()
        log_file = paths["log_dir"] / chunk_log_name(chunk)
        print(
            "[{}/{}] running {} target_start={} output={}".format(
                index,
                len(chunks),
                study,
                chunk["target_start_index"],
                chunk["output_dir"],
            ),
            flush=True,
        )
        returncode = run_command(chunk["command"], BASE_DIR, log_file)
        duration = (datetime.now() - start).total_seconds()
        case_path = resolve_path(chunk["case_summary"])
        ok = returncode == 0 and case_path.exists()
        append_status(
            paths["status_csv"],
            {
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "event": "chunk_complete" if ok else "chunk_failed",
                "study": study,
                "target_start_index": chunk["target_start_index"],
                "target_end_index_exclusive": chunk["target_end_index_exclusive"],
                "output_dir": chunk["output_dir"],
                "returncode": returncode,
                "duration_seconds": "{:.3f}".format(duration),
                "message": "log={}".format(log_file),
            },
        )
        if not ok:
            failures.append(
                {
                    "study": study,
                    "target_start_index": chunk["target_start_index"],
                    "returncode": returncode,
                    "log_file": str(log_file),
                    "case_summary_exists": case_path.exists(),
                }
            )
            print(
                "failed {} target_start={} returncode={} log={}".format(
                    study,
                    chunk["target_start_index"],
                    returncode,
                    log_file,
                ),
                flush=True,
            )
            break
        print(
            "completed {} target_start={} in {:.1f}s".format(
                study,
                chunk["target_start_index"],
                duration,
            ),
            flush=True,
        )
    return failures


def merge_command_for_study(manifest, study):
    for merge in manifest.get("merge_commands", []):
        if merge.get("study") == study:
            return merge
    return None


def run_merge(args, manifest, study, paths):
    merge = merge_command_for_study(manifest, study)
    if merge is None:
        return {"study": study, "merged": False, "reason": "missing_merge_command"}
    if not all_chunks_done(manifest, study):
        return {"study": study, "merged": False, "reason": "chunks_incomplete"}
    if args.dry_run:
        print("dry-run merge {}".format(study), flush=True)
        return {"study": study, "merged": False, "reason": "dry_run"}
    log_file = paths["log_dir"] / "{}_merge.log".format(study)
    print("merging {} into {}".format(study, merge["output_dir"]), flush=True)
    start = datetime.now()
    returncode = run_command(merge["command"], BASE_DIR, log_file)
    duration = (datetime.now() - start).total_seconds()
    ok = returncode == 0
    append_status(
        paths["status_csv"],
        {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "event": "merge_complete" if ok else "merge_failed",
            "study": study,
            "target_start_index": "",
            "target_end_index_exclusive": "",
            "output_dir": merge["output_dir"],
            "returncode": returncode,
            "duration_seconds": "{:.3f}".format(duration),
            "message": "log={}".format(log_file),
        },
    )
    return {
        "study": study,
        "merged": ok,
        "returncode": returncode,
        "duration_seconds": duration,
        "log_file": str(log_file),
        "output_dir": merge["output_dir"],
    }


def summarize(manifest, studies, failures, merge_results):
    summary = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "studies": {},
        "failures": failures,
        "merge_results": merge_results,
    }
    for study in studies:
        chunks = manifest.get(chunk_key(study), [])
        done_count = sum(1 for chunk in chunks if chunk_done(chunk))
        summary["studies"][study] = {
            "planned_chunks": len(chunks),
            "completed_chunks": done_count,
            "missing_chunks": len(chunks) - done_count,
            "all_chunks_done": done_count == len(chunks),
        }
    return summary


def main():
    args = parse_args()
    manifest = load_manifest(args.manifest)
    paths = log_paths(args)
    studies = planned_studies(args)

    failures = []
    for study in studies:
        failures.extend(run_missing_chunks(args, manifest, study, paths))
        if failures:
            break

    merge_results = []
    if not args.no_merge:
        for study in studies:
            merge_results.append(run_merge(args, manifest, study, paths))

    summary = summarize(manifest, studies, failures, merge_results)
    paths["summary_json"].write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, sort_keys=True), flush=True)
    if failures:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
