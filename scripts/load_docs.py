"""Upload documents to S3 and index them in the knowledge base.

Usage: python scripts/load_docs.py [folder]

The folder defaults to sample_docs. Run this after 'cdk deploy' and again
each time the documents change.
"""

import sys
import time
from pathlib import Path

import boto3

STACK_NAME = "KnowledgeBaseAgent"
ROOT = Path(__file__).resolve().parent.parent


def stack_outputs():
    stack = boto3.client("cloudformation").describe_stacks(StackName=STACK_NAME)
    outputs = stack["Stacks"][0]["Outputs"]
    return {item["OutputKey"]: item["OutputValue"] for item in outputs}


def upload_folder(folder, bucket_name):
    s3 = boto3.client("s3")
    count = 0
    for path in sorted(folder.iterdir()):
        if path.is_file():
            s3.upload_file(str(path), bucket_name, path.name)
            print(f"Uploaded {path.name}")
            count += 1
    return count


def index_documents(knowledge_base_id, data_source_id):
    bedrock = boto3.client("bedrock-agent")
    job = bedrock.start_ingestion_job(
        knowledgeBaseId=knowledge_base_id, dataSourceId=data_source_id
    )["ingestionJob"]

    while job["status"] in ("STARTING", "IN_PROGRESS"):
        time.sleep(5)
        job = bedrock.get_ingestion_job(
            knowledgeBaseId=knowledge_base_id,
            dataSourceId=data_source_id,
            ingestionJobId=job["ingestionJobId"],
        )["ingestionJob"]
        print(f"Indexing status: {job['status']}")
    return job


def main():
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "sample_docs"
    if not folder.is_dir():
        sys.exit(f"Folder not found: {folder}")

    outputs = stack_outputs()
    count = upload_folder(folder, outputs["DocsBucketName"])
    if count == 0:
        sys.exit(f"No files found in {folder}")

    job = index_documents(outputs["KnowledgeBaseId"], outputs["DataSourceId"])
    if job["status"] != "COMPLETE":
        sys.exit(f"Indexing failed: {job.get('failureReasons', job['status'])}")
    print(f"Done. Indexed {count} documents.")


if __name__ == "__main__":
    main()
