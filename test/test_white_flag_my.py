import copy
import math

import pandas as pd
import pytest

from white_flag_my import whiteflag


@pytest.mark.parametrize(
    "input, expected",
    [
        ("+60123456789", (["+6012-345-6789"], math.nan)),
        ("0377212345 (En Pai Ton)", (["+6037-721-2345"], "En Pai Ton")),
        (
            "Anna: 0341512345, Quon Da: 01134512395",
            (["+6034-151-2345", "+6011-345-12395"], "Anna, Quon Da"),
        ),
        ("", (math.nan, math.nan)),
        (math.nan, (math.nan, math.nan)),
        ("SURE2FAIL", (math.nan, "SURE2FAIL")),
        ([], (math.nan, math.nan)),
    ],
)
def test_format_phone_number(input, expected) -> None:
    assert whiteflag.format_phone_number(input) == expected


@pytest.fixture
def json_data():

    data = {
        "record": "pytest_id",
        "json_dict": {
            "meta": ["meta_1"],
            "contact": ["contact_1", "contact_2"],
            "location": ["location_1", "location_2"],
            "resource": ["resource_1", "resource_2"],
        },
        "row": pd.Series(
            {
                "meta_1": 3.14159265,
                "contact_1": "Biggus Dickus",
                "contact_2": ["+1243-420-6969"],
                "location_1": math.nan,
                "location_2": "Ular Sour, Snek",
                "resource_1": 42,
                "resource_2": math.nan,
            }
        ),
    }

    return data


def test_construct_json(json_data):
    assert (
        whiteflag.construct_json(
            json_data["record"], json_data["json_dict"], json_data["row"]
        )
        == '{"meta": {"recordId": "pytest_id", "meta_1": 3.14159265}, '
        + '"contact": {"contact_1": "Biggus Dickus", "contact_2": ["+1243-420-6969"]}, '
        + '"location": {"location_2": "Ular Sour, Snek"}, '
        + '"resource": {"resource_1": 42}}'
    )


def test_schema_get_json():
    schema = whiteflag.Schema()

    s_dict = copy.deepcopy(schema.dict)
    s_dict["meta"].pop("Schema Validated")
    assert schema.get_json_dict() == {
        "meta": list(s_dict["meta"].values()),
        "contact": list(s_dict["contact"].values()),
        "location": list(s_dict["location"].values()),
        "resource": list(s_dict["resource"].values()),
    }


def test_schema_get_airtable():
    schema = whiteflag.Schema()

    s_dict = schema.dict
    assert schema.get_airtable_dict() == {
        "meta": list(s_dict["meta"].keys()),
        "contact": list(s_dict["contact"].keys()),
        "location": list(s_dict["location"].keys()),
        "resource": list(s_dict["resource"].keys()),
    }


def test_schema_get_unnested_dict():
    schema = whiteflag.Schema()

    unnested = schema.dict["meta"]
    unnested.update(schema.dict["contact"])
    unnested.update(schema.dict["location"])
    unnested.update(schema.dict["resource"])
    assert schema.get_unnested_dict() == unnested


@pytest.mark.parametrize(
    "input, expected",
    [
        (
            {
                "meta": {
                    "recordId": "pytest_id",
                    "createdDatetime": "1969-07-16T14:32:00.000Z",
                },
                "contact": {},
                "location": {},
                "resource": {
                    "businessName": "Kobis Briyani",
                    "accessMethod": ["Self-Service", "Home Delivery"],
                    "religiousAffiliation": "Non-Affiliated",
                },
            },
            "",
        ),
        (
            {
                "meta": {
                    "recordId": "pytest_id",
                    "createdDatetime": "1969-07-16T14:32:00.000Z",
                },
                "resource": {
                    "businessName": "Kobis Briyani",
                    "accessMethod": ["Self-Service", "Home Delivery"],
                    "religiousAffiliation": "Non-Affiliated",
                },
            },
            "'contact' is a required property, 'location' is a required property",
        ),
        (
            {
                "meta": {
                    "recordId": "pytest_id",
                    "createdDatetime": "1969-07-16T14:32:00.000Z",
                },
                "contact": {},
                "location": {},
                "resource": {
                    "businessName": "Kobis Briyani",
                    "accessMethod": ["Self-Service", "Home Delivery", "Jenga"],
                    "religiousAffiliation": "Non-Affiliated",
                },
            },
            "'Jenga' is not one of ['Self-Service', 'Arrange Pickup', 'Home Delivery', 'Online Only', 'Organisations Only', 'Other']",
        ),
    ],
)
def test_schema_validate_compliance(input, expected):
    schema = whiteflag.Schema()
    assert schema.validate_compliance(input) == expected
