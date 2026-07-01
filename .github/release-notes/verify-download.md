**Checksum (recommended):**

```bash
shasum -a 256 -c SHA256SUMS.txt
```

(Run in the folder where you downloaded the DMG and `SHA256SUMS.txt`.)

**After launch (~5 s):**

```bash
curl -s http://127.0.0.1:8123/health
```

Expected: `{"status":"ok"}`
