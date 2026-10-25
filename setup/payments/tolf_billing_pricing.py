"""Authoritative integer pricing for 50–1000 decimal gigabytes."""
import re
from fastapi import HTTPException
VERSION='volume-parabola-20261025-v1'
MIN_GB=50
MAX_GB=1000
def quote(sku):
    if not isinstance(sku,str) or not re.fullmatch(r'[1-9][0-9]{1,3}',sku):
        raise HTTPException(400,'invalid_package')
    gb=int(sku)
    if not MIN_GB<=gb<=MAX_GB:
        raise HTTPException(400,'invalid_package')
    return gb,(7500*gb-3*gb*gb+625)//1250
def require_version(payload):
    if payload.get('pricingVersion')!=VERSION:
        raise HTTPException(409,'pricing_changed')
