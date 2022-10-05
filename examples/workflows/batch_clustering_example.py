import os
import json
import base64
import numpy as np

from typing import List, Optional

from workflows_core.api.client import Client
from workflows_core.dataset.dataset import Dataset
from workflows_core.engine.stable_engine import StableEngine

from workflows_core.utils.random import mock_documents
from workflows_core.workflow.helpers import decode_workflow_token

from workflows_core.workflow.abstract_workflow import AbstractWorkflow
from workflows_core.operator.abstract_operator import AbstractOperator

from workflows_core.utils.random import Document

from sklearn.cluster import MiniBatchKMeans


class BatchClusterFitOperator(AbstractOperator):
    def __init__(
        self,
        n_clusters: int,
        vector_field: str,
        alias: Optional[str] = None,
    ):

        self._model = MiniBatchKMeans(n_clusters=n_clusters)

        self._vector_field = vector_field
        self._alias = f"minibatchkmeans-{n_clusters}" if alias is None else alias
        self._output_field = f"_cluster_.{vector_field}.{self._alias}"

    def transform(self, documents: List[Document]) -> List[Document]:
        """
        Main transform function
        """
        vectors = np.array(
            [np.array(document.get(self._vector_field)) for document in documents]
        )
        self._model.partial_fit(vectors)
        return documents


class BatchClusterPredictOperator(AbstractOperator):
    def __init__(
        self,
        model: MiniBatchKMeans,
        vector_field: str,
        alias: Optional[str] = None,
    ):
        self._model = model
        self._vector_field = vector_field
        self._alias = f"minibatchkmeans-{model.n_clusters}" if alias is None else alias
        self._output_field = f"_cluster_.{vector_field}.{self._alias}"

    def transform(self, documents: List[Document]) -> List[Document]:
        """
        Main transform function
        """

        vectors = np.array(
            [np.array(document.get(self._vector_field)) for document in documents]
        )
        labels = self._model.predict(vectors).tolist()

        for document, label in zip(documents, labels):
            document.set(self._output_field, f"cluster_{label}")

        return documents

    def post_hooks(self, dataset: Dataset):
        """
        Insert the centroids after clustering
        """
        centroid_documents = [
            dict(_id=f"cluster_{_id}", centroid_vector=centroid_vector)
            for _id, centroid_vector in enumerate(self._model.cluster_centers_.tolist())
        ]

        alias = self._alias
        vector_field = self._vector_field

        dataset[vector_field].insert_centroids(
            centroid_documents=centroid_documents, alias=alias
        )


class BatchClusterFitWorkflow(AbstractWorkflow):
    pass


class BatchClusterPredictWorkflow(AbstractWorkflow):
    pass


def main(token: str):
    config = decode_workflow_token(token)

    token = config["authorizationToken"]
    dataset_id = config["dataset_id"]
    vector_field = config["vector_field"]
    alias = config.get("alias", None)
    n_clusters = config.get("n_clusters", 8)

    client = Client(token=token)

    dataset = client.Dataset(dataset_id)

    fit_operator = BatchClusterFitOperator(
        n_clusters=n_clusters,
        vector_field=vector_field,
    )
    predict_operator = BatchClusterPredictOperator(
        model=fit_operator._model,
        vector_field=vector_field,
        alias=alias,
    )

    filters = dataset[vector_field].exists()
    chunksize = 8

    fit_engine = StableEngine(
        dataset=dataset,
        operator=fit_operator,
        chunksize=chunksize,
        select_fields=[vector_field],
        filters=filters,
    )

    predict_engine = StableEngine(
        dataset=dataset,
        operator=predict_operator,
        chunksize=chunksize,
        select_fields=[vector_field],
        filters=filters,
    )

    fit_workflow = BatchClusterFitOperator(fit_engine)
    fit_workflow.run()

    predict_workflow = BatchClusterPredictOperator(predict_engine)
    predict_workflow.run()


if __name__ == "__main__":
    config = dict(
        authorizationToken=os.getenv("TOKEN"),
        dataset_id="test_dataset",
        vector_field="sample_1_label_sentence-transformers-all-mpnet-base-v2_vector_",
    )
    string = f"{json.dumps(config)}"
    bytes = string.encode()
    token = base64.b64encode(bytes).decode()
    main(token)
