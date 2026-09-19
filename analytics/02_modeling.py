"""Part B: predictive modeling pipeline, continuing from the same Titanic data.

Reads the committed titanic.csv produced by 01_eda.py (the raw snapshot) —
this is a continuation of that one load, not a second network/cache call.
All preprocessing is fit on the training split only and applied in
transform-only mode to the test split, to avoid leakage.
"""
import os

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from imblearn.over_sampling import SMOTE
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import GridSearchCV, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier, plot_tree

CHARTS_DIR = "charts"
os.makedirs(CHARTS_DIR, exist_ok=True)
report_lines = ["# Modeling Report\n"]


def log(text: str, also_print: bool = True):
    report_lines.append(text)
    if also_print:
        print(text)


# ---------------------------------------------------------------------------
# Load the same raw snapshot 01_eda.py produced (continuation, not a new load)
# ---------------------------------------------------------------------------
df = pd.read_csv("titanic.csv")

FEATURES = ["pclass", "sex", "age", "sibsp", "parch", "fare", "embarked"]
TARGET = "survived"
NUMERIC_FEATURES = ["age", "fare", "sibsp", "parch", "pclass"]
CATEGORICAL_FEATURES = ["sex", "embarked"]

X = df[FEATURES]
y = df[TARGET]

log(
    "**Features used:** pclass, sex, age, sibsp, parch, fare, embarked. "
    "Excluded: `alive` (directly encodes the target — would leak), `deck` "
    "(too much missingness, dropped in EDA), and `who`/`adult_male`/`alone`/"
    "`class`/`embark_town` (redundant derivations of columns already included).\n"
)

# ---------------------------------------------------------------------------
# Task 1: Stratified train/test split (BEFORE any preprocessing)
# ---------------------------------------------------------------------------
class_balance = y.value_counts(normalize=True)
log(
    f"**Class balance (survived):** {class_balance.get(1, 0):.1%} survived, "
    f"{class_balance.get(0, 0):.1%} did not. Since the classes are imbalanced, "
    f"a plain random split risks producing a train or test set with a noticeably "
    f"different survival ratio than the full data, which would bias evaluation "
    f"metrics. **Stratified splitting** preserves this ratio in both splits.\n"
)

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, stratify=y, random_state=42
)

# ---------------------------------------------------------------------------
# Task 2: Preprocessing — fit on train only, ColumnTransformer + Pipeline
# ---------------------------------------------------------------------------
preprocessor = ColumnTransformer(
    transformers=[
        (
            "num",
            Pipeline([("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler())]),
            NUMERIC_FEATURES,
        ),
        (
            "cat",
            Pipeline(
                [
                    ("imputer", SimpleImputer(strategy="most_frequent")),
                    ("onehot", OneHotEncoder(handle_unknown="ignore")),
                ]
            ),
            CATEGORICAL_FEATURES,
        ),
    ]
)

# ---------------------------------------------------------------------------
# Task 3 & 4: Train 3 classifiers on the identical split, evaluate each
# ---------------------------------------------------------------------------
classifiers = {
    "Logistic Regression": LogisticRegression(max_iter=1000, random_state=42),
    "Decision Tree": DecisionTreeClassifier(random_state=42),
    "Random Forest": RandomForestClassifier(random_state=42),
}

fitted_pipelines = {}
metrics_rows = []

for name, clf in classifiers.items():
    pipe = Pipeline([("preprocessor", preprocessor), ("classifier", clf)])
    pipe.fit(X_train, y_train)
    fitted_pipelines[name] = pipe

    y_pred = pipe.predict(X_test)
    y_proba = pipe.predict_proba(X_test)[:, 1]

    cm = confusion_matrix(y_test, y_pred)
    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred)
    rec = recall_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)
    auc = roc_auc_score(y_test, y_proba)

    metrics_rows.append(
        {"model": name, "accuracy": acc, "precision": prec, "recall": rec, "f1": f1, "auc": auc}
    )
    log(f"**{name}** — confusion matrix:\n```\n{cm}\n```")
    log(
        f"accuracy={acc:.3f}, precision={prec:.3f}, recall={rec:.3f}, "
        f"f1={f1:.3f}, AUC={auc:.3f}\n"
    )

metrics_df = pd.DataFrame(metrics_rows).set_index("model")
log("### Classifier comparison table\n\n```\n" + metrics_df.round(3).to_string() + "\n```\n")

# ROC curves, all 3 models on one plot
plt.figure(figsize=(7, 6))
for name, pipe in fitted_pipelines.items():
    y_proba = pipe.predict_proba(X_test)[:, 1]
    fpr, tpr, _ = roc_curve(y_test, y_proba)
    plt.plot(fpr, tpr, label=f"{name} (AUC={roc_auc_score(y_test, y_proba):.3f})")
plt.plot([0, 1], [0, 1], "k--", label="Chance")
plt.xlabel("False Positive Rate")
plt.ylabel("True Positive Rate")
plt.title("ROC Curves")
plt.legend()
plt.tight_layout()
plt.savefig(f"{CHARTS_DIR}/roc_curves.png")
plt.close()

# Decision tree visualization
dt_pipe = fitted_pipelines["Decision Tree"]
feature_names = dt_pipe.named_steps["preprocessor"].get_feature_names_out()
plt.figure(figsize=(20, 10))
plot_tree(
    dt_pipe.named_steps["classifier"],
    feature_names=feature_names,
    class_names=["Died", "Survived"],
    filled=True,
    max_depth=3,  # limit depth for a readable rendering
)
plt.title("Decision Tree (top 3 levels shown)")
plt.tight_layout()
plt.savefig(f"{CHARTS_DIR}/decision_tree.png")
plt.close()
log(f"Saved ROC curves to `{CHARTS_DIR}/roc_curves.png` and the decision tree to `{CHARTS_DIR}/decision_tree.png`.\n")

# ---------------------------------------------------------------------------
# Task 5: Imbalance handling comparison (baseline vs class_weight vs SMOTE)
# ---------------------------------------------------------------------------
log("## Imbalance Handling Comparison\n")

X_train_proc = preprocessor.fit_transform(X_train, y_train)
X_test_proc = preprocessor.transform(X_test)

imbalance_results = {}

# (a) baseline
rf_baseline = RandomForestClassifier(random_state=42)
rf_baseline.fit(X_train_proc, y_train)
pred = rf_baseline.predict(X_test_proc)
imbalance_results["baseline"] = (precision_score(y_test, pred), recall_score(y_test, pred), f1_score(y_test, pred))

# (b) class_weight='balanced'
rf_balanced = RandomForestClassifier(random_state=42, class_weight="balanced")
rf_balanced.fit(X_train_proc, y_train)
pred = rf_balanced.predict(X_test_proc)
imbalance_results["class_weight=balanced"] = (precision_score(y_test, pred), recall_score(y_test, pred), f1_score(y_test, pred))

# (c) SMOTE — applied to the training fold only, after preprocessing (SMOTE needs numeric input)
smote = SMOTE(random_state=42)
X_train_smote, y_train_smote = smote.fit_resample(X_train_proc, y_train)
rf_smote = RandomForestClassifier(random_state=42)
rf_smote.fit(X_train_smote, y_train_smote)
pred = rf_smote.predict(X_test_proc)
imbalance_results["SMOTE"] = (precision_score(y_test, pred), recall_score(y_test, pred), f1_score(y_test, pred))

imbalance_df = pd.DataFrame(imbalance_results, index=["precision", "recall", "f1"]).T
log("```\n" + imbalance_df.round(3).to_string() + "\n```\n")

best_strategy = imbalance_df["f1"].idxmax()
log(
    f"**Conclusion:** of the three strategies, **{best_strategy}** achieved the highest "
    f"F1 score ({imbalance_df.loc[best_strategy, 'f1']:.3f}), "
    f"trading precision={imbalance_df.loc[best_strategy, 'precision']:.3f} against "
    f"recall={imbalance_df.loc[best_strategy, 'recall']:.3f}. Since Titanic's class "
    f"imbalance is moderate (not extreme), the differences between strategies are "
    f"modest here — the effect would likely be larger on a more heavily imbalanced dataset.\n"
)

# ---------------------------------------------------------------------------
# Task 6: GridSearchCV tuning Random Forest (with OOB score)
# ---------------------------------------------------------------------------
log("## Hyperparameter Tuning (Random Forest)\n")

rf_pipe = Pipeline(
    [("preprocessor", preprocessor), ("classifier", RandomForestClassifier(oob_score=True, random_state=42))]
)
param_grid = {
    "classifier__n_estimators": [100, 200, 300],
    "classifier__max_depth": [None, 5, 10],
    "classifier__max_features": ["sqrt", "log2"],
}
grid_search = GridSearchCV(rf_pipe, param_grid, cv=5, scoring="accuracy", n_jobs=-1)
grid_search.fit(X_train, y_train)

best_rf_pipe = grid_search.best_estimator_
oob = best_rf_pipe.named_steps["classifier"].oob_score_
log(f"**Best params:** {grid_search.best_params_}")
log(f"**OOB score of best estimator:** {oob:.3f}\n")

# ---------------------------------------------------------------------------
# Task 7: Regression side-task — predict fare from other features
# ---------------------------------------------------------------------------
log("## Regression Side-Task: Predicting fare\n")

REG_FEATURES = ["pclass", "sex", "age", "sibsp", "parch", "embarked", "survived"]
REG_NUMERIC = ["age", "sibsp", "parch", "pclass", "survived"]
REG_CATEGORICAL = ["sex", "embarked"]

X_reg = df[REG_FEATURES]
y_reg = df["fare"]

X_reg_train, X_reg_test, y_reg_train, y_reg_test = train_test_split(
    X_reg, y_reg, test_size=0.2, random_state=42
)

reg_preprocessor = ColumnTransformer(
    [
        (
            "num",
            Pipeline([("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler())]),
            REG_NUMERIC,
        ),
        (
            "cat",
            Pipeline([("imputer", SimpleImputer(strategy="most_frequent")), ("onehot", OneHotEncoder(handle_unknown="ignore"))]),
            REG_CATEGORICAL,
        ),
    ]
)

reg_pipe = Pipeline([("preprocessor", reg_preprocessor), ("regressor", LinearRegression())])
reg_pipe.fit(X_reg_train, y_reg_train)
y_reg_pred = reg_pipe.predict(X_reg_test)

mae = mean_absolute_error(y_reg_test, y_reg_pred)
rmse = np.sqrt(mean_squared_error(y_reg_test, y_reg_pred))
r2 = r2_score(y_reg_test, y_reg_pred)
n, p = len(y_reg_test), len(REG_FEATURES)
adj_r2 = 1 - (1 - r2) * (n - 1) / (n - p - 1)

log(f"MAE={mae:.2f}, RMSE={rmse:.2f}, R2={r2:.3f}, Adjusted R2={adj_r2:.3f}\n")

residuals = y_reg_test - y_reg_pred
plt.figure(figsize=(7, 5))
plt.scatter(y_reg_pred, residuals, alpha=0.6)
plt.axhline(0, color="red", linestyle="--")
plt.xlabel("Predicted fare")
plt.ylabel("Residual")
plt.title("Residual plot")
plt.tight_layout()
plt.savefig(f"{CHARTS_DIR}/residual_plot.png")
plt.close()

hetero_corr = np.corrcoef(y_reg_pred, np.abs(residuals))[0, 1]
if abs(hetero_corr) > 0.2:
    hetero_conclusion = (
        f"The correlation between predicted fare and |residual| is {hetero_corr:.2f}, "
        f"indicating **heteroscedasticity** — residual spread grows with predicted value, "
        f"consistent with fare's right-skewed distribution seen in the EDA."
    )
else:
    hetero_conclusion = (
        f"The correlation between predicted fare and |residual| is only {hetero_corr:.2f}, "
        f"suggesting residual spread is **roughly constant (homoscedastic)** across the "
        f"range of predictions."
    )
log(hetero_conclusion + "\n")

# ---------------------------------------------------------------------------
# Task 8: Final comparison table + recommendation
# ---------------------------------------------------------------------------
log("## Final Model Comparison\n")
log("### Classification metrics\n\n```\n" + metrics_df.round(3).to_string() + "\n```\n")
log(
    "### Regression metrics\n\n```\n"
    + pd.DataFrame(
        {"MAE": [mae], "RMSE": [rmse], "R2": [r2], "Adjusted_R2": [adj_r2]}, index=["Linear Regression (fare)"]
    ).round(3).to_string()
    + "\n```\n"
)
log(
    "Classification and regression metrics are on different scales (probabilities/rates "
    "vs. currency units) and are shown as separate tables above rather than one merged scale.\n"
)

best_classifier = metrics_df["f1"].idxmax()
best_row = metrics_df.loc[best_classifier]
log(
    f"**Recommendation:** deploy **{best_classifier}**. It achieved the highest F1 score "
    f"({best_row['f1']:.3f}) among the three classifiers, with accuracy={best_row['accuracy']:.3f} "
    f"and AUC={best_row['auc']:.3f}. "
    + (
        "Random Forest's ensemble of trees typically generalizes better than a single "
        "Decision Tree and captures non-linear feature interactions that Logistic "
        "Regression cannot, which matches the metrics observed here. "
        if best_classifier == "Random Forest"
        else "This model's specific balance of precision and recall on this test split "
        "made it the strongest choice among the three tried here. "
    )
    + f"The tuned Random Forest (OOB score {oob:.3f}) is saved as the deployable "
    f"pipeline below since it incorporates the hyperparameter search.\n"
)

# ---------------------------------------------------------------------------
# Task 9: Save the full fitted pipeline (preprocessing + estimator together)
# ---------------------------------------------------------------------------
joblib.dump(best_rf_pipe, "model_pipeline.joblib")
log("Saved the tuned Random Forest pipeline (preprocessing + model) to model_pipeline.joblib\n")

reloaded = joblib.load("model_pipeline.joblib")
sample_raw = X_test.iloc[[0]]
original_pred = best_rf_pipe.predict(sample_raw)[0]
reloaded_pred = reloaded.predict(sample_raw)[0]
log(
    f"**Reload check:** original pipeline predicted {original_pred}, reloaded pipeline "
    f"predicted {reloaded_pred} on the same raw sample row — "
    f"{'MATCH' if original_pred == reloaded_pred else 'MISMATCH'}.\n"
)

with open("MODELING_REPORT.md", "w", encoding="utf-8") as f:
    f.write("\n".join(report_lines))
print("\nSaved full modeling report to MODELING_REPORT.md")
