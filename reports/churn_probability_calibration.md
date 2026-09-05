# Churn Probability Calibration

Raw Brier score: 0.0270.
Calibration retained: **raw**.

Sigmoid and isotonic calibration were evaluated with five-fold calibration on the training partition and compared on the untouched held-out partition. A method is retained only for Brier improvement above 0.005 without ROC-AUC degradation below -0.01.

No current production artifact is replaced automatically. Calibration affects probability reliability, not whether observational features cause churn.
