# LeRoboto 🤗

This script imports a [Hugging Face LeRobot](https://github.com/huggingface/lerobot) dataset into [Roboto](https://roboto.ai), using one of two modes:

- `import`: Mirrors the dataset files from Hugging Face to your configured S3 bucket, then imports them to Roboto. This is ideal for large datasets or when using your own cloud storage.

- `upload`: Downloads the dataset files from Hugging Face and uploads them directly to Roboto. Use this for quick uploads without S3 involvement.

When using import mode, Roboto does not copy the source files — it simply records their location in your S3 bucket so they can be ingested in place.

## Requirements

- Python ≥ 3.10
- A Roboto account
- A Hugging Face account (if using private datasets)
- Environment variables set via `.env.local` file (see below)


Additional requirements for `import` mode:
- AWS CLI installed and available in your path
- AWS S3 bucket connected to your Roboto account
    - [Contact us](https://www.roboto.ai/contact) to configure this

## Setup

1. Clone this package:
    ```bash
    git clone https://github.com/roboto-ai/leroboto.git
    cd leroboto
    ```

2. Create a virtual environment:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Install dependencies:

    ```bash
    pip install roboto python-dotenv
    ```

4. Install `lerobot` from source (required for `LeRobotDataset`):

    ```bash
    git clone https://github.com/huggingface/lerobot.git
    cd lerobot
    pip install -e .
    ```

## Configuration

Create a `.env.local` file in the root directory of this repo.

Populate it by copying the provided example in `.env.example`:

```bash
# =============================
# Required for both modes
# =============================

# Hugging Face token
# Create one here: https://huggingface.co/settings/tokens
HF_TOKEN=hf_...

# Roboto token 
# Create one here: https://app.roboto.ai/settings/tokens
ROBOTO_API_KEY=roboto_pat_... # Optional if you already have: `~/.roboto/config.json`
ROBOTO_ORG_ID=og_...          # Optional if you're just in 1 org

# =============================
# Required for import mode only
# =============================

# S3 bucket to mirror HF dataset to
S3_BUCKET=your-s3-bucket
S3_PREFIX=hf-mirror           # Optional, defaults to 'hf-mirror'

# Read/write credentials to S3 bucket
AWS_ACCESS_KEY=...
AWS_SECRET_KEY=...

# Optional session token (if using temporary credentials)
AWS_SESSION_TOKEN=...
```

This file configures:
- Hugging Face access for downloading datasets
- Roboto access for importing or uploading datasets
- AWS S3 access for uploading mirrored content

#### AWS Permissions

For `import` mode, your AWS credentials will need read/write permissions to sync files to the S3 bucket. Here's an example policy you can use for constrained access:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:ListBucket",
                "s3:GetBucketLocation"
            ],
            "Resource": "arn:aws:s3:::your-s3-bucket"
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:GetObjectAcl",
                "s3:PutObject",
                "s3:PutObjectAcl",
                "s3:DeleteObject"
            ],
            "Resource": "arn:aws:s3:::your-s3-bucket/*"
        }
    ]
}
```

## Usage

```bash
python leroboto.py {import,upload} <huggingface_dataset_id> [<roboto_dataset_id>]
```
If a Roboto dataset ID is not provided, a new dataset will be created automatically.

### Modes
- `import`: Mirrors the dataset files from Hugging Face to your configured S3 bucket, then imports them to Roboto. This is ideal for large datasets or when using your own cloud storage.

- `upload`: Downloads the dataset files from Hugging Face and uploads them directly to Roboto. Use this for quick uploads without S3 involvement.

### Examples

Create a new Roboto dataset and import files into it:

```
python leroboto.py import lerobot/utokyo_xarm_bimanual
```

Import files into an existing Roboto dataset:

```
python leroboto.py import lerobot/utokyo_xarm_bimanual ds_abc123xyz
```

Upload files directly to Roboto without using your own S3 bucket:

```
python leroboto.py upload lerobot/utokyo_xarm_bimanual
```

#### Example `import` mode output

```
☁️ Starting mirror and import process:
   HF Dataset: lerobot/utokyo_xarm_bimanual
   Roboto Dataset: Will create new dataset

📁 Creating new Roboto dataset for lerobot/utokyo_xarm_bimanual...
✅ Created dataset: ds_tdnowr3uirfa

⬇️ Downloading lerobot/utokyo_xarm_bimanual...
✅ Downloaded files from Hugging Face in 0.4s

🔄 Syncing data to s3://your-s3-bucket/hf-mirror/lerobot/utokyo_xarm_bimanual
✅ Synced files to S3 in 0.8s

🧾 Preparing Roboto import batch...
🤖 Importing 145 files to Roboto: ds_tdnowr3uirfa
📦 Processing chunk 1/1 (145 files)...
✅ Chunk 1 imported successfully (145 files)

✅ Process complete — 145 total files in Roboto.

⬆️ Uploading manifest.txt to Roboto.
✅ Uploaded manifest.txt to ds_tdnowr3uirfa.

🔗 View dataset: https://app.roboto.ai/datasets/ds_tdnowr3uirfa
```

## Notes
- Paths like `.cache/`, `.lock`, `.metadata`, and `.gitignore` are excluded from upload.
- Roboto import occurs in chunks of 500 files.
- A `manifest.txt` is uploaded to Roboto to signal upload is complete so ingestion can begin.