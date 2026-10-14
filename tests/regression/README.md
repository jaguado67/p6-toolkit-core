# Regresión con archivos reales

1. Copie un XER real (o el Excel `data` de un layout) en `tests/regression/data/`. Esa carpeta está en `.gitignore`: los cronogramas de clientes nunca entran al repositorio.
2. Registre los valores esperados:
   `py tests/regression/record_golden.py tests/regression/data/UP05.xer --data-date 2026-10-01T08:00`
3. Abra el `.golden.json` y compare cada número con P6 (actividades, relaciones por tipo, extremos abiertos, restricciones…). Si todo cuadra, cambie `validated_against_p6` a `true`.
4. Desde entonces `py -m pytest -q` falla si una modificación del código cambia cualquiera de esos números.
