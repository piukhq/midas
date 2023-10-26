import json
import os

import pytest


def test_run():
    retailers = ["itsu", "stonegate", "wasabi"]
    for ret in retailers:
        path = os.getcwd() + f"/app/tests/component/retailer_fixtures/{ret}.json"
        with open(path, "r") as json_data:
            data = json.load(json_data)
            # Patch the target function within the test function
            pytest.main(["test_component.py::test_join", f"--retailer_fixture={data}"])
