import json
from valuation.engine.router import ValuationRouter
router = ValuationRouter()
print("HPG:", router.get_routing("HPG"))
print("VCB:", router.get_routing("VCB"))
print("VHM:", router.get_routing("VHM"))
print("REE:", router.get_routing("REE"))
