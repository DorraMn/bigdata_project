import abc
from typing import Any, Dict

class BaseInstaller(abc.ABC):
    def __init__(self, config: Dict[str, Any], progress_callback: callable, logger: Any):
        self.config = config
        self.progress = progress_callback
        self.logger = logger

    @abc.abstractmethod
    def check_prerequisites(self) -> None:
        pass

    @abc.abstractmethod
    def install(self) -> None:
        pass

    @abc.abstractmethod
    def test_installation(self) -> bool:
        pass

    @abc.abstractmethod
    def rollback(self) -> None:
        pass
