# 🫀 MedPredict — Multi-Disease Prediction System

A production-grade, full-stack AI/ML system for predicting Heart Disease, Diabetes, and Chronic Kidney Disease using 6 machine learning models, with SHAP explainability, model comparison, PDF reporting, and role-based access control.

---

## 📐 Architecture Overview

```
multi-disease-prediction/
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── main.py             # App entry point & lifespan
│   │   ├── core/
│   │   │   ├── config.py       # Pydantic settings (.env)
│   │   │   ├── database.py     # SQLAlchemy async engine
│   │   │   └── security.py     # JWT auth, bcrypt
│   │   ├── routes/
│   │   │   ├── auth.py         # POST /auth/register, /login, GET /me
│   │   │   ├── predict.py      # POST /predict/{disease}
│   │   │   ├── models.py       # GET /models/performance
│   │   │   ├── report.py       # GET /report/download
│   │   │   └── train.py        # POST /train (admin)
│   │   ├── services/
│   │   │   ├── prediction_service.py
│   │   │   └── report_service.py
│   │   ├── models/
│   │   │   └── db_models.py    # SQLAlchemy ORM (users, predictions, model_metrics)
│   │   ├── schemas/
│   │   │   └── schemas.py      # Pydantic request/response models
│   │   └── ml/
│   │       ├── data_loader.py  # Dataset loaders (Heart, Diabetes, Kidney)
│   │       ├── pipelines/
│   │       │   ├── preprocessor.py      # sklearn Pipeline builders
│   │       │   └── model_registry.py    # All 6 model definitions
│   │       ├── training/
│   │       │   └── trainer.py           # SMOTE + CV + training orchestrator
│   │       ├── evaluation/
│   │       │   └── evaluator.py         # Metrics, confusion matrices, ROC
│   │       └── explainability/
│   │           └── shap_explainer.py    # SHAP values + feature importance plots
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                   # React + Vite + TailwindCSS
│   ├── src/
│   │   ├── App.jsx             # Router setup
│   │   ├── api/client.js       # Axios API client
│   │   ├── store/authStore.js  # Zustand auth state
│   │   ├── utils/diseaseConfig.js  # Form field definitions
│   │   ├── pages/
│   │   │   ├── DashboardPage.jsx
│   │   │   ├── PredictPage.jsx
│   │   │   ├── PerformancePage.jsx
│   │   │   ├── HistoryPage.jsx
│   │   │   └── TrainPage.jsx
│   │   └── components/
│   │       ├── Layout/Layout.jsx
│   │       └── Prediction/PredictionResult.jsx
│   └── Dockerfile
├── database/
│   └── schema.sql              # PostgreSQL DDL + seed admin user
└── docker-compose.yml
```

---

## 🧠 Machine Learning Models

| Model                | Type              | Key Strength                        |
|----------------------|-------------------|-------------------------------------|
| Logistic Regression  | Linear            | Interpretable, fast baseline        |
| Random Forest        | Ensemble (Bagging)| Robust, handles non-linearity       |
| SVM (RBF kernel)     | Kernel method     | Strong on small/medium datasets     |
| XGBoost              | Gradient Boosting | High accuracy, built-in regularization |
| LightGBM             | Gradient Boosting | Fastest training, memory efficient  |
| Stacking Ensemble    | Meta-learning     | Combines LR + RF + XGB via meta-LR  |

**Pipeline for each model:**
1. Median imputation (missing values)
2. StandardScaler (numeric features)
3. SMOTE (class imbalance, training set only)
4. 5-fold Stratified Cross-Validation
5. Train on full training set
6. Evaluate on held-out test set

---

## 🚀 Quick Start — Local Development

### Prerequisites
- Python 3.11+
- Node.js 20+
- PostgreSQL 15+ (or use Docker)

---

### Option A: Docker Compose (Recommended)

```bash
# 1. Clone / unzip the project
cd multi-disease-prediction

# 2. Create .env (optional overrides)
cp backend/.env.example backend/.env

# 3. Start all services
docker compose up --build

# Services:
#   Frontend  → http://localhost:5173
#   Backend   → http://localhost:8000
#   API Docs  → http://localhost:8000/api/docs
#   DB        → localhost:5432
```

---

### Option B: Manual Setup

#### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy env
cp .env.example .env
# Edit .env — set DATABASE_URL to your PostgreSQL

# Apply DB schema
psql -U mdps_user -d mdps_db -f ../database/schema.sql

# Run development server
uvicorn app.main:app --reload --port 8000
```

#### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Set API URL
echo "VITE_API_URL=http://localhost:8000/api" > .env

# Start dev server
npm run dev
# → http://localhost:5173
```

---

## 📊 Datasets

Place CSV files in `backend/ml/data/` before training.

| Disease | File | Source |
|---------|------|--------|
| Heart Disease | `heart.csv` | [UCI Heart Disease](https://archive.ics.uci.edu/ml/datasets/heart+disease) |
| Diabetes | `diabetes.csv` | [PIMA Indians (Kaggle)](https://www.kaggle.com/datasets/uciml/pima-indians-diabetes-database) |
| Kidney Disease | `kidney.csv` | [UCI CKD](https://archive.ics.uci.edu/ml/datasets/Chronic_Kidney_Disease) |

> **No files?** The system auto-generates realistic synthetic data for development/demo.

---

## 🔐 Authentication

**Default admin credentials:**
- Username: `admin`
- Password: `admin123`

Roles:
- `user` — can predict, view history, view performance
- `admin` — additionally can trigger training (`POST /api/train`)

---

## 📡 API Reference

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/auth/register` | — | Create account |
| POST | `/api/auth/login` | — | Get JWT token |
| GET | `/api/auth/me` | User | Current user info |
| POST | `/api/predict/{disease}` | User | Run prediction + SHAP |
| GET | `/api/predictions/history` | User | Prediction history |
| GET | `/api/models/performance` | User | All model metrics |
| GET | `/api/models/performance/{disease}` | User | Per-disease metrics |
| GET | `/api/models/comparison` | User | Flat comparison table |
| GET | `/api/report/download` | User | Download PDF report |
| POST | `/api/train` | Admin | Trigger training |
| GET | `/api/train/status` | Admin | Training progress |

Interactive docs at: `http://localhost:8000/api/docs`

---

## 🔁 Training Workflow

1. Login as admin → Navigate to **Train Models**
2. Select diseases and models
3. Click **Start Training** → runs in background
4. Monitor status with auto-refresh
5. Once complete → navigate to **Model Performance** to see results
6. Download PDF report from Performance page

---

## 📈 Evaluation Output

For each disease × model combination:
- ✅ Accuracy, Precision, Recall, F1-Score, ROC-AUC
- ✅ 5-fold CV mean ± std AUC
- ✅ Confusion matrix image (`reports/confusion_matrices/`)
- ✅ Classification report (JSON)
- ✅ Best model auto-selected by ROC-AUC
- ✅ PDF report with all matrices and comparison table

---

## 🧾 SHAP Explainability

Every prediction response includes:
```json
{
  "explanation": {
    "feature_names": ["age", "glucose", ...],
    "shap_values": [0.12, -0.08, ...],
    "base_value": 0.35,
    "top_features": [
      {
        "feature": "glucose",
        "shap_value": 0.22,
        "abs_impact": 0.22,
        "direction": "increases risk"
      }
    ]
  }
}
```

The frontend renders an interactive horizontal bar chart showing which features pushed the prediction positive (red) or negative (green).

---

## 🐋 Docker Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | `change-me` | JWT signing key |
| `APP_ENV` | `production` | Environment |
| `DATABASE_URL` | `postgresql+asyncpg://...` | Async DB URL |
| `ALLOWED_ORIGINS` | `http://localhost:5173` | CORS origins |

---

## 🗂️ Generated Output Files

```
backend/
├── ml/saved_models/
│   ├── heart_random_forest.joblib
│   ├── heart_xgboost.joblib
│   ├── heart_metrics.json          ← cached metrics
│   ├── diabetes_*.joblib
│   └── kidney_*.joblib
└── reports/
    ├── confusion_matrices/
    │   ├── heart_random_forest_cm.png
    │   └── ...
    ├── feature_importance/
    │   └── ...
    └── mdps_report_20240325_143000.pdf
```

---

## 🧪 Running Tests

```bash
cd backend
pytest tests/ -v
```

---

## 🛠️ Tech Stack

**Backend:** FastAPI · SQLAlchemy (async) · Alembic · Pydantic v2 · python-jose · passlib · Loguru

**ML:** scikit-learn · XGBoost · LightGBM · imbalanced-learn · SHAP · pandas · numpy · joblib

**Reporting:** ReportLab · matplotlib · seaborn

**Frontend:** React 18 · Vite · TailwindCSS · Recharts · Zustand · TanStack Query · react-hook-form

**Database:** PostgreSQL 15

**DevOps:** Docker · Docker Compose · Nginx

---

## 📝 License

MIT — free for academic, research, and commercial use.
