"""
Módulo de Validação e Qualidade de Dados (Data Quality).
Analisa o ficheiro de Staging, valida schemas, nulos e duplicados,
e gera um relatório de auditoria para avaliação técnica.
"""

import json
from pathlib import Path
from datetime import datetime
import pandas as pd

from src.utils.config import load_config
from src.utils.logger import get_logger

logger = get_logger("transform_quality")


def run_data_quality_checks():
    logger.info("=" * 60)
    logger.info("INÍCIO DA VALIDAÇÃO DE QUALIDADE DE DADOS")
    logger.info("=" * 60)

    config = load_config()
    staging_dir = Path(config["paths"].get("staging_data", "data/staging"))
    metrics_dir = Path("data/metrics_quality")
    metrics_dir.mkdir(parents=True, exist_ok=True)

    # 1. Localizar o ficheiro mais recente de Staging
    files = sorted(list(staging_dir.glob("fact_playlists_tracks_staging_*.csv")), key=lambda x: x.stat().st_mtime)
    if not files:
        logger.error("Nenhum ficheiro de staging encontrado para validação.")
        return

    latest_staging = files[-1]
    logger.info(f"A auditar a qualidade de: {latest_staging.name}")
    df = pd.read_csv(latest_staging)

    total_rows = len(df)
    report = {
        "check_timestamp": datetime.now().isoformat(),
        "source_file": latest_staging.name,
        "total_records_analyzed": total_rows,
        "validations": {}
    }

    # Validação 1: Valores Nulos (Missing Values)
    null_counts = df.isnull().sum().to_dict()
    report["validations"]["missing_values"] = {
        "status": "PASS" if sum(null_counts.values()) == 0 else "WARNING",
        "details": null_counts
    }

    # Validação 2: Duplicados
    duplicate_count = int(df.duplicated().sum())
    report["validations"]["duplicate_rows"] = {
        "status": "PASS" if duplicate_count == 0 else "FAIL",
        "count": duplicate_count
    }

    # Validação 3: Consistência de IDs e Chaves (Regra de Matching)
    # Quantas linhas não conseguiram dar match com a MusicBrainz (ficaram com mbid nulo)?
    unmatched_artists = df[df["mbid"].isnull()]["artist_name"].nunique()
    report["validations"]["musicbrainz_match_quality"] = {
        "status": "PASS" if unmatched_artists == 0 else "INFO",
        "unmatched_unique_artists_count": unmatched_artists
    }

    # Valisdação 4: Limites plausíveis (Durações absurdas > 30 minutos por faixa)
    abnormal_tracks = int((df["track_duration_min"] > 30.0).sum())
    report["validations"]["plausible_duration_check"] = {
        "status": "PASS" if abnormal_tracks == 0 else "WARNING",
        "abnormal_tracks_detected": abnormal_tracks
    }

    # 2. Escrever Relatório Curto em formato JSON e Markdown (para documentação)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Salvar JSON estruturado
    json_path = metrics_dir / f"quality_report_{timestamp}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # Salvar Markdown legível para o teu relatório final académico
    md_path = metrics_dir / f"quality_report_{timestamp}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# Relatório de Qualidade de Dados - ETL\n\n")
        f.write(f"- **Data da Auditoria:** {report['check_timestamp']}\n")
        f.write(f"- **Ficheiro Analisado:** {report['source_file']}\n")
        f.write(f"- **Total de Linhas:** {report['total_records_analyzed']}\n\n")
        f.write(f"## Sumário Executivo das Validações\n")
        f.write(f"- **Valores Nulos:** {report['validations']['missing_values']['status']}\n")
        f.write(
            f"- **Linhas Duplicadas:** {report['validations']['duplicate_rows']['status']} ({duplicate_count} encontradas)\n")
        f.write(f"- **Artistas sem Match MBID:** {unmatched_artists} artistas\n")
        f.write(f"- **Músicas > 30 min:** {abnormal_tracks} faixas detetadas\n")

    logger.success(f"Validação de qualidade terminada. Relatórios gerados em: {metrics_dir}")


if __name__ == "__main__":
    run_data_quality_checks()