
# Zepto Data & AI Platform — Capstone

An end-to-end AI/ML platform built as three internally-linked modules: a data-engineering
pipeline, an analytics/modeling pipeline, and a GenAI support assistant.

| Module | Path | What it does |
|---|---|---|
| Data Pipeline | [`/data_pipeline`](data_pipeline/) | Scrapes books.toscrape.com, cleans and converts currency, loads into a normalized SQLite DB, queries with SQL + pandas |
| Analytics | [`/analytics`](analytics/) | Profiles and cleans the Titanic dataset, tells a visual EDA story, then trains/tunes/evaluates 3 classifiers + a regression model |
| Support Assistant | [`/support_assistant`](support_assistant/) | RAG-based GenAI service answering Zepto policy questions via ChromaDB + LangGraph + FastAPI |

## Quick Setup

Each module has its **own `requirements.txt`** (three separate environments, since the
modules have unrelated dependencies — e.g. `analytics` needs `scikit-learn`/`seaborn` while
`support_assistant` needs `chromadb`/`langgraph`/`sentence-transformers`):

```
pip install -r data_pipeline/requirements.txt
pip install -r analytics/requirements.txt
pip install -r support_assistant/requirements.txt
```

## Quick Run

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

---

## Full Step-by-Step Guide (Beginner-Friendly, Start to Finish)

### Phase 0: Check prerequisites

```
python --version
git --version
gh --version
```
You should see version numbers for each. If `python` isn't found, install it from python.org
(check "Add Python to PATH" during install). If `git` isn't found, install from git-scm.com.

### Phase 1: Create the folder structure

```
mkdir zepto-capstone
cd zepto-capstone
mkdir data_pipeline
mkdir analytics
mkdir support_assistant
mkdir support_assistant\docs
```

```
zepto-capstone/
├── data_pipeline/       (empty for now)
├── analytics/           (empty for now)
└── support_assistant/   (empty for now)
```

### Phase 2: Initialize git

```
git init
git branch -M main
```
This creates an invisible notebook (`.git`) that remembers every version of your project:
```
zepto-capstone/
├── data_pipeline/
├── analytics/
├── support_assistant/
└── .git/   <-- invisible history tracker
```

Create a `.gitignore` file in the root with:
```
.venv/
__pycache__/
*.pyc
.ipynb_checkpoints/
.env
```
Then save your first snapshot:
```
git add .gitignore
git commit -m "Initial commit: project scaffolding"
```
Mental picture of a commit:
```
Your files NOW --git add--> "staged" --git commit -m "message"--> 📸 saved snapshot in history
```

### Phase 3: Set up a virtual environment (an isolated toolbox for Python packages)

```
python -m venv .venv
```
Without this, every Python project on your computer would share the same packages, causing
version conflicts. A virtual environment gives **this project** its own private toolbox:
```
Your computer
 ├── Project A → its own .venv (pandas 1.5)
 ├── Project B → its own .venv (pandas 2.1)
 └── zepto-capstone → its own .venv
```
Activate it (PowerShell):
```
.venv\Scripts\Activate.ps1
```
You'll know it worked when your prompt shows `(.venv)` at the front. Every `pip install` and
`python` command below should be run with this active.

### Phase 4: Module 1 — Data Pipeline

**What's inside:**
```
data_pipeline/
├── scraper.py         Step 1: goes to the website, grabs book data
├── clean.py            Step 2: fixes the data types (text -> numbers)
├── build_database.py   Step 3: saves the clean data into a mini-database
├── run_queries.py      Step 4: asks questions of that database
├── requirements.txt
├── README.md
└── data/                (auto-created)
    ├── books_raw.csv
    ├── books_clean.csv
    └── zepto_books.db
```

**What scraper.py extracts from each book card:**
```python
title = card.h3.a["title"]                                          # "A Light in the Attic"
price = card.find("p", class_="price_color").text                   # "£51.77"
rating = card.find("p", class_="star-rating")["class"][1]            # "Two"
availability = card.find("p", class_="instock availability").text.strip()  # "In stock"
```

**Sample of `books_raw.csv`** (straight out of the scraper — still messy text):
```
title,price,star_rating,availability,category
It's Only the Himalayas,£45.17,Two,In stock,Travel
```

**What clean.py does to that row:**
```python
price_gbp = float(price.replace("£", ""))                            # 45.17
rating = {"One":1,"Two":2,"Three":3,"Four":4,"Five":5}[star_rating]   # 2
in_stock = "in stock" in availability.lower()                         # True
price_inr = price_gbp * 105.50                                        # 4765.44
```

**Sample of `books_clean.csv`** (same row, now typed data):
```
title,price_gbp,price_inr,rating,in_stock,category
It's Only the Himalayas,45.17,4765.44,2,True,Travel
```

**The flow:**
```
[books.toscrape.com] --scraper.py--> books_raw.csv --clean.py--> books_clean.csv
                                                                        |
                                        build_database.py <-------------
                                                |
                                                v
                                        zepto_books.db --run_queries.py--> query_output.md
```

**Run it:**
```
cd data_pipeline
pip install -r requirements.txt
python scraper.py
python clean.py
python build_database.py
python run_queries.py
```

**Expected output at each step:**
| Command | You should see |
|---|---|
| `scraper.py` | `Total books scraped: 69` |
| `clean.py` | `Cleaning complete: 69 -> 69 rows (0 dropped)` |
| `build_database.py` | `Inserted 3 categories and 69 books into data/zepto_books.db` |
| `run_queries.py` | Ends with `Outputs match: True` |

### Phase 5: Module 2 — Analytics

**What's inside:**
```
analytics/
├── 01_eda.py             Step 1: loads Titanic data, explores it, makes charts
├── 02_modeling.py         Step 2: trains AI models to predict who survived
├── requirements.txt
├── README.md
├── titanic.csv            (created by step 1)
├── EDA_REPORT.md          (created by step 1)
├── MODELING_REPORT.md     (created by step 2)
├── model_pipeline.joblib  (created by step 2 — the trained model, saved to a file)
└── charts/                (created automatically — all PNG charts)
```

**The flow:**
```
[seaborn's built-in Titanic dataset]
        |
        v  01_eda.py
titanic.csv + EDA_REPORT.md + charts/*.png
        |
        v  02_modeling.py
MODELING_REPORT.md + model_pipeline.joblib
```

**Run it:**
```
cd analytics
pip install -r requirements.txt
python 01_eda.py
python 02_modeling.py
```

**Expected output:**
| Command | You should see |
|---|---|
| `01_eda.py` | `Saved full EDA report to EDA_REPORT.md` |
| `02_modeling.py` | Ends with `Reload check: ... MATCH` |

### Phase 6: Module 3 — Support Assistant

**What's inside:**
```
support_assistant/
├── docs/                 8 text files — Zepto's policies
│   ├── doc_01.txt  ... doc_08.txt
├── ingest.py             turns those 8 documents into searchable "AI memory"
├── prompts.py            the exact instructions given to the AI
├── schemas.py            defines the shape of the answer
├── graph.py              the "brain" — routes policy vs. general questions
├── llm.py                (optional) connects to a real AI model
├── main.py               starts the web server
├── requirements.txt
├── Dockerfile
└── README.md
```

**Sample doc (`docs/doc_01.txt`, full content):**
```
Zepto delivers grocery and household essentials to serviceable pin codes within 10 to 30
minutes of order confirmation, depending on the customer's delivery zone and current order
volume. Standard delivery is free on orders over INR 149; orders below this threshold incur
a flat INR 25 delivery fee. Priority delivery, which reserves the next available rider slot,
is available at checkout for an additional INR 15. Zepto does not currently deliver to
addresses outside its listed serviceable pin codes.
```
(7 more just like it: returns, membership, tracking, cancellation, damaged items, gift cards,
support hours.)

**`schemas.py` (full file — defines what an answer looks like):**
```python
class AskRequest(BaseModel):
    query: str

class AskResponse(BaseModel):
    answer: str
    sources: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
```

**The flow — how one question gets answered:**
```
You ask: "What is your delivery fee?"
        |
        v
[graph.py: classify_intent] -- checks for words like "delivery", "refund"...
        |
        |-- YES (policy question) --> searches the 8 documents --> builds an answer from them
        |
        |-- NO (unrelated question) --> "I can only answer Zepto policy questions"
```

**Run it:**
```
cd support_assistant
pip install -r requirements.txt
python main.py
```
Expected: `Uvicorn running on http://0.0.0.0:7860`. Then, in a **second terminal**:
```
curl -X POST http://localhost:7860/ask -H "Content-Type: application/json" -d "{\"query\": \"What is your delivery fee?\"}"
```
Expected: `{"answer":"Based on the retrieved context: Zepto delivers grocery...","sources":["doc_01"],"confidence":1.0}`

### Phase 7: Commit each module, then push

```
git checkout -b feature/data-pipeline
git add data_pipeline/
git commit -m "Add data pipeline: scraping, cleaning, database, queries"
git checkout main
git merge feature/data-pipeline --no-ff -m "Merge feature/data-pipeline"
```
Repeat the same pattern for `feature/analytics` and `feature/support-assistant`, then:
```
gh auth login
git remote add origin https://github.com/<your-username>/<your-repo>.git
git push -u origin main
```

---

## Troubleshooting — issues you may hit, and the fix

**`SSLCertVerificationError: self-signed certificate in certificate chain`**
→ A corporate network's TLS-inspection proxy, not a code bug. Ask IT about a corporate CA
bundle for `REQUESTS_CA_BUNDLE`. Never leave `verify=False` in submitted code — test-only.

**Price/text shows `Â£45.17` instead of `£45.17`**
→ The site doesn't declare a charset in its HTTP headers, so `requests` defaults to Latin-1.
Fix: `response.encoding = "utf-8"` right after `requests.get(...)`, before parsing.

**`ModuleNotFoundError: No module named 'X'`**
→ Either the venv isn't activated (look for `(.venv)` in your prompt), or you haven't run
`pip install -r requirements.txt` yet in that folder.

**`ImportError: Import tabulate failed`** (from `df.to_markdown()`)
→ Either `pip install tabulate`, or use `.to_string()` in a markdown code fence instead.

**Hugging Face model download hangs / "Application Blocked" page**
→ Corporate proxy blocking huggingface.co. Try a different network, or ask IT to allowlist it.

**`git push` → `[rejected] ... (fetch first)`**
→ The remote has commits you don't have locally (often: GitHub auto-created a README). Fix:
`git pull origin main --allow-unrelated-histories`, resolve any conflict, push again.

**Leftover `<<<<<<<`, `=======`, `>>>>>>>` markers in a file after resolving a conflict**
→ You committed before fully cleaning up. Open the file, delete the marker lines and the
content you don't want, save, `git add <file>`, `git commit`, push again. Always re-open and
read the file after resolving a conflict — don't just trust "merge succeeded."

**Push rejected due to permissions**
→ You're authenticated as a GitHub account without write access to that repo. Either
`gh auth login` as the repo owner's account, or have the owner add yours as a collaborator.

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
