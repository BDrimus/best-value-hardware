from dataclasses import dataclass
from database.gpu import GPU

@dataclass
class Listing:
    title: str
    url: str
    gpu: GPU
