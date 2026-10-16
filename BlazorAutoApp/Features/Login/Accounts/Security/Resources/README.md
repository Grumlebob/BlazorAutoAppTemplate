# Offline common-password resource

`10k-most-common.txt` is copied without modification from SecLists commit `f1196104c5594a19d78b486c52c0794b9d947993`, path `Passwords/Common-Credentials/10k-most-common.txt`.

- Source: https://github.com/danielmiessler/SecLists/blob/f1196104c5594a19d78b486c52c0794b9d947993/Passwords/Common-Credentials/10k-most-common.txt
- Raw SHA-256: `68782d6a4a19a4768d5f15dd66bd534e7a33055cc755411e33f16d18c50fdcce`
- Size: 73,026 bytes; 10,001 source lines.
- License: MIT; the original notice is retained in `SecLists-LICENSE.txt`.

The application embeds the file, verifies its hash and 256 KiB size bound, and parses it once. It compares whole candidates case-insensitively. It does not perform runtime downloads, substring rejection or a comprehensive breached-password check. Updates require source, hash, attribution and boundary-test review together.
