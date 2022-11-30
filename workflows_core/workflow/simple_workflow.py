import logging

from inspect import Traceback
from typing import Any, Dict, Optional

from workflows_core.api.api import API
from workflows_core.dataset.dataset import Dataset

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s:%(levelname)s:%(name)s:%(message)s"
)

logger = logging.getLogger(__file__)


class SimpleWorkflow(API):

    FAILED = "failed"
    COMPLETE = "complete"
    IN_PROGRESS = "inprogress"

    def __init__(
        self,
        workflow_name: str,
        job_id: str,
        dataset: Dataset,
        metadata: Optional[Dict[str, Any]] = None,
        additional_information: str = "",
        send_email: bool = True,
        worker_number: int = None,
        **kwargs
    ) -> None:
        super().__init__(dataset.api._credentials, job_id, workflow_name)

        self._dataset = dataset
        self._dataset_id = dataset.dataset_id

        self._workflow_name = workflow_name
        self._job_id = job_id
        self._worker_number = worker_number

        self._metadata = metadata
        self._additional_information = additional_information
        self._send_email = send_email

    def __enter__(self):
        """
        The workflow is in progress
        """
        self._set_status(status=self.IN_PROGRESS, worker_number=None)
        return

    def __exit__(self, exc_type: type, exc_value: BaseException, traceback: Traceback):
        if exc_type is not None:
            logger.exception("Exception")
            self._set_status(status=self.FAILED, worker_number=self._worker_number)
            self._update_workflow_metadata(
                job_id=self._job_id,
                metadata=dict(
                    _error_=dict(
                        exc_value=str(exc_value),
                        traceback=str(traceback),
                    ),
                ),
            )
            return False
        else:
            # Workflow must have run successfully
            self._set_status(status=self.COMPLETE, worker_number=self._worker_number)
            return True

    def _set_status(self, status: str, worker_number: int = None):
        """
        Set the status of the workflow
        """
        result = self._set_workflow_status(
            status=status,
            job_id=self._job_id,
            metadata={} if self._metadata is not None else self._metadata,
            workflow_name=self._workflow_name,
            additional_information=self._additional_information,
            send_email=self._send_email,
            worker_number=worker_number,
        )
        from workflows_core import __version__

        logger.debug(
            {
                "status": status,
                "job_id": self._job_id,
                "workflow_name": self._workflow_name,
                "worker_number": worker_number,
                "result": result,
                "workflows_core_version": __version__,
            }
        )
        return result
