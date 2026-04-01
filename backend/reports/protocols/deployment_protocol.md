# Clinical Deployment Protocol: Minimal Feature Disease Prediction

## Model Performance

- **Accuracy**: 85.00%
- **AUC-ROC**: 91.85%
- **F1-Score**: 82.35%
- **Feature Reduction**: 30.8% fewer tests

## Required Diagnostic Tests (9)

1. **thalach** (importance: 0.1546)
2. **cp** (importance: 0.1245)
3. **ca** (importance: 0.1223)
4. **oldpeak** (importance: 0.1140)
5. **thal** (importance: 0.0954)
6. **age** (importance: 0.0866)
7. **chol** (importance: 0.0836)
8. **trestbps** (importance: 0.0738)
9. **exang** (importance: 0.0481)

## Implementation Notes
- Collect only the listed measurements before running the model.
- High Risk (>75%): immediate referral
- Moderate Risk (40–75%): follow-up in 3 months
- Low Risk (<40%): annual screening

*Approved for use only under clinical supervision.*