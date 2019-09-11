from dataclasses import dataclass


@dataclass(frozen=True)
class Secret:
    key: str
    val: str

    @property
    def env_key(self):
        return self.key.upper().replace("-", "_")

    def __hash__(self):
        return hash(self.key)

    def __eq__(self, other: "Secret"):
        return self.key == other.key

    def __ne__(self, other: "Secret"):
        return not self.__eq__(other)

    def __lt__(self, other: "Secret"):
        return NotImplemented

    def __le__(self, other: "Secret"):
        return self.__eq__(other)

    def __gt__(self, other: "Secret"):
        return NotImplemented

    def __ge__(self, other: "Secret"):
        return self.__eq__(other)

    def __repr__(self):
        return "%s: '%s'" % (self.key, "*****")
