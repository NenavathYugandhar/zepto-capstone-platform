
# Zepto Data & AI Platform — Capstone

An end-to-end AI/ML platform built as three internally-linked modules: a data-engineering
pipeline, an analytics/modeling pipeline, and a GenAI support assistant.

| Module | Path | What it does |
|---|---|---|
| Data Pipeline | [`/data_pipeline`](data_pipeline/) | Scrapes books.toscrape.com, cleans and converts currency, loads into a normalized SQLite DB, queries with SQL + pandas |
| Analytics | [`/analytics`](analytics/) | Profiles and cleans the Titanic dataset, tells a visual EDA story, then trains/tunes/evaluates 3 classifiers + a regression model |
| Support Assistant | [`/support_assistant`](support_assistant/) | RAG-based GenAI service answering Zepto policy questions via ChromaDB + LangGraph + FastAPI |

## Setup

Each module has its **own `requirements.txt`** (three separate environments, since the
modules have unrelated dependencies — e.g. `analytics` needs `scikit-learn`/`seaborn` while
`support_assistant` needs `chromadb`/`langgraph`/`sentence-transformers`):

```
pip install -r data_pipeline/requirements.txt
pip install -r analytics/requirements.txt
pip install -r support_assistant/requirements.txt
```

## Running each module end to end

**Data Pipeline:**
```
cd data_pipeline
python scraper.py && python clean.py && python build_database.py && python run_queries.py
```

**Analytics:**
```
cd analytics
python 01_eda.py && python 02_modeling.py
```

**Support Assistant:**
```
cd support_assistant
python main.py
# in another terminal:
curl -X POST http://localhost:7860/ask -H "Content-Type: application/json" -d '{"query": "What is your delivery fee?"}'
```
or via Docker: `docker build -t zepto-support-assistant support_assistant && docker run -p 7860:7860 zepto-support-assistant`

## Design decisions summary

- **Data Pipeline:** scraped 3 categories (Travel, Mystery, Historical Fiction) for 69 books
  total. Fixed conversion rate 1 GBP = 105.50 INR, per spec. Unparseable categorical fields
  (rating/stock status) are dropped; unparseable numeric price is median-imputed. Full
  reasoning in [`data_pipeline/README.md`](data_pipeline/README.md).
- **Analytics:** missing-value handling follows the assignment's percentage thresholds exactly
  (age ~20% imputed, embarked <5% dropped, deck ~77% dropped entirely). All modeling
  preprocessing is fit on the training split only via `ColumnTransformer` + `Pipeline` to
  avoid leakage. Every written interpretation in the generated reports is computed
  programmatically from the real run's statistics, not pre-written. Full reasoning in
  [`analytics/README.md`](analytics/README.md).
- **Support Assistant:** all 8 policy documents are embedded locally (no API key) and stored
  in ChromaDB. `MOCK_LLM` (default on) makes the entire pipeline deterministic and networkless
  except for the one-time local embedding-model download. Full architecture walkthrough in
  [`support_assistant/README.md`](support_assistant/README.md).

## Git workflow

This repository's history includes three feature branches (`feature/data-pipeline`,
`feature/analytics`, `feature/support-assistant`), each committed to multiple times and
merged back into `main` via `--no-ff` merges — visible with `git log --graph --all`.

## A known environment limitation, stated transparently

Parts of this repository (the `analytics` and `support_assistant` modules specifically) were
authored on a corporate network that blocks package installs/model downloads needed to
*execute* them end-to-end in that environment (Hugging Face is proxy-blocked there). The code
is complete and was reasoned through carefully for correctness, and `data_pipeline` was fully
executed and verified live. `analytics` and `support_assistant` should be run once on an
unrestricted machine (which is required anyway, to capture real metric values and real example
API transcripts for submission) before final submission — see the note in
[`support_assistant/README.md`](support_assistant/README.md) for specifics.
