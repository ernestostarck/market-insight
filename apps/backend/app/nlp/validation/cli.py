"""CLI runner for End-to-End Validation on Real Mercado Público Data (Fase 6.28).

Run as:
    python -m app.nlp.validation.cli
"""

from __future__ import annotations

import argparse
import json
import sys
import time

from app.nlp.validation.validator import RealMarketPublicoValidator, ValidationSummary


def run_cli(args: argparse.Namespace) -> int:
    print("=" * 80)
    print("MERCADO INSIGHT — FASE 6.28: END-TO-END VALIDATION (MERCADO PÚBLICO)")
    print("=" * 80)
    print("Iniciando validación sobre 20 licitaciones reales de ChileCompra...")

    validator = RealMarketPublicoValidator()
    summary: ValidationSummary = validator.run_validation()

    print("\n" + "-" * 80)
    print("RESULTADOS POR LICITACIÓN")
    print("-" * 80)
    header = f"{'ID':<5} {'CÓDIGO':<15} {'ESPERADO':<14} {'PREDICCIÓN':<14} {'CAT':<4} {'REL':<4} {'CONF':<7} {'MS':<6}"
    print(header)
    print("-" * 80)

    for r in summary.results:
        cat_status = "OK" if r.is_category_correct else "X"
        rel_status = "OK" if r.is_relevance_correct else "X"
        conf_str = f"{r.confidence_assessment.confidence_score:.2f}"
        print(
            f"{r.tender_id:<5} {r.codigo_externo:<15} {r.expected_category:<14} "
            f"{r.predicted_category:<14} {cat_status:<4} {rel_status:<4} {conf_str:<7} {r.latency_ms:<6.1f}"
        )

    print("\n" + "-" * 80)
    print("MATRIZ DE CONFUSIÓN")
    print("-" * 80)
    classes = sorted(list(summary.metrics.confusion_matrix.keys()))
    header_cm = f"{'REAL \\ PRED':<15} " + " ".join(f"{c:>12}" for c in classes)
    print(header_cm)
    for c_true in classes:
        row_str = f"{c_true:<15} " + " ".join(
            f"{summary.metrics.confusion_matrix[c_true].get(c_pred, 0):>12}" for c_pred in classes
        )
        print(row_str)

    print("\n" + "-" * 80)
    print("MÉTRICAS GLOBALES DE RENDIMIENTO (FASE 6)")
    print("-" * 80)
    m = summary.metrics
    print(f"Total Licitaciones Validadas:  {m.total_tenders}")
    print(f"Exactitud Categórica:          {m.accuracy * 100:.1f}%")
    print(f"F1 Macro (Multiclase):          {m.f1_macro * 100:.1f}%")
    print(f"Precisión Macro:               {m.precision_macro * 100:.1f}%")
    print(f"Exhaustividad (Recall) Macro:  {m.recall_macro * 100:.1f}%")
    print(f"Exactitud de Relevancia:       {m.relevance_accuracy * 100:.1f}%")
    print(f"Latencia Media por Documento:  {m.mean_latency_ms:.1f} ms")
    print(f"Latencia P95:                  {m.p95_latency_ms:.1f} ms")
    print(f"Revisiones Humanas Requeridas: {m.human_reviews_triggered}")
    print(f"Data Drift (Divergencia KL):   {m.drift_report.kl_divergence:.4f} (drift_detected={m.drift_report.drift_detected})")

    print("\n" + "-" * 80)
    print("MÉTRICAS POR CATEGORÍA")
    print("-" * 80)
    print(f"{'CATEGORÍA':<15} {'PRECISIÓN':<12} {'RECALL':<12} {'F1-SCORE':<12} {'SOPORTE':<8}")
    for cat, metrics in m.per_class_metrics.items():
        print(
            f"{cat:<15} {metrics['precision']*100:>10.1f}% {metrics['recall']*100:>10.1f}% "
            f"{metrics['f1']*100:>10.1f}% {metrics['support']:>8}"
        )

    print("\n" + "=" * 80)
    print("ESTADO DE VALIDACIÓN: " + ("EXITOSO (F1 >= 0.85)" if m.f1_macro >= 0.85 else "FALLIDO"))
    print("=" * 80)

    if args.output:
        output_data = {
            "timestamp": summary.timestamp.isoformat(),
            "total_tenders": m.total_tenders,
            "accuracy": m.accuracy,
            "f1_macro": m.f1_macro,
            "precision_macro": m.precision_macro,
            "recall_macro": m.recall_macro,
            "relevance_accuracy": m.relevance_accuracy,
            "mean_latency_ms": m.mean_latency_ms,
            "p95_latency_ms": m.p95_latency_ms,
            "drift_kl": m.drift_report.kl_divergence,
            "per_class": m.per_class_metrics,
            "confusion_matrix": m.confusion_matrix,
        }
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2)
        print(f"Reporte JSON guardado en: {args.output}")

    return 0 if m.f1_macro >= 0.85 else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="End-to-End Validation on Real Mercado Público Data (Fase 6.28)")
    parser.add_argument("--output", "-o", type=str, help="Ruta de archivo JSON para exportar métricas", default=None)
    args = parser.parse_args()
    sys.exit(run_cli(args))


if __name__ == "__main__":
    main()
