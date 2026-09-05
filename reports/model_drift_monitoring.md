# Reproducible Model Monitoring Framework

Recorded baselines use generated project data and explicit review thresholds.

- Reference period: signup date <= 2024-08-08
- Current period: signup date > 2024-08-08
- Feature signals: 8; watch/material: 1
- Prediction signals: 6; watch/material: 1
- Segment signals: 5; watch: 0

PSI below 0.10 is stable, 0.10–0.25 is watch, and >=0.25 is material drift. KS statistics supplement PSI for continuous features; p-values reflect detectability and are not severity measures. Shift alone does not prove performance degradation.
