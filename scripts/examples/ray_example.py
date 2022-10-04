import os
import json
import base64
from typing import List

import pandas as pd
import pyarrow as pa

from ray.data.block import Block

from core.api import Client
from core.engine import RayEngine
from core.operator import AbstractRayOperator
from core.workflow import AbstractWorkflow
from core.utils import Document
from core.workflow.helpers import decode_workflow_token

TOKEN = os.getenv("TOKEN")


class RayOperator(AbstractRayOperator):
    def __init__(self, field: str):
        self._field = field

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Main transform function
        """
        df[self._field] += 1

        return df


class ExampleWorkflow(AbstractWorkflow):
    def pre_hook(self):
        """
        Optional Method
        """
        print("Starting Workflow")
        print(f"Using {type(self.operator).__name__} as Operator")

    def post_hook(self):
        """
        Optional Method
        """
        print(f"Dataset has {len(self.dataset)} documents")
        print("Finished Workflow")


def main(token: str):
    config = decode_workflow_token(token)

    token = config["authorizationToken"]
    datatset_id = config["dataset_id"]
    field = config["field"]

    client = Client(token=token)

    dataset = client.Dataset(datatset_id)
    operator = RayOperator(field=field)

    engine = RayEngine(dataset=dataset, operator=operator)

    workflow = ExampleWorkflow(engine)
    workflow.run()


if __name__ == "__main__":
    config = dict(
        authorizationToken=os.getenv("TOKEN"),
        dataset_id="test_dataset",
        field="new_field1.new_field2",
    )
    string = f"{json.dumps(config)}"
    bytes = string.encode()
    token = base64.b64encode(bytes).decode()
    main(token)
