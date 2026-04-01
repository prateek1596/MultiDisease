# 🚀 Quick Setup Guide — Using Your Existing Models & Datasets

This guide explains exactly how to connect your pre-trained `.pkl` models and CSV datasets to the system.

---

## Step 1 — Install Backend Dependencies

```bash
cd backend/
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

---

## Step 2 — Configure Environment

```bash
cp .env.example .env
# Edit .env if needed (DB URL, SECRET_KEY)
```

---

## Step 3 — Add Your Datasets (CSV files)

Place your CSV files inside `backend/ml/data/`:

```
backend/
└── ml/
    └── data/
        ├── heart.csv       ← Cleveland Heart Disease
        ├── diabetes.csv    ← PIMA Indians Diabetes
        └── kidney.csv      ← UCI CKD
```

### Expected Column Formats

**heart.csv** — target column must be named `target` or `condition`:
```
age, sex, cp, trestbps, chol, fbs, restecg, thalach, exang, oldpeak, slope, ca, thal, target
```
The target can also be `num` (UCI format — values 0-4, auto-converted to binary).

**diabetes.csv** — target column must be `Outcome`:
```
Pregnancies, Glucose, BloodPressure, SkinThickness, Insulin, BMI, DiabetesPedigreeFunction, Age, Outcome
```

**kidney.csv** — target column must be `classification` or `target`:
```
age, blood_pressure, specific_gravity, albumin, sugar, ... , classification
```
Text values like `ckd`/`notckd`, `yes`/`no`, `normal`/`abnormal` are auto-encoded.

> ⚠️ **No CSV files?** The system generates realistic synthetic data automatically — you can still train and run predictions.

---

## Step 4A — Use Your Existing .pkl Models (Fastest Path)

If you already have trained `.pkl` models from your previous project, you have two options:

### Option 1: Drop files in the models folder
```
backend/
└── ml/
    └── saved_models/
        ├── heart_model.pkl
        ├── diabetes_model.pkl
        └── kidney_model.pkl     ← (optional)
```
The system will **auto-detect and convert** these on the first prediction request.

### Option 2: Use the import script
```bash
cd backend/
python scripts/import_existing_models.py \
    --heart   path/to/heart_model.pkl \
    --diabetes path/to/diabetes_model.pkl \
    --kidney  path/to/kidney_model.pkl
```

This converts your existing models to the new `.joblib` format immediately.

---

## Step 4B — Train All 6 New Models (Recommended)

To train all 6 models (Logistic Regression, Random Forest, SVM, XGBoost, LightGBM, Stacking):

```bash
cd backend/
python scripts/train_all.py
```

**Output you'll see:**
```
==================================================
Training disease: HEART
  → logistic_regression
    CV AUC: 0.8821 ± 0.0312
    Saved heart_logistic_regression.joblib
  → random_forest
    CV AUC: 0.9145 ± 0.0218
    Saved heart_random_forest.joblib
  ...
  ★ Best: random_forest  AUC=0.9145

==================================================
Training disease: DIABETES
  ...

TRAINING COMPLETE
Time elapsed: 187.3s

Best Models Summary:
  heart      best=random_forest         AUC=0.9145  ACC=0.8689
  diabetes   best=xgboost               AUC=0.8923  ACC=0.8182
  kidney     best=lightgbm              AUC=0.9876  ACC=0.9750
```

### Train specific diseases/models only:
```bash
# Only retrain XGBoost and LightGBM for heart:
python scripts/train_all.py --diseases heart --models xgboost lightgbm

# Skip if .joblib already exists:
python scripts/train_all.py --skip-existing
```

---

## Step 5 — Start the API Server

```bash
cd backend/
uvicorn app.main:app --reload --port 8000
```

Visit **http://localhost:8000/api/docs** for the interactive API documentation.

---

## Step 6 — Start the Frontend

```bash
cd frontend/
npm install
npm run dev
# → http://localhost:5173
```

**Default admin login:** `admin` / `admin123`

---

## Step 7 — Verify Everything Works

1. Log in → Dashboard should show best model AUC scores
2. Go to **Predict** → select Heart Disease → fill in values → Run Prediction
   - If you see "model not found" → run `scripts/train_all.py` or `scripts/import_existing_models.py`
3. Go to **Model Performance** → should show comparison table and charts
4. Go to **Fairness Analysis** → select disease → Run Fairness Analysis
5. Go to **Minimal Features** → select disease → Find Minimal Feature Set

---

## File Layout After Setup

```
backend/
└── ml/
    ├── data/
    │   ├── heart.csv
    │   ├── diabetes.csv
    │   └── kidney.csv
    └── saved_models/
        ├── heart_logistic_regression.joblib
        ├── heart_random_forest.joblib
        ├── heart_svm.joblib
        ├── heart_xgboost.joblib
        ├── heart_lightgbm.joblib
        ├── heart_stacking.joblib
        ├── heart_best_model.txt          ← "random_forest"
        ├── heart_metrics.json            ← all metric scores
        ├── heart_features.json           ← feature name list
        ├── diabetes_*.joblib
        └── kidney_*.joblib
reports/
├── confusion_matrices/
│   ├── heart_random_forest_cm.png
│   └── ...
├── feature_importance/
├── fairness/
├── feature_reduction/
└── protocols/
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `FileNotFoundError: No trained model` | Run `scripts/train_all.py` or `scripts/import_existing_models.py` |
| `SMOTE error: k_neighbors` | Dataset too small; system auto-lowers k or skips SMOTE |
| `401 Unauthorized` | Login with `admin`/`admin123` first |
| `404 on /api/train` | Must be logged in as admin |
| Fairness 422 error | `sensitive_attr` length must match test set size (shown in error) |
| Database connection error | Start PostgreSQL or use Docker Compose |

---

## Docker (Easiest)

```bash
# From project root:
docker compose up --build

# Frontend: http://localhost:5173
# Backend:  http://localhost:8000/api/docs
```

Place your CSV files in `backend/ml/data/` before running Docker, or they'll be generated synthetically.
