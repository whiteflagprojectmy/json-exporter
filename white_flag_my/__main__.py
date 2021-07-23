import math
import os

import pandas as pd
from airtable import Airtable
from dotenv import load_dotenv

from . import whiteflag

if __name__ == "__main__":
    load_dotenv("./.env")
    api_key = os.environ.get("API_KEY")
    base_id = os.environ.get("PROD_BASE_ID")
    data_table = os.environ.get("TABLE_ID")

    airtable = Airtable(base_id, data_table, api_key)
    schema = whiteflag.Schema()

    df = pd.json_normalize(airtable.get_all())
    df.columns = [x.replace("fields.", "") for x in df.columns]
    df = df.set_index("id")

    df.replace("?", math.nan, inplace=True)
    df.replace("N/A", math.nan, inplace=True)
    df.replace("", math.nan, inplace=True)

    # Clean meta properties
    df["Inactive?"] = ~df["Inactive?"].isna()

    # Clean contact properties
    phone = []
    phone_notes = []
    for num, info in zip(df["Contact Number(s)"], df["Contact Freeform Info"]):

        if pd.isnull(num):
            phone.append(math.nan)
            phone_notes.append(info)
        else:
            py_num, py_info = whiteflag.format_phone_number(num)
            phone.append(py_num)

            if pd.isnull(py_info) or not py_info:
                phone_notes.append(info)
            else:
                phone_notes.append(
                    py_info if pd.isnull(info) else py_info + "; " + info
                )

    df["Contact Number(s)"] = phone
    df["Contact Freeform Info"] = phone_notes

    # Clean location properties
    df["Postcode"] = df["Postcode"].map(lambda x: x if pd.isnull(x) else f"{int(x):5d}")
    df["Covers Area?"] = df["Covers Area?"].fillna(False)

    # Clean resource properties
    df["Must Contact First?"] = ~df["Must Contact First?"].isna()
    df["Religious Organisation?"] = df["Religious Organisation?"].map(
        lambda x: "Non-Affiliated" if pd.isnull(x) else x
    )
    df["Other Limits"] = [
        x if type(x) is list else math.nan for x in df["Other Limits"]
    ]
    df["Launch URL Language"] = [
        x if type(x) is list else math.nan for x in df["Launch URL Language"]
    ]

    notes = []
    for extra_notes in zip(
        df["Resource Freeform Notes"],
        df["Freeform Notes Misc"],
        df["Freeform Update Notes"],
    ):
        text = "; ".join(text for text in extra_notes if not pd.isnull(text) and text)

        if not text:
            notes.append(math.nan)
            continue

        notes.append(text)

    df["Freeform Notes Misc"] = notes

    whiteflag.export_to_json(airtable, schema, df)
