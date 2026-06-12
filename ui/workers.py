"""Background workers for dictionary loading and typing."""

from PySide6.QtCore import QObject, Signal


class DictWorker(QObject):
    """Loads a dictionary file in a background thread.

    Moves to a QThread; call .run() via thread.started.connect().
    """

    finished = Signal(list, bool)  # wordlist, from_cache
    error = Signal(str)

    def __init__(self, session, path: str) -> None:
        super().__init__()
        self.session = session
        self.path = path

    def run(self) -> None:
        try:
            wordlist, from_cache = self.session.load_dictionary(self.path)
            self.finished.emit(wordlist, from_cache)
        except Exception as e:
            self.error.emit(str(e))


class TypeWorker(QObject):
    """Types a word into the focused window in a background thread.

    Moves to a QThread; call .run() via thread.started.connect().
    """

    finished = Signal(bool, str)  # success, message

    def __init__(self, session, completion: str,
                 pre_delay_s: float, post_delay_s: float) -> None:
        super().__init__()
        self.session = session
        self.completion = completion
        self.pre_delay_s = pre_delay_s
        self.post_delay_s = post_delay_s

    def run(self) -> None:
        success, msg = self.session.typer.type_text(
            self.completion,
            pre_delay_s=self.pre_delay_s,
            post_delay_s=self.post_delay_s,
        )
        self.finished.emit(success, msg)
