import datetime as dt
import importlib
import json
import math
import os

import pandas as pd
from airtable import Airtable

from . import whiteflag


def lambda_handler(event, context):

    API_KEY = os.environ["API_KEY"]
    BASE_ID = os.environ["PROD_BASE_ID"]
    TABLE_ID = os.environ["TABLE_ID"]

    airtable = Airtable(BASE_ID, TABLE_ID, API_KEY)
    schema = whiteflag.Schema()

    df = pd.json_normalize(airtable.get_all())
    df.columns = [x.replace("fields.", "") for x in df.columns]
    df = df.set_index("id")

    try:
        _ = df[list(schema.get_unnested_dict().keys())]
    except KeyError as error:
        raise KeyError(
            f"Airtable column name(s) does not match entries in Schema.dict: {error}"
        )

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

    json_output = whiteflag.export_to_json(airtable, schema, df)

    if importlib.util.find_spec("boto3") is not None:
        import boto3

        s3 = boto3.client("s3")
        S3_KEY = os.environ["S3_KEY"]
        S3_BUCKET = os.environ["S3_BUCKET"]

        uploadByteStream = bytes(json.dumps(json_output).encode("UTF-8"))
        s3.put_object(Bucket=S3_BUCKET, Key=S3_KEY, Body=uploadByteStream)
        returnStatement = (
            f"Upload Complete... File uploaded to {S3_BUCKET} filename: {S3_KEY}"
        )

        return {"body": json.dumps(returnStatement)}

    else:
        now = dt.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        with open(f"./json_output/{now}-data.json", "w") as f:
            f.write(json.dumps(json_output))

        returnStatement = (
            f'Write Complete... File exported to "./json_output/{now}-data.json"'
        )

        return {"body": json.dumps(json_output)}
