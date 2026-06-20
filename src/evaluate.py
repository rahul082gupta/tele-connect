import joblib

import matplotlib.pyplot as plt

from sklearn.metrics import (
    confusion_matrix,
    ConfusionMatrixDisplay,
    roc_curve,
    auc,
    precision_recall_curve
)

model = joblib.load(
    "../models/churn_model.joblib"
)

probs = model.predict_proba(
    X_test
)[:,1]

preds = model.predict(
    X_test
)

cm = confusion_matrix(
    y_test,
    preds
)

disp = ConfusionMatrixDisplay(
    confusion_matrix=cm
)

disp.plot()

plt.savefig(
    "../outputs/confusion_matrix.png"
)

fpr,tpr,_ = roc_curve(
    y_test,
    probs
)

plt.figure()

plt.plot(
    fpr,
    tpr
)

plt.title(
    "ROC Curve"
)

plt.savefig(
    "../outputs/roc_curve.png"
)