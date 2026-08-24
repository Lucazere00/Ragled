import pandas as pd
import numpy as np

def build_documents(csv_path):
    df = pd.read_csv(csv_path, parse_dates=['event_date'])

    # riempi i NaN prima di concatenare stringhe
    df['actor2_filled'] = df['actor2'].fillna('')
    df['notes_filled'] = df['notes'].fillna('')

    text_series = (
        "Il " + df['event_date'].dt.strftime('%Y-%m-%d') +
        " a " + df['location'].fillna('') + ", " + df['admin2'].fillna('') + ", " +
        df['admin1'].fillna('') + ", " + df['country'] +
        " si è verificato un evento di tipo " + df['event_type'] +
        " (" + df['sub_event_type'] + "), disorder type: " + df['disorder_type'] +
        ". Coinvolti: " + df['actor1'] +
        np.where(df['actor2_filled'] != '', " contro " + df['actor2_filled'], "") +
        ". Fatalities: " + df['fatalities'].astype(str) +
        ". Note: " + df['notes_filled']
    )

    metadata_cols = ['event_id_cnty','event_date','year','disorder_type','event_type',
                      'sub_event_type','actor1','actor2','country','region','admin1',
                      'civilian_targeting','fatalities','latitude','longitude']
    metadata_df = df[metadata_cols].copy()
    metadata_df['event_date'] = metadata_df['event_date'].astype(str)

    documents = [
        {"text": t, "metadata": m}
        for t, m in zip(text_series, metadata_df.to_dict('records'))
    ]
    return documents, df



if __name__ == "__main__":
    import time

    # prima testa su poche righe per verificare la logica
    df_sample = pd.read_csv("acled_data.csv", nrows=1000, parse_dates=['event_date'])
    df_sample.to_csv("acled_sample.csv", index=False)

    start = time.time()
    documents, df = build_documents("acled_sample.csv")
    elapsed = time.time() - start

    print(f"Tempo per {len(documents)} documenti: {elapsed:.2f}s")
    print("\n--- Esempio documento 0 ---")
    print(documents[0]["text"])
    print(documents[0]["metadata"])

    print("\n--- Controllo NaN/valori strani ---")
    print("Numero documenti con 'nan' nel testo:", sum("nan" in d["text"].lower() for d in documents))
    print("Fatalities negative?", (df['fatalities'] < 0).any())
    print("Date non parsate correttamente?", df['event_date'].isna().sum())
    
    nan_docs = [d for d in documents if "nan" in d["text"].lower()]

print(f"Documenti con 'nan' nel testo: {len(nan_docs)}")