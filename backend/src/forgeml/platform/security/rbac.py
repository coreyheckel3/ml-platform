from dataclasses import dataclass


@dataclass(frozen=True)
class Principal:
    user_id: str
    email: str
    organization_id: str
    permissions: frozenset[str]

    def has(self, permission: str) -> bool:
        return permission in self.permissions or "*" in self.permissions

