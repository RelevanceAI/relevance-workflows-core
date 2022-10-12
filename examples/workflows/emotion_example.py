# For this workflow to to run, you need the following;
# transformers[torch]==4.18.0
# relevance-workflows-core

import uuid
import torch

from typing import Callable, List, Optional

from transformers import pipeline
from workflows_core.api.client import Client
from workflows_core.engine.stable_engine import StableEngine
from workflows_core.workflow.helpers import decode_workflow_token
from workflows_core.workflow.abstract_workflow import AbstractWorkflow
from workflows_core.operator.abstract_operator import AbstractOperator
from workflows_core.utils.random import Document


class EmotionOperator(AbstractOperator):
    def __init__(
        self,
        text_field: str,
        model: str = "Emanuel/bertweet-emotion-base",
        alias: Optional[str] = None,
        min_score: float = 0.1,
    ):

        device = 0 if torch.cuda.is_available() else -1
        self._model = pipeline(
            "sentiment-analysis", model=model, device=device, return_all_scores=True
        )

        self._text_field = text_field
        self._alias = model.replace("/", "-") if alias is None else alias
        self._output_field = f"_emotion_.{text_field}.{self._alias}"
        self._min_score = min_score

        super().__init__(
            input_fields=[text_field],
            output_fields=[
                f"{self._output_field}.label",
                f"{self._output_field}.score",
            ],
        )

    def transform(self, documents: List[Document]) -> List[Document]:
        """
        Main transform function
        """

        batch = [document.get(self._text_field) for document in documents]
        labels = self._model(batch)

        for index in range(len(labels)):
            _labels = labels[index]
            _label = max(_labels, key=lambda logit: logit["score"])

            score = _label["score"]
            if score < self._min_score:
                emotion = dict(label="No emotion detected")

            else:
                label = _label["label"]
                emotion = dict(label=label, score=score)

            documents[index].set(self._output_field, emotion)

        return documents


def execute(token: str, logger: Callable, worker_number: int = 0, *args, **kwargs):
    config = decode_workflow_token(token)

    workflow_id = config.get("workflow_id", str(uuid.uuid4()))
    token = config["authorizationToken"]
    dataset_id = config["dataset_id"]
    text_fields: list = config["text_fields"]
    model: str = config.get("model_id", "Emanuel/bertweet-emotion-base")
    alias: list = config.get("alias", None)
    min_score = float(config.get("min_score", 0.1))
    filters: list = config.get("filters", [])
    chunksize: int = 8

    alias = config.get("alias", None)

    client = Client(token=token)
    dataset = client.Dataset(dataset_id)

    operator = EmotionOperator(
        text_field=text_fields[0], model=model, alias=alias, min_score=min_score
    )

    filters = dataset[text_fields[0]].exists()

    engine = StableEngine(
        dataset=dataset,
        operator=operator,
        chunksize=chunksize,
        select_fields=text_fields,
        filters=filters,
        worker_number=worker_number,
    )

    workflow = AbstractWorkflow(engine=engine, workflow_id=workflow_id)
    workflow.run()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Emotion workflow.")
    parser.add_argument(
        "token",
        type=str,
        help="a base64 encoded token that contains parameters for running the workflow",
    )
    args = parser.parse_args()
    execute(args.token, print)
