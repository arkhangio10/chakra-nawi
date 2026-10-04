# Experimento semi-real (sustituto, NO broca)

Generado 2026-10-04 00:58 por `ml/semireal.py`.

Prueba `semireal_v1`: 70 % de las brocas son recortes de *Xylosandrus compactus* (especie no vista en entrenamiento) y los escarabajos grandes son *Phloeosinus dentatus* (no vistos). Prueba `sint_dificiles_v1`: el test anterior, 100 % dibujado.

| Modelo | Prueba | Var. | MiB | MAE a 0,60 | Sesgo | FP en vacíos | P | R | Score val | MAE con score val |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| broca-y8n-v0-sint | semireal_v1 | fp32 | 11.7 | 26.72 | 24.78 | 26.67 | 0.814 | 0.918 | 0.65 | 22.62 |
| broca-y8n-v0-sint | semireal_v1 | int8 | 3.2 | 26.28 | 24.08 | 25.17 | 0.814 | 0.915 | 0.6 | 26.28 |
| broca-y8n-v0-sint-dificiles | semireal_v1 | fp32 | 11.7 | 32.45 | -32.08 | 0.17 | 0.949 | 0.792 | 0.25 | 14.43 |
| broca-y8n-v0-sint-dificiles | semireal_v1 | int8 | 3.2 | 44.0 | -43.93 | 0.17 | 0.959 | 0.742 | 0.25 | 10.13 |
| broca-y8n-v0-semireal | semireal_v1 | fp32 | 11.7 | 10.98 | -10.65 | 0.17 | 0.977 | 0.924 | 0.45 | 5.92 |
| broca-y8n-v0-semireal | semireal_v1 | int8 | 3.2 | 11.2 | -10.83 | 0.17 | 0.977 | 0.922 | 0.45 | 6.0 |
| broca-y8n-v0-semireal | sint_dificiles_v1 | fp32 | 11.7 | 13.03 | -12.53 | 0.17 | 0.977 | 0.914 | 0.4 | 5.47 |
| broca-y8n-v0-semireal | sint_dificiles_v1 | int8 | 3.2 | 13.55 | -13.15 | 0.17 | 0.977 | 0.91 | 0.4 | 5.42 |
| broca-y8n-v0-sint-dificiles | sint_dificiles_v1 | fp32 | 11.7 | 9.13 | -8.53 | 0.33 | 0.975 | 0.932 | 0.45 | 5.13 |
| broca-y8n-v0-sint-dificiles | sint_dificiles_v1 | int8 | 3.2 | 12.27 | -12.03 | 0.33 | 0.978 | 0.917 | 0.4 | 4.77 |

Fuente de los recortes: Marais et al. (2024) PLOS ONE, doi:10.1371/journal.pone.0310716 (Hugging Face `ChristopherMarais/Andrew_Alpha_training_data`, CC-BY-SA-4.0).
El modelo NO se copió a `apps/campo`; el contrato (0,60) no cambió.
