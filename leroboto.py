#!/usr/bin/env python3

import os
import sys
import time
import tempfile
import argparse
from pathlib import Path
import subprocess

# Set these before any other imports
# Suppress noisy progress bars for HF downloads
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
os.environ["TQDM_DISABLE"] = "1"

from roboto import Dataset, File

from dotenv import load_dotenv

# === CONFIGURATION ===

# Load environment variables from a local .env file
load_dotenv(dotenv_path=".env.local")

S3_BUCKET = os.environ.get("S3_BUCKET")
S3_PREFIX = os.environ.get("S3_PREFIX", "hf-mirror")

AWS_ACCESS_KEY = os.environ.get("AWS_ACCESS_KEY")
AWS_SECRET_KEY = os.environ.get("AWS_SECRET_KEY")
AWS_SESSION_TOKEN = os.environ.get("AWS_SESSION_TOKEN")

HF_TOKEN = os.environ.get("HF_TOKEN")
ROBOTO_ORG_ID = os.environ.get("ROBOTO_ORG_ID")

# https://github.com/huggingface/lerobot
from lerobot.datasets.lerobot_dataset import LeRobotDataset


def should_exclude(path: Path, local_root: Path) -> bool:
    """Check if a path should be excluded based on the same patterns used in S3 sync."""
    relative_path = path.relative_to(local_root)
    path_str = str(relative_path).replace("\\", "/")

    # Exclude .cache directory and subdirectories
    if path_str.startswith(".cache/") or path_str == ".cache":
        return True

    # Exclude certain file extensions
    if path_str.endswith((".lock", ".metadata", ".gitignore", ".gitattributes")):
        return True

    return False


def construct_import_records(
    local_root: Path, bucket: str, prefix: str, dataset_id: str
):
    """Construct import records for all files that were synced to S3."""
    print("🧾 Preparing Roboto import batch...")

    records = []

    for path in local_root.rglob("*"):
        if path.is_file() and not should_exclude(path, local_root):
            relative_path = path.relative_to(local_root)
            s3_key = f"{prefix}/{relative_path}".replace("\\", "/")
            file_size_bytes = path.stat().st_size

            records.append(
                {
                    "uri": f"s3://{bucket}/{s3_key}",
                    "dataset_id": dataset_id,
                    "relative_path": str(relative_path),
                    "size": file_size_bytes,
                }
            )

    return records


def sync_hf_dataset_to_s3(local_path: str, bucket: str, prefix: str):
    """Syncs the local directory to the specified S3 bucket and prefix."""
    print(f"🔄 Syncing data to s3://{bucket}/{prefix}")
    start_time = time.time()

    try:
        s3_uri = f"s3://{bucket}/{prefix}"
        env = os.environ.copy()
        env["AWS_ACCESS_KEY_ID"] = AWS_ACCESS_KEY
        env["AWS_SECRET_ACCESS_KEY"] = AWS_SECRET_KEY
        if AWS_SESSION_TOKEN:
            env["AWS_SESSION_TOKEN"] = AWS_SESSION_TOKEN
        subprocess.run(
            [
                "aws",
                "s3",
                "sync",
                str(local_path),
                s3_uri,
                "--only-show-errors",
                "--quiet",
                "--exclude",
                ".cache/**",
                "--exclude",
                "*.lock",
                "--exclude",
                "*.metadata",
                "--exclude",
                ".gitignore",
                "--exclude",
                ".gitattributes",
            ],
            check=True,
            env=env,
        )
    except subprocess.CalledProcessError as e:
        print(f"❌ S3 sync failed with exit code {e.returncode}")
        print(f"   Command: {' '.join(e.cmd)}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ S3 sync failed: {str(e)}")
        sys.exit(1)

    elapsed = time.time() - start_time
    print(f"✅ Synced files to S3 in {elapsed:.1f}s\n")


def import_records_in_chunks(import_records, dataset_id, batch_size=500):
    """Import records to Roboto in chunks to handle batch size limits."""
    print(f"🤖 Importing {len(import_records)} files to Roboto: {dataset_id}")

    all_imported_files = []

    # Process in chunks
    for i in range(0, len(import_records), batch_size):
        chunk = import_records[i : i + batch_size]
        chunk_num = (i // batch_size) + 1
        total_chunks = (len(import_records) + batch_size - 1) // batch_size

        print(f"📦 Processing chunk {chunk_num}/{total_chunks} ({len(chunk)} files)...")

        try:
            files = File.import_batch(
                chunk, roboto_client=None, caller_org_id=ROBOTO_ORG_ID
            )

            if files:
                all_imported_files.extend(files)
                print(
                    f"✅ Chunk {chunk_num} imported successfully ({len(files)} files)"
                )
            else:
                print(f"⚠️ Chunk {chunk_num} returned no files")

        except Exception as e:
            print(f"❌ Error importing chunk {chunk_num}: {str(e)}")
            continue

    return all_imported_files


def download_dataset_from_hf(hf_dataset_id: str) -> Path:
    """Downloads a Hugging Face dataset and returns the local path."""
    print(f"⬇️  Downloading {hf_dataset_id}...")
    start_time = time.time()

    try:
        dataset = LeRobotDataset(hf_dataset_id)
    except Exception as e:
        print(f"❌ Failed to download using LeRobotDataset: {str(e)}")
        sys.exit(1)

    elapsed = time.time() - start_time
    print(f"✅ Downloaded files from Hugging Face in {elapsed:.1f}s\n")

    return dataset.root


def resolve_roboto_dataset(
    hf_dataset_id: str, roboto_dataset_id: str = None
) -> Dataset:
    """
    Creates a new Roboto dataset if roboto_dataset_id is None.
    Otherwise, returns the existing one. Exits on failure.
    """
    if roboto_dataset_id is None:
        print(f"📁 Creating new Roboto dataset for {hf_dataset_id}...")
        dataset_name = hf_dataset_id
        dataset_description = f"Mirrored from Hugging Face dataset: {hf_dataset_id}"

        try:
            dataset = Dataset.create(
                name=dataset_name,
                description=dataset_description,
                tags=["LeRobot"],
                caller_org_id=ROBOTO_ORG_ID,
            )
            roboto_dataset_id = dataset.dataset_id
            print(f"✅ Created dataset: {roboto_dataset_id}\n")
        except Exception as e:
            print(f"❌ Failed to create Roboto dataset: {str(e)}")
            sys.exit(1)
    else:
        try:
            dataset = Dataset.from_id(roboto_dataset_id)
            print(f"📁 Using existing Roboto dataset: {roboto_dataset_id}\n")
        except Exception as e:
            print(f"❌ Failed to get Roboto dataset: {str(e)}")
            sys.exit(1)

    return dataset


def finalize(files: list, roboto_dataset: str):
    """
    Upload a manifest file to Roboto. This signals that the upload or import
    process is complete and ingestion can begin.
    """
    if files:
        print(f"✅ Process complete — {len(files)} total files in Roboto.\n")
        manifest_lines = []

        # Populate the file with a manifest
        for f in files:
            if hasattr(f, "relative_path"):
                manifest_lines.append(f.relative_path)
            elif isinstance(f, Path):
                manifest_lines.append(str(f))

        manifest_text = "\n".join(sorted(manifest_lines))

        # Write to a temporary file
        with tempfile.NamedTemporaryFile("w+", suffix=".txt", delete=False) as tf:
            tf.write(manifest_text)
            tf.flush()
            manifest_path = Path(tf.name)

        # Upload manifest.txt to dataset root
        print(f"⬆️  Uploading manifest.txt to Roboto.")
        roboto_dataset.upload_files(
            files=[manifest_path],
            file_destination_paths={manifest_path: "manifest.txt"},
            print_progress=False,
        )
        print(f"✅ Uploaded manifest.txt to {roboto_dataset.dataset_id}.")
        print("")
        print(
            f"🔗 View dataset: https://app.roboto.ai/datasets/{roboto_dataset.dataset_id}"
        )
    else:
        print("⚠️  No files imported to Roboto.")


def s3_mirror_and_import(
    hf_dataset_id: str, roboto_dataset_id: str = None, hf_repo_dir: Path = None
):
    """Mirror Hugging Face dataset to S3 then import to Roboto."""
    # Sync HF dataset to S3 bucket
    full_s3_prefix = f"{S3_PREFIX}/{hf_dataset_id}"
    sync_hf_dataset_to_s3(hf_repo_dir, S3_BUCKET, full_s3_prefix)

    # Prepare S3 URIs to import into Roboto
    import_records = construct_import_records(
        hf_repo_dir, S3_BUCKET, full_s3_prefix, roboto_dataset_id
    )

    # Import files to Roboto in chunks
    files = import_records_in_chunks(import_records, roboto_dataset_id)
    return files


def direct_roboto_upload(roboto_dataset: Dataset = None, hf_repo_dir: Path = None):
    """Directly upload a Hugging Face dataset to a Roboto dataset."""
    # Gather all local HF dataset files recursively
    local_files = [
        p
        for p in hf_repo_dir.rglob("*")
        if p.is_file() and not should_exclude(p, hf_repo_dir)
    ]

    # Preserve relative path structure inside the dataset
    file_destination_paths = {
        path: str(path.relative_to(hf_repo_dir)) for path in local_files
    }

    try:
        print("⬆️  Uploading files directly to Roboto...")
        roboto_dataset.upload_files(
            files=local_files,
            file_destination_paths=file_destination_paths,
            print_progress=True,
        )
    except Exception as e:
        print(f"❌ Failed to upload files to Roboto dataset: {str(e)}")
        sys.exit(1)

    return local_files


def process_dataset(
    hf_dataset_id: str, roboto_dataset_id: str = None, direct_upload: bool = False
):
    """Process a Hugging Face LeRobot dataset and bring it to Roboto."""

    # Step 1: Create or resolve provided Roboto dataset
    roboto_dataset = resolve_roboto_dataset(hf_dataset_id, roboto_dataset_id)

    # Step 2: Download dataset from Hugging Face
    hf_repo_dir = download_dataset_from_hf(hf_dataset_id)

    # Step 3: Either upload files to Roboto directly, or mirror them to S3 and then import to Roboto
    if direct_upload:
        files = direct_roboto_upload(roboto_dataset, hf_repo_dir)
    else:
        files = s3_mirror_and_import(
            hf_dataset_id, roboto_dataset.dataset_id, hf_repo_dir
        )

    print("")

    # Step 4: Upload manifest file to Roboto to signal completion, so ingestion can begin
    finalize(files, roboto_dataset)


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Import a Hugging Face dataset into Roboto, either by mirroring the data to S3 "
            "and importing from there, or by uploading the files directly to Roboto."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s import lerobot/utokyo_xarm_bimanual               # Mirror to S3 and import into Roboto
  %(prog)s import lerobot/utokyo_xarm_bimanual ds_abc123     # Use existing Roboto dataset
  %(prog)s upload lerobot/utokyo_xarm_bimanual               # Direct upload to Roboto
        """,
    )

    parser.add_argument(
        "mode",
        choices=["import", "upload"],
        help="Mode: 'import' (mirror to S3 and import to Roboto) or 'upload' (direct upload to Roboto)",
    )

    parser.add_argument(
        "hf_dataset_id",
        help="Hugging Face dataset ID (e.g., 'lerobot/utokyo_xarm_bimanual')",
    )

    parser.add_argument(
        "roboto_dataset_id",
        nargs="?",
        help="Optional: Roboto dataset ID (use existing if provided)",
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    direct_upload = args.mode == "upload"

    if direct_upload:
        print("🎯 Starting direct download and upload process:")
    else:
        print("☁️  Starting mirror and import process:")

    print(f"   HF Dataset: {args.hf_dataset_id}")
    if args.roboto_dataset_id:
        print(f"   Roboto Dataset: {args.roboto_dataset_id} (existing)")
    else:
        print("   Roboto Dataset: Will create new dataset")
    print("")

    process_dataset(args.hf_dataset_id, args.roboto_dataset_id, direct_upload)
