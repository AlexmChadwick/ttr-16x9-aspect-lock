# Push to public GitHub (AlexmChadwick/ttr-16x9-aspect-lock)

`gh` on this box is **not logged in**, and no GitHub MCP is available. Alex must authenticate, then create/push.

## One-time auth (on this machine or your laptop)
```bash
gh auth login
# choose GitHub.com → HTTPS → login with browser/token
gh auth status
```

## Create the target if needed

If the repository does not already exist, authenticate with `gh` and create
the exact public target. This command does not push the local source tree.

```bash
gh repo create AlexmChadwick/ttr-16x9-aspect-lock --public
```

## Push the local release

From `/workspace/ttr-aspect-lock`, after reviewing the clean release commit:

```bash
cd /workspace/ttr-aspect-lock
git remote add origin https://github.com/AlexmChadwick/ttr-16x9-aspect-lock.git
git push -u origin main
git tag -a v1.0.0 -m "v1.0.0"
git push origin v1.0.0
```

## Alternative without gh
1. Create empty public repo `ttr-16x9-aspect-lock` under AlexmChadwick in the GitHub UI.
2. Then:
```bash
git remote add origin https://github.com/AlexmChadwick/ttr-16x9-aspect-lock.git
git push -u origin main
git tag -a v1.0.0 -m "v1.0.0"
git push origin v1.0.0
```

## Release artifact
Create the `v1.0.0` GitHub Release after pushing the tag, then attach both
`dist/ttr-aspect-lock-1.0.0.zip` and
`dist/ttr-aspect-lock-1.0.0.zip.sha256`.
