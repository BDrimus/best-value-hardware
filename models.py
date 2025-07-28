from dataclasses import dataclass

@dataclass
class GPUData:
    name: str
    g3d_mark: str

@dataclass
class EbayResult:
    name: str
    title: str
    price: float
    shipping_cost: float
    url: str
    performance_to_price_ratio: float = 0