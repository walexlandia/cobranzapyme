import enum


class Role(str, enum.Enum):
    ADMIN = "admin"
    OPERATOR = "operator"
    CLIENT = "client"


class ActorType(str, enum.Enum):
    SYSTEM = "system"
    AI = "ai"
    HUMAN = "human"
    PAYER = "payer"


class InvoiceStatus(str, enum.Enum):
    ISSUED = "issued"
    PAID = "paid"
    VOID = "void"
    CLAIMED = "claimed"
    DISPUTED = "disputed"

