import shap
import joblib
import matplotlib.pyplot as plt

model = joblib.load(
    "../models/churn_model.joblib"
)

xgb_model = model.named_steps[
    "model"
]

X_processed = model.named_steps[
    "prep"
].transform(
    X_train
)

explainer = shap.TreeExplainer(
    xgb_model
)

shap_values = explainer(
    X_processed
)

shap.summary_plot(
    shap_values,
    X_processed,
    show=False
)

plt.savefig(
    "../outputs/feature_importance.png"
)

joblib.dump(
    explainer,
    "../models/shap_explainer.joblib"
)