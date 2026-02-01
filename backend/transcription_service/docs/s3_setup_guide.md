# S3 Configuration & Best Practices Guide

This guide explains how to configure the Transcription Service to use Amazon S3 with the `memorybun-assets` bucket.

## 1. Bucket Strategy

**Bucket Name**: `memorybun-assets`
**Region**: `eu-north-1`

We use a **Single Bucket** strategy. Assets are organized by folders (prefixes):
- `s3://memorybun-assets/screenshots/` - Screenshot images
- `s3://memorybun-assets/audio/` - Audio recordings (for future evaluation/training)

## 2. Recommended Workflow (Team Standard)

### Local Development: Use Filesystem
For all daily development, use the **Filesystem**. It mimics S3 but runs locally without internet or credentials.

**Configuration (`docker-compose.yml`)**:
Keep the defaults. You do **NOT** need to change anything or add any AWS keys.

```yaml
  transcription-service:
    environment:
      - STORAGE_TYPE=FILESYSTEM  # Default
      # - STORAGE_TYPE=S3        # Keep commented out
```

### Cloud Production: Use S3
When deployed to the cloud (ECS/EC2), the service should use S3.

**Configuration**:
Set these environment variables in your cloud deployment (e.g., via Terraform or ECS Task Definition):

```bash
STORAGE_TYPE=S3
S3_BUCKET=memorybun-assets
S3_REGION=eu-north-1
S3_PREFIX=screenshots
```

**Authentication**:
Cloud servers use **IAM Roles**. You do **not** need to set `AWS_ACCESS_KEY_ID` or `AWS_SECRET_ACCESS_KEY`. The server authenticates automatically.

---

## Appendix: Optional Local Testing (Sanity Check)

**Only read this section if you specifically need to test S3 connectivity from your local machine.** (e.g., debugging a permission issue).

### Docker Configuration for S3 Testing
Update `docker-compose.yml` temporarily:

```yaml
  transcription-service:
    environment:
      - STORAGE_TYPE=S3
      - S3_BUCKET=memorybun-assets
      - S3_REGION=eu-north-1
      - S3_PREFIX=screenshots
      # Local Keys (Never use in production!)
      - AWS_ACCESS_KEY_ID=your_access_key
      - AWS_SECRET_ACCESS_KEY=your_secret_key
```

### Getting Local Keys
1.  **AWS Console** -> **IAM** -> **Users**.
2.  Create user `memorybun-local-dev` with `AmazonS3FullAccess`.
3.  **Security credentials** -> **Create access key** (Local code).
4.  Copy Key ID and Secret.
