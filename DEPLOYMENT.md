# Deploy P6 Toolkit to Streamlit Community Cloud (v0.2.2)

## GitHub

1. Create a new repository, recommended name: `p6-toolkit-core`.
2. For testing, use a **private** repository if Community Cloud private-app quota is available.
3. Commit the contents of this directory at the **repository root**, not inside a `p6_toolkit_deploy` folder.
4. Keep `.streamlit/secrets.toml`, local XER schedules, `.venv` and customer files out of GitHub.

## Community Cloud

1. Sign in at https://share.streamlit.io and connect GitHub.
2. Create app > choose your repository and `main` branch.
3. Set **Main file path** to `app.py`.
4. Leave `requirements.txt` at the root (`-e .[ui]` installs this project's package and UI dependencies).
5. Choose a Python version compatible with `pyproject.toml` (Python 3.12 is a reasonable baseline; project supports >= 3.10).
6. Deploy.

## Access / secrets

This app has optional login. When no Streamlit `auth` secrets are configured it runs in open mode. **Do not make the app public with customer XER data or the expectation of protected access when authentication is off.** Keep the app private for initial tests, and configure the existing login if shared access is needed. Add users to the Community Cloud **Secrets** editor, never to the GitHub repository. Use `.streamlit/secrets.toml.example` only as a format reference. Hash passwords locally: `py -m p6toolkit hash-password`.

## Local run on Windows

```powershell
py -m pip install -e ".[ui,dev]"
py -m pytest -q
py -m streamlit run app.py
```

The app is read-only for XER input. Core 1.0 is under development; output is not a validated substitute for Primavera P6 scheduling.

## Publish from Windows with one command

Once you create the empty repository at `https://github.com/jaguado67/p6-toolkit-core` (do not initialize it with a README or license), extract this ZIP and run in its root folder:

```powershell
.\publish_to_github.ps1
```

Requires Git installed and authenticated to your GitHub account. The script refuses to overwrite an unrelated `origin` remote and never force-pushes.
