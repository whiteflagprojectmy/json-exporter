import copy
import datetime as dt
import json
import math
import re

import jsonschema as js
import jsonschema.exceptions as json_except
import jsonschema.validators as json_validator
from pandas import isnull


class Schema:
    def __init__(self, schema_file="./schema.json"):
        with open(schema_file) as f:
            self.validator = json_validator.Draft6Validator(json.load(f))

        self.meta_definition = self.validator.schema["definitions"]["meta"]
        self.contact_definition = self.validator.schema["definitions"]["contact"]
        self.location_definition = self.validator.schema["definitions"]["location"]
        self.resource_definition = self.validator.schema["definitions"]["resource"]

        self.dict = {
            "meta": {
                "createdTime": "createdDatetime",
                "Latest Social Media Post Date": "lastUpdated",
                "Inactive?": "inactive",
                "Schema Validated": "validated",
            },
            "contact": {
                "Contact Name": "name",
                "Contact Number(s)": "phone",
                "Contact Method(s)": "preferredMethod",
                "Contact Freeform Info": "additionalNotes",
            },
            "location": {
                "Freeform Address": "address",
                "Postcode": "postcode",
                "City": "city",
                "State/WP": "state",
                "GPS Latitude": "latitude",
                "GPS Longitude": "longitude",
                "Operating Hours": "operatingTime",
                "Covers Area?": "coversArea",
            },
            "resource": {
                "Resource Name": "businessName",
                "Must Contact First?": "mustContactFirst",
                "Organisation Name": "hostOrganization",
                "Launch URL Date": "launchDate",
                "Launch URL": "postUrl",
                "Resource End Date": "endDate",
                "Resources Offered": "offerings",
                "Launch URL Language": "language",
                "Estimated Supply Levels": "estimatedStock",
                "Access Method": "accessMethod",
                "Other Limits": "limitations",
                "Freeform Notes Misc": "additionalNotes",
                "Religious Organisation?": "religiousAffiliation",
                "Organization Scale": "organizationScale",
            },
        }

    def get_unnested_dict(self):
        return {
            key: val for _, nested in self.dict.items() for key, val in nested.items()
        }

    def get_airtable_dict(self):
        return {key: list(nested.keys()) for key, nested in self.dict.items()}

    def get_json_dict(self):
        json_dict = copy.deepcopy(self.dict)
        json_dict["meta"].pop("Schema Validated")
        return {key: list(nested.values()) for key, nested in json_dict.items()}

    def validate_compliance(self, json):
        issues = []
        try:
            js.validate(instance=[json], schema=self.validator.schema)

        except json_except.ValidationError:
            # If a single field is non-compliant, we search and flag all non-compliant fields
            for error in sorted(self.validator.iter_errors([json]), key=str):
                issues.append(error.message)

            return ", ".join(issues)

        return ""


def format_phone_number(phone):

    if isnull(phone) or type(phone) is not str:
        return math.nan, math.nan

    # First we extract any text that is not a phone number
    # We will chuck anything here in the additional info column
    text = re.sub(r"(?<=[\s\d])-(?=[\s\d])", "", phone)
    text = re.sub(r"\+6\d{1,}|\s?\d{3,}(?!\w)|(?![',-@])\W", " ", text)
    non_phone = []

    for t in re.sub(r"\s{2,}|:", "", text).split(","):
        t = t.strip()
        if t != "" and t != "/":
            non_phone.append(t)

    non_phone = ", ".join(non_phone)

    # Now we look for the phone numbers
    phone = re.sub(r"[\s-]", "", phone.replace("/", ","))
    phone_list = []

    for p in phone.split(","):

        for match in re.findall(r"\d{8,}", re.sub(r"^\+60|^0|^60|[A-Za-z\W]0", "", p)):
            match = "+60" + match
            phone_list.append(match[0:5] + "-" + match[5:8] + "-" + match[8:])

    phone_list = phone_list if phone_list else math.nan
    non_phone = non_phone if non_phone else math.nan

    return phone_list, non_phone


def construct_json(record_id, json_dict, row):

    return (
        "{"
        + '"meta": '
        + json.dumps(
            {"recordId": record_id, **row[json_dict["meta"]].dropna().to_dict()}
        )
        + ", "
        + '"contact": '
        + json.dumps(row[json_dict["contact"]].dropna().to_dict())
        + ", "
        + '"location": '
        + json.dumps(row[json_dict["location"]].dropna().to_dict())
        + ", "
        + '"resource": '
        + json.dumps(row[json_dict["resource"]].dropna().to_dict())
        + "}"
    )


def export_to_json(airtable, schema, df):  # pragma: no cover

    json_export = []
    json_dict = schema.get_json_dict()
    unnested_dict = schema.get_unnested_dict()

    for record_id, row in df.iterrows():

        record = construct_json(record_id, json_dict, row.rename(unnested_dict))
        issues = schema.validate_compliance(json.loads(record))

        if not issues:
            json_export.append(record)

            if not isnull(row["Schema Validated"]) and row["Schema Validated"]:
                continue
            else:
                if type(row["Contact Number(s)"]) is list:
                    row["Contact Number(s)"] = ", ".join(row["Contact Number(s)"])

                fields = (
                    row[
                        [
                            "Contact Number(s)",
                            "Contact Freeform Info",
                            "Postcode",
                            "Religious Organisation?",
                        ]
                    ]
                    .dropna()
                    .to_dict()
                )
                fields.update({"Schema Error": "", "Schema Validated": True})
                airtable.update(record_id, fields)

        else:
            airtable.update(
                record_id,
                {"Schema Error": issues, "Schema Validated": False},
            )

    now = dt.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    with open(f"./json_output/{now}-data.json", "w") as f:
        f.write("[" + ",\n".join(json_export) + "]")
