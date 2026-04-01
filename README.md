# 🫀 MedPredict — AI-Powered Multi-Disease Prediction System

A **production-grade full-stack AI/ML platform** for early prediction of **Heart Disease, Diabetes, and Chronic Kidney Disease**, built with explainable machine learning, interactive dashboards, and clinical-style reporting.

> ⚡ Designed for **research, healthcare analytics, and real-world deployment**

---

## 🌟 Key Highlights

* 🧠 **6 ML Models + Stacking Ensemble**
* 📊 **Explainable AI (SHAP) for every prediction**
* 📈 **Cross-validated evaluation (ROC-AUC, F1, etc.)**
* 📄 **Auto-generated PDF medical reports**
* 🔐 **JWT Authentication + Role-based access**
* 🐳 **Dockerized full-stack deployment**
* ⚡ **FastAPI + React production architecture**

---

## 🧩 System Architecture

* **Frontend:** React + Vite + Tailwind
* **Backend:** FastAPI (async)
* **ML Engine:** scikit-learn, XGBoost, LightGBM
* **Database:** PostgreSQL
* **Deployment:** Docker + Nginx

📁 Clean modular structure:

```
backend/   → ML + API
frontend/  → UI Dashboard
database/  → Schema & setup
```

---

## 🧠 Machine Learning Pipeline

Each model follows a **research-grade pipeline**:

1. Data preprocessing (missing value handling)
2. Feature scaling (StandardScaler)
3. Class balancing using SMOTE
4. Stratified 5-fold Cross Validation
5. Model training + evaluation
6. Explainability using SHAP

### Models Used

* Logistic Regression
* Random Forest
* Support Vector Machine (RBF)
* XGBoost
* LightGBM
* Stacking Ensemble (Meta-learning)

---

## 📊 Explainable AI (SHAP)

Every prediction includes:

* Feature-level contribution
* Risk direction (increase/decrease)
* Top influencing factors

👉 Makes the system **clinically interpretable**, not a black box.

---

## 🚀 Quick Start

### 🐳 Docker (Recommended)

```bash
docker compose up --build
```

* Frontend → http://localhost:5173
* Backend → http://localhost:8000
* Docs → http://localhost:8000/api/docs

---

### ⚙️ Manual Setup

#### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

#### Frontend

```bash
cd frontend
npm install
npm run dev
```

---

## 📡 API Features

* User Authentication (JWT)
* Disease Prediction (with explanation)
* Model Performance Dashboard
* Prediction History Tracking
* PDF Report Generation
* Admin Training Control

---

## 📈 Evaluation Metrics

* Accuracy
* Precision / Recall
* F1 Score
* ROC-AUC
* Cross-validation mean ± std
* Confusion Matrix

✔ Best model automatically selected per disease

---

## 📁 Dataset Sources

* UCI Heart Disease Dataset
* PIMA Diabetes Dataset
* UCI Chronic Kidney Disease Dataset

*(Synthetic data auto-generated if datasets are missing)*

---

## 🔐 Roles

| Role  | Access                        |
| ----- | ----------------------------- |
| User  | Predictions, history, reports |
| Admin | Model training + monitoring   |

---

## 📦 Output Artifacts

* Trained models (`.joblib`)
* SHAP feature importance plots
* Confusion matrices
* PDF reports

---

## 🛠️ Tech Stack

**Backend:** FastAPI, SQLAlchemy, Pydantic
**ML:** scikit-learn, XGBoost, LightGBM, SHAP
**Frontend:** React, TailwindCSS, Zustand
**Database:** PostgreSQL
**DevOps:** Docker

---

## 🎯 Project Goals

* Early disease risk prediction
* Explainable AI in healthcare
* Research-grade ML pipeline
* Real-world deployable system

---

## 📌 Future Improvements

* 📱 Mobile app integration
* 🌐 Federated learning (multi-hospital data)
* 🤖 Real-time wearable data integration
* 📊 Advanced clinical dashboards

