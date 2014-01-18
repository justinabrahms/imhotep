class UnknownTools(Exception):
    def __init__(self, known):
        self.known = known


class NoCommitInfo(Exception):
    pass
