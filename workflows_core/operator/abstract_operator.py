import logging
from copy import deepcopy
from abc import ABC, abstractmethod

from typing import List, Optional

from workflows_core.dataset.dataset import Dataset
from workflows_core.utils.document import Document
from workflows_core.utils.documents import Documents

logger = logging.getLogger(__file__)


def get_document_diff(old_document: Document, new_document: Document) -> Document:
    pp_document = Document()
    new_fields = new_document.keys()
    old_fields = old_document.keys()
    for field in new_fields:
        old_value = old_document.get(field, None)
        new_value = new_document.get(field, None)
        value_diff = old_value != new_value
        if field not in old_fields or value_diff or field == "_id":
            pp_document[field] = new_value
    return pp_document


class AbstractOperator(ABC):
    def __init__(
        self,
        input_fields: Optional[List[str]] = None,
        output_fields: Optional[List[str]] = None,
    ):
        self._input_fields = input_fields
        self._output_fields = output_fields

    @abstractmethod
    def transform(self, documents: Documents) -> Documents:
        """
        Every Operator needs a transform function
        """
        raise NotImplementedError

    def __repr__(self):
        return str(type(self).__name__)

    def __call__(self, old_documents: Documents) -> Documents:
        new_documents = deepcopy(old_documents)
        new_documents = self.transform(new_documents)
        new_documents = AbstractOperator._postprocess(new_documents, old_documents)
        return new_documents

    @staticmethod
    def _postprocess(new_batch: Documents, old_batch: Documents) -> Documents:
        """
        Removes fields from `new_batch` that are present in the `old_keys` list.
        Necessary to avoid bloating the upload payload with unnecesary information.
        """
        batch = []
        for old_document, new_document in zip(old_batch, new_batch):
            document_diff = get_document_diff(old_document, new_document)
            if document_diff:
                batch.append(document_diff)

        return Documents(batch)

    def pre_hooks(self, dataset: Dataset):
        pass

    def post_hooks(self, dataset: Dataset):
        pass
