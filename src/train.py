import pandas as pd
import joblib
import json

from pathlib import Path

from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer

from sklearn.impute import SimpleImputer

from sklearn.preprocessing import (
    OneHotEncoder,
    StandardScaler
)

from sklearn.linear_model import (
    LogisticRegression
)

from xgboost import XGBClassifier

from sklearn.metrics import (
    classification_report,
    roc_auc_score,
    confusion_matrix,
    ConfusionMatrixDisplay,
    RocCurveDisplay
)

import matplotlib.pyplot as plt

from data_quality import DataQualityProcessor
from feature_engineering import create_features


# ==================================================
# PATHS
# ==================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_PATH = PROJECT_ROOT / "data" / "test_datafile.csv"

MODEL_DIR = PROJECT_ROOT / "models"
OUTPUT_DIR = PROJECT_ROOT / "outputs"

MODEL_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# ==================================================
# LOAD DATA
# ==================================================

df = pd.read_csv(DATA_PATH)

print(f"Loaded dataset: {df.shape}")

# ==================================================
# DATA QUALITY
# ==================================================

processor = DataQualityProcessor(df)

df = processor.clean()

issues = processor.issue_report()
stats = processor.statistics_report()

issues.to_csv(
    OUTPUT_DIR / "data_quality_issues.csv",
    index=False
)

stats.to_csv(
    OUTPUT_DIR / "before_after_statistics.csv"
)

df.to_csv(
    PROJECT_ROOT / "data" / "cleaned_test_datafile.csv",
    index=False
)

print("Data quality reports generated")

# ==================================================
# FEATURE ENGINEERING
# ==================================================

df = create_features(df)

# ==================================================
# DATE FEATURE
# ==================================================

TARGET = "churned"

df.drop(
    columns=["customer_id"],
    errors="ignore",
    inplace=True
)

df["last_interaction_date"] = pd.to_datetime(
    df["last_interaction_date"],
    errors="coerce"
)

latest_date = df["last_interaction_date"].max()

df["days_since_last_interaction"] = (
    latest_date - df["last_interaction_date"]
).dt.days

df.drop(
    columns=["last_interaction_date"],
    inplace=True
)

# ==================================================
# SPLIT
# ==================================================

X = df.drop(TARGET, axis=1)

y = df[TARGET]

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    stratify=y,
    random_state=42
)

# ==================================================
# PREPROCESSOR
# ==================================================

numeric_features = X_train.select_dtypes(
    include=["int64", "float64"]
).columns.tolist()

categorical_features = X_train.select_dtypes(
    include=["object"]
).columns.tolist()

preprocessor = ColumnTransformer([

    (
        "num",

        Pipeline([

            (
                "imputer",
                SimpleImputer(
                    strategy="median"
                )
            ),

            (
                "scaler",
                StandardScaler()
            )

        ]),

        numeric_features
    ),

    (
        "cat",

        Pipeline([

            (
                "imputer",
                SimpleImputer(
                    strategy="most_frequent"
                )
            ),

            (
                "encoder",
                OneHotEncoder(
                    handle_unknown="ignore"
                )
            )

        ]),

        categorical_features
    )

])

# ==================================================
# MODELS
# ==================================================

models = {

    "LogisticRegression":

        LogisticRegression(
            class_weight="balanced",
            max_iter=3000
        ),

    "XGBoost":

        XGBClassifier(
            n_estimators=300,
            max_depth=5,
            learning_rate=0.05,
            random_state=42,
            eval_metric="logloss"
        )
}

best_auc = 0
best_model = None
best_model_name = None

# ==================================================
# TRAIN
# ==================================================

for name, clf in models.items():

    print("\n" + "=" * 50)
    print(name)
    print("=" * 50)

    pipe = Pipeline([

        (
            "preprocessor",
            preprocessor
        ),

        (
            "model",
            clf
        )

    ])

    pipe.fit(
        X_train,
        y_train
    )

    probs = pipe.predict_proba(
        X_test
    )[:, 1]

    preds = pipe.predict(
        X_test
    )

    auc = roc_auc_score(
        y_test,
        probs
    )

    print(
        f"ROC-AUC: {auc:.4f}"
    )

    print(
        classification_report(
            y_test,
            preds
        )
    )

    if auc > best_auc:

        best_auc = auc
        best_model = pipe
        best_model_name = name

# ==================================================
# SAVE MODEL
# ==================================================

joblib.dump(
    best_model,
    MODEL_DIR / "churn_model.joblib"
)

# ==================================================
# SAVE METADATA
# ==================================================

metadata = {

    "best_model": best_model_name,

    "best_auc": float(best_auc),

    "required_columns":
        X_train.columns.tolist(),

    "engineered_features": [

        "charge_per_month_of_tenure",

        "support_ticket_rate",

        "usage_per_month",

        "customer_lifetime_value",

        "days_since_last_interaction"

    ]
}

with open(
    MODEL_DIR /
    "churn_model_metadata.json",
    "w"
) as fh:

    json.dump(
        metadata,
        fh,
        indent=4
    )

# ==================================================
# EVALUATION PLOTS
# ==================================================

preds = best_model.predict(X_test)

probs = best_model.predict_proba(
    X_test
)[:, 1]

cm = confusion_matrix(
    y_test,
    preds
)

disp = ConfusionMatrixDisplay(
    confusion_matrix=cm
)

disp.plot()

plt.title(
    "Confusion Matrix"
)

plt.savefig(
    OUTPUT_DIR /
    "confusion_matrix.png"
)

plt.close()

RocCurveDisplay.from_predictions(
    y_test,
    probs
)

plt.title(
    "ROC Curve"
)

plt.savefig(
    OUTPUT_DIR /
    "roc_curve.png"
)

plt.close()

print("\nBest Model:", best_model_name)

print(
    f"Best ROC-AUC: {best_auc:.4f}"
)

print(
    "\nModel saved successfully"
)