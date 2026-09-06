import pandas as pd


US_AIRAN_COLUMNS = [
    "id", "date", "name", "country", "status", "type", "theater",
    "lat", "lng", "description", "source_outlet", "source_url", "source",
]


def _empty_if_missing(value):
    if pd.isna(value):
        return ""
    return str(value).strip()


def _optional_float(value):
    if pd.isna(value) or str(value).strip() == "":
        return None
    return float(value)


def _build_doc_text(row):
    date = _empty_if_missing(row.get("date"))
    name = _empty_if_missing(row.get("name"))
    country = _empty_if_missing(row.get("country"))
    theater = _empty_if_missing(row.get("theater"))
    status = _empty_if_missing(row.get("status"))
    event_type = _empty_if_missing(row.get("type"))
    description = _empty_if_missing(row.get("description"))

    text = f"On {date} in {country}"

    if theater:
        text += f" ({theater} theater)"

    text += f", a {event_type} event"

    if name:
        text += f' named "{name}"'

    if status:
        text += f" was reported with status {status}"
    else:
        text += " was reported"

    text += "."

    if description:
        text += f" Description: {description}"

    return text


def iter_usairan_batches(csv_path, batch_size=500):
    """
    Generatore pandas-only: legge il CSV USA-Iran a chunk e produce batch
    compatibili con la pipeline di embedding + inserimento in Chroma.
    """
    for chunk in pd.read_csv(csv_path, chunksize=batch_size):
        missing_columns = set(US_AIRAN_COLUMNS) - set(chunk.columns)
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise ValueError(f"Colonne mancanti nel CSV USA-Iran: {missing}")

        batch = []
        for row in chunk.to_dict(orient="records"):
            original_id = _empty_if_missing(row.get("id"))
            if not original_id:
                raise ValueError("Trovato evento USA-Iran senza id.")

            metadata = {
                "event_id": f"usairan_{original_id}",
                "dataset": "usa_iran_conflict",
                "original_id": original_id,
                "event_date": _empty_if_missing(row.get("date")),
                "name": _empty_if_missing(row.get("name")),
                "country": _empty_if_missing(row.get("country")),
                "status": _empty_if_missing(row.get("status")),
                "event_type": _empty_if_missing(row.get("type")),
                "theater": _empty_if_missing(row.get("theater")),
                "latitude": _optional_float(row.get("lat")),
                "longitude": _optional_float(row.get("lng")),
                "source_outlet": _empty_if_missing(row.get("source_outlet")),
                "source_url": _empty_if_missing(row.get("source_url")),
                "source": _empty_if_missing(row.get("source")),
            }

            batch.append(
                {
                    "text": _build_doc_text(row),
                    "metadata": metadata,
                }
            )

        if batch:
            yield batch
