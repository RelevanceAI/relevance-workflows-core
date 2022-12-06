import warnings

from collections import UserList
from typing import Any, Dict, List, Union

from workflows_core.utils.document import Document


class DocumentList(UserList):
    data: List[Document]

    def __init__(self, initlist=None):
        if initlist is not None:
            for index, document in enumerate(initlist):
                if not isinstance(document, Document):
                    initlist[index] = Document(document)
        super().__init__(initlist)

    def __repr__(self):
        return repr(self.data)

    def __getitem__(self, key: Union[str, int]) -> Union[Document, "DocumentList"]:
        if isinstance(key, str):
            return [document[key] for document in self.data]
        elif isinstance(key, slice):
            return self.__class__(self.data[key])
        elif isinstance(key, int):
            return self.data[key]

    def __setitem__(self, key: Union[str, int], value: Union[Any, List[Any]]):
        if isinstance(key, str):
            if isinstance(value, list):
                for document, value in zip(self.data, value):
                    document[key] = value
            else:
                for document in self.data:
                    document[key] = value
        elif isinstance(key, int):
            self.data[key] = value

    def to_json(self):
        return [document.to_json() for document in self.data]
    
    def set_chunks(self, chunk_field: str, field: str, values: list):
        """
        Set a list of lists - will overwrite if already there
        """
        # I'm not sure how we would actually use this one just yet...
        raise NotImplementedError

    def get_chunks(self, chunk_field: str, field: str):
        """
        Gets a list of list of values
        """
        docs = DocumentList(
            [
                DocumentList(
                    d.get(chunk_field)
                ) for d in self.data
            ]
        )
        return [d.get(field) for d in docs.data]
        
    def set_chunks_from_flat(self, chunk_field: str, field: str, values: list):
        """
        Set chunks from a flat list.
        Note that this is only possible if there is pre-existing
        chunk documents.
        """
        # general logic for this is that we assume that the number of values equals
        # to the number of chunk values
        chunk_counter = 0
        for i, doc in enumerate(self.data):
            for chunk_doc in doc.get(chunk_field, []):
                chunk_doc = Document(chunk_doc)
                chunk_doc.set(field, values[chunk_counter])
                chunk_counter += 1

        if chunk_counter > len(values):
            raise ValueError("Number of chunks do not match with number of values - check logic.")
    
    def get_chunks_as_flat(self, chunk_field: str, field: str, default=None):
        """
        Set chunks from a flat list.
        Note that this is only possible if there is pre-existing
        chunk documents.
        """
        docs = DocumentList([d.get(chunk_field) for d in self.data])
        return [d.get(field, default=default) for d in docs.data]

    def remove_tag(self, field: str, value: str) -> None:
        warnings.warn("This behaivour is experimental and is subject to change")

        *tag_fields, remove_field = field.split(".")
        tag_field = ".".join(tag_fields)

        for document in self.data:
            new_tags = []

            old_tags = document.get(tag_field, [])
            for tag_json in old_tags:
                if tag_json.get(remove_field) != value:
                    new_tags.append(tag_json)

            document[tag_field] = new_tags

    def append_tag(
        self, field: str, value: Union[Dict[str, Any], List[Dict[str, Any]]]
    ) -> None:
        warnings.warn("This behaivour is experimental and is subject to change")

        if isinstance(value, list):
            for document, tag in zip(self.data, value):
                document[field].append(tag)
        else:
            for document in self.data:
                document[field].append(value)

    def sort_tags(self, field: str, reverse: bool = False) -> None:
        warnings.warn("This behaivour is experimental and is subject to change")

        *tag_fields, sort_field = field.split(".")
        tag_field = ".".join(tag_fields)

        for document in self.data:
            tags = document.get(tag_field)

            if tags is not None:
                document[tag_field] = sorted(
                    document[tag_field],
                    key=lambda tag_json: tag_json[sort_field],
                    reverse=reverse,
                )
