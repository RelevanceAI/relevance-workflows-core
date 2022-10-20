import math
import time
import logging
import warnings

from typing import Any, List, Optional
from abc import ABC, abstractmethod

from workflows_core.types import Filter
from workflows_core.dataset.dataset import Dataset
from workflows_core.operator.abstract_operator import AbstractOperator
from workflows_core.utils.document import Document
from workflows_core.errors import MaxRetriesError


logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s:%(levelname)s:%(name)s:%(message)s"
)
logger = logging.getLogger(__name__)


class AbstractEngine(ABC):
    def __init__(
        self,
        dataset: Dataset,
        operator: AbstractOperator,
        filters: Optional[List[Filter]] = None,
        select_fields: Optional[List[str]] = None,
        chunksize: Optional[int] = 8,
        refresh: bool = True,
        after_id: Optional[List[str]] = None,
        worker_number: int = 0,
        total_workers: int = 0,
    ):
        if select_fields is not None:
            assert all(
                field in dataset.schema
                for field in select_fields
                if field not in {"_id", "insert_date_"}
            ), "Some fields not in dataset schema"

        self._dataset = dataset
        self._select_fields = select_fields
        self._size = dataset.len(filters=filters)
        self.worker_number = worker_number
        self.total_workers = total_workers

        if isinstance(chunksize, int):
            assert chunksize > 0, "Chunksize should be a Positive Integer"
            self._chunksize = chunksize
            self._num_chunks = math.ceil(self._size / chunksize)
        else:
            warnings.warn(
                f"`chunksize=None` assumes the operation transforms on the entire dataset at once"
            )
            self._chunksize = self._size
            self._num_chunks = 1

        if filters is None:
            self._filters = []
        else:
            self._filters = filters
        self._filters += self._get_workflow_filter()

        self._operator = operator

        self._refresh = refresh
        self._after_id = after_id

    @property
    def num_chunks(self) -> int:
        return self._num_chunks

    @property
    def operator(self) -> AbstractOperator:
        return self._operator

    @property
    def dataset(self) -> Dataset:
        return self._dataset

    @property
    def chunksize(self) -> int:
        return self._chunksize

    @property
    def size(self) -> int:
        return self._size

    @abstractmethod
    def apply(self) -> float:
        raise NotImplementedError

    def __call__(self) -> Any:
        self.operator.pre_hooks(self._dataset)
        success_ratio = self.apply()
        self.operator.post_hooks(self._dataset)
        return success_ratio

    def _get_workflow_filter(self, field: str = "_id"):
        # Get the required workflow filter as an environment variable
        # WORKER_NUMBER is passed into execute function
        if self.worker_number and self.total_workers:
            return [
                {
                    "matchModulo": {
                        "field": field,
                        "modulo": self.total_workers,
                        "value": self.worker_number,
                    }
                }
            ]
        return []

    def iterate(
        self,
        filters: Optional[List[Filter]] = None,
        select_fields: Optional[List[str]] = None,
        max_retries: int = 3,
    ):
        if filters is None:
            filters = self._filters

        if select_fields is None:
            select_fields = self._select_fields

        retry_count = 0
        while True:
            try:
                chunk = self._dataset.get_documents(
                    self._chunksize,
                    filters=filters,
                    select_fields=select_fields,
                    after_id=self._after_id,
                    worker_number=self.worker_number,
                )
            except ConnectionError as e:
                logger.error(e)
                retry_count += 1
                time.sleep(1)

                if retry_count >= max_retries:
                    raise MaxRetriesError("max number of retries exceeded")
            else:
                self._after_id = chunk["after_id"]
                if not chunk["documents"]:
                    break
                yield chunk["documents"]
                retry_count = 0

    def update_chunk(self, chunk: List[Document], max_retries: int = 3):
        if chunk:
            for _ in range(max_retries):
                try:
                    update_json = self._dataset.update_documents(documents=chunk)
                except Exception as e:
                    logger.error(e)
                else:
                    return update_json

            raise MaxRetriesError("max number of retries exceeded")
