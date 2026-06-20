import pandas as pd
import joblib
import numpy as np
from pathlib import Path

from src.data_quality import DataQualityProcessor
from src.feature_engineering import create_features

MODEL_PATH = (
    Path(__file__)
    .resolve()
    .parents[1]
    / "models"
    / "churn_model.joblib"
)

model = joblib.load(MODEL_PATH)
META_PATH = MODEL_PATH.with_name("churn_model_metadata.json")

metadata = {}
if META_PATH.exists():
    try:
        import json

        with open(META_PATH, "r") as fh:
            metadata = json.load(fh)
    except Exception:
        metadata = {}


def predict_churn(
    customer_data: dict
):

    df = pd.DataFrame(
        [customer_data]
    )

    # Apply the same cleaning and feature engineering used during training
    quality = DataQualityProcessor(df)
    df = quality.clean()

    df = create_features(df)

    # Ensure engineered features exist (fallback to NaN)
    engineered = metadata.get(
        "engineered_features",
        [
            "charge_per_month_of_tenure",
            "support_ticket_rate",
            "usage_per_month",
            "customer_lifetime_value",
        ],
    )

    for col in engineered:
        if col not in df.columns:
            df[col] = np.nan

    # If we have metadata about required raw columns, ensure they exist
    required = metadata.get("required_columns")
    if required:
        for col in required:
            if col not in df.columns:
                df[col] = np.nan

    if "last_interaction_date" in df.columns:

        latest = pd.Timestamp.today()

        df[
            "last_interaction_date"
        ] = pd.to_datetime(
            df[
                "last_interaction_date"
            ]
        )

        df[
            "days_since_last_interaction"
        ] = (
            latest -
            df[
                "last_interaction_date"
            ]
        ).dt.days

        df.drop(
            columns=[
                "last_interaction_date"
            ],
            inplace=True
        )

    # Remove identifier if present so pipeline column checks succeed
    if "customer_id" in df.columns:
        df = df.drop(columns=["customer_id"])

    probability = (
        model.predict_proba(df)
        [0][1]
    )

    # Try to compute SHAP top risk factors (best-effort, optional)
    top_risk = ["Requires SHAP integration"]
    try:
        import shap

        pipe = model

        def _pretty(name: str) -> str:
            try:
                if name.startswith("cat__"):
                    s = name.split("cat__", 1)[1]
                    if "_" in s:
                        base, val = s.split("_", 1)
                        return f"{base.replace('_', ' ')} = {val}"
                    return s.replace('_', ' ')
                if name.startswith("num__"):
                    return name.split("num__", 1)[1]
                return name.replace('_', ' ')
            except Exception:
                return str(name)
        preprocessor = None
        estimator = None
        if hasattr(pipe, "named_steps"):
            preprocessor = pipe.named_steps.get("preprocessor")
            estimator = pipe.named_steps.get("model") or pipe.named_steps.get("estimator")

        if preprocessor is not None and estimator is not None:
            # transform to numeric features first to avoid masker dtype issues
            X_proc = preprocessor.transform(df)

            # feature names from preprocessor if available
            try:
                feature_names = preprocessor.get_feature_names_out()
            except Exception:
                feature_names = [f"f_{i}" for i in range(X_proc.shape[1])]

            # build explainer on the estimator using processed numeric data
            try:
                expl = shap.Explainer(estimator, X_proc)
                shap_out = expl(X_proc)
            except Exception:
                # fallback to TreeExplainer for tree-based models
                try:
                    expl = shap.TreeExplainer(estimator)
                    shap_vals = expl.shap_values(X_proc)
                    if isinstance(shap_vals, list):
                        arr = np.array(shap_vals[1]) if len(shap_vals) > 1 else np.array(shap_vals[0])
                    else:
                        arr = np.array(shap_vals)
                    sample_shap = arr[0]
                    abs_imp = np.abs(sample_shap)
                    top_idx = abs_imp.argsort()[::-1][:3]
                    top_risk = [(_pretty(feature_names[i]) if i < len(feature_names) else f"f_{i}") for i in top_idx]
                    raise StopIteration
                except StopIteration:
                    pass
            else:
                vals = getattr(shap_out, "values", None)
                if vals is None:
                    vals = np.array(shap_out)
                if isinstance(vals, list):
                    arr = np.array(vals[1]) if len(vals) > 1 else np.array(vals[0])
                else:
                    arr = np.array(vals)
                sample_shap = arr[0]
                abs_imp = np.abs(sample_shap)
                top_idx = abs_imp.argsort()[::-1][:3]
                top_risk = [(_pretty(feature_names[i]) if i < len(feature_names) else f"f_{i}") for i in top_idx]
        else:
            # fallback: try explainer on the pipeline using raw df
            expl = shap.Explainer(model.predict_proba, df)
            shap_out = expl(df)
            vals = getattr(shap_out, "values", None)
            if vals is None:
                vals = np.array(shap_out)
            if isinstance(vals, list):
                arr = np.array(vals[1]) if len(vals) > 1 else np.array(vals[0])
            else:
                arr = np.array(vals)
            sample_shap = arr[0]
            abs_imp = np.abs(sample_shap)
            feature_names = list(df.columns)
            top_idx = abs_imp.argsort()[::-1][:3]
            top_risk = [(_pretty(feature_names[i]) if i < len(feature_names) else f"f_{i}") for i in top_idx]
    except Exception as e:
        # swallow errors silently in production; keep fallback message
        top_risk = ["Requires SHAP integration"]

    if probability > 0.70:
        risk = "high"

    elif probability > 0.40:
        risk = "medium"

    else:
        risk = "low"

    return {

        "churn_probability":
            round(
                float(probability),
                4
            ),

        "risk_tier":
            risk,

        "top_risk_factors": top_risk

    }