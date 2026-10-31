"""Journal des anomalies : aucune ligne n'est modifiée ou écartée sans laisser de trace."""

from dataclasses import dataclass, field

import pandas as pd

LOG_COLUMNS = ["table", "source", "column", "row_id", "value", "reason"]


@dataclass
class QualityLog:
    """Collecte les anomalies détectées pendant le nettoyage."""

    _frames: list = field(default_factory=list)

    def record(self, table, source, column, row_ids, raw_values, reasons):
        """Enregistre les lignes pour lesquelles `reasons` contient un motif."""
        mask = reasons.notna()
        if not mask.any():
            return
        self._frames.append(
            pd.DataFrame(
                {
                    "table": table,
                    "source": source,
                    "column": column,
                    "row_id": row_ids[mask].astype(str).to_numpy(),
                    "value": raw_values[mask].astype(str).to_numpy(),
                    "reason": reasons[mask].astype(str).to_numpy(),
                }
            )
        )

    def to_frame(self):
        """Retourne toutes les anomalies dans un seul tableau."""
        if not self._frames:
            return pd.DataFrame(columns=LOG_COLUMNS)
        return pd.concat(self._frames, ignore_index=True)

    def summary(self):
        """Compte les anomalies par table, source, colonne et motif."""
        frame = self.to_frame()
        if frame.empty:
            return pd.DataFrame(columns=["table", "source", "column", "reason", "rows"])
        return (
            frame.groupby(["table", "source", "column", "reason"])
            .size()
            .reset_index(name="rows")
            .sort_values("rows", ascending=False, ignore_index=True)
        )
