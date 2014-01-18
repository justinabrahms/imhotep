class UnknownTools(Exception):
    def __init__(self, known):
        self.known = known


class NoReporterFound(Exception):
    pass


class NoCommitInfo(Exception):
    pass
