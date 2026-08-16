from pydantic import BaseModel


class GoodsCreatePyModel(BaseModel):
    name: str
    classify: str
    status: str
    price: float

class GoodsUpdatePyModel(BaseModel):
    name: str
    classify: str
    status: str
    price: float