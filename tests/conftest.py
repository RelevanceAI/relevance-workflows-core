import base64
import json
import os
import random
import string
import pytest

from typing import Any, List, Optional

from core import Client, Dataset
from core.api import process_token
from core.utils import Document, mock_documents, static_documents
from core.operator import AbstractOperator
from core.engine import AbstractEngine


TEST_TOKEN = os.getenv("TEST_TOKEN")
test_creds = process_token(TEST_TOKEN)


@pytest.fixture(scope="session")
def test_token() -> str:
    return TEST_TOKEN


@pytest.fixture(scope="session")
def test_client(test_token: str) -> Client:
    return Client(test_token)


@pytest.fixture(scope="function")
def test_dataset_id() -> str:
    salt = "".join(random.choices(string.ascii_lowercase, k=10))
    dataset_id = f"_sample_dataset_{salt}"
    return dataset_id


@pytest.fixture(scope="class")
def empty_dataset(test_client: Client) -> Dataset:
    salt = "".join(random.choices(string.ascii_lowercase, k=10))
    dataset_id = f"_sample_dataset_{salt}"
    dataset = test_client.Dataset(dataset_id)
    yield dataset
    test_client.delete_dataset(dataset_id)


@pytest.fixture(scope="class")
def full_dataset(test_client: Client) -> Dataset:
    salt = "".join(random.choices(string.ascii_lowercase, k=10))
    dataset_id = f"_sample_dataset_{salt}"
    dataset = test_client.Dataset(dataset_id)
    dataset.insert_documents(mock_documents(20))
    yield dataset
    test_client.delete_dataset(dataset_id)


@pytest.fixture(scope="class")
def static_dataset(test_client: Client) -> Dataset:
    salt = "".join(random.choices(string.ascii_lowercase, k=10))
    dataset_id = f"_sample_dataset_{salt}"
    dataset = test_client.Dataset(dataset_id)
    dataset.insert_documents(static_documents(20))
    yield dataset
    test_client.delete_dataset(dataset_id)


@pytest.fixture(scope="function")
def test_document() -> Document:
    raw_dict = {
        "field1": {"field2": 1},
        "field3": 3,
    }
    return Document(raw_dict)


@pytest.fixture(scope="function")
def test_operator() -> AbstractOperator:
    class ExampleOperator(AbstractOperator):
        def transform(self, documents: List[Document]) -> List[Document]:
            """
            Main transform function
            """

            for document in documents:
                document.set("new_field", 3)

            return documents

    return ExampleOperator()


@pytest.fixture(scope="function")
def test_engine(
    full_dataset: Dataset, test_operator: AbstractOperator
) -> AbstractEngine:
    class TestEngine(AbstractEngine):
        def apply(self) -> Any:

            for chunk in self.iterate():
                new_batch = self.operator(chunk)
                self.update_chunk(new_batch)

            return

    return TestEngine(full_dataset, test_operator)


@pytest.fixture(scope="session")
def test_workflow_token() -> str:
    config = dict(
        authorizationToken=os.getenv("TOKEN"),
        dataset_id="test_dataset",
        field="feild1.field2",
    )
    string = f"{json.dumps(config)}"
    bytes = string.encode()
    token = base64.b64encode(bytes).decode()
    return token
