# CSE407 — GPU vs CPU Energy Dashboard

A Streamlit dashboard comparing GPU vs CPU energy profiles for everyday AI workloads
(image processing, text generation, chatbot), built on the results from the
`CSE407_GPU_vs_CPU_Energy_Profiling` notebooks.

The dashboard ships with your actual results already loaded (`data/results_summary.csv`),
so it works immediately — no setup needed to view it locally.

## Run it locally first (optional, to check it before deploying)

```bash
pip install -r requirements.txt
streamlit run app.py
```

This opens the dashboard at `http://localhost:8501`.

## Deploy for free (so it's reachable from any device, including mobile)

1. Create a free GitHub account if you don't have one, and a new **public** repo
   (e.g. `cse407-energy-dashboard`).
2. Push these three files/folders to that repo: `app.py`, `requirements.txt`, `data/`.
3. Go to **https://share.streamlit.io**, sign in with GitHub.
4. Click **New app** → pick your repo → branch `main` → main file `app.py` → **Deploy**.
5. After a minute or two you'll get a public URL like
   `https://cse407-energy-dashboard.streamlit.app` — this works on any phone or laptop,
   satisfying the "accessible from mobile network" requirement from the original
   instructions.

## Updating it later

You can change *anything* after deploying — nothing here is a one-shot output:

- **New data, no code change:** just open the live dashboard and use the
  "Upload results_summary.csv" box in the sidebar. This doesn't touch the deployed
  files at all, so it's the fastest way to look at a fresh run.
- **Make the bundled default data permanent:** replace `data/results_summary.csv` in
  your GitHub repo with the new file and commit — Streamlit Community Cloud
  auto-redetects the change and redeploys within about a minute.
- **Change the charts, layout, or add new ones:** edit `app.py` directly (either
  locally or in GitHub's web editor), commit, and it redeploys automatically the
  same way. For example, to add a new chart you'd add another `st.plotly_chart(...)`
  block following the same pattern as the existing ones.
- **Change the electricity rate default:** edit the `value=8.0` in the
  `st.sidebar.number_input(...)` call in `app.py`, or just type a new number into
  the sidebar each time you open it — that doesn't require redeploying at all.

## Files

- `app.py` — the dashboard itself
- `requirements.txt` — Python dependencies for Streamlit Cloud to install
- `data/results_summary.csv` — your current large-scale results, bundled as the default dataset
