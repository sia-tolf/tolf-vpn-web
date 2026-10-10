#!/usr/bin/env python3
"""Offline regression checks: native VPN object survives unchanged."""
import copy, importlib.util
from pathlib import Path
spec=importlib.util.spec_from_file_location("builder",Path(__file__).with_name("build.py"))
builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
vpn={"title":"Synthetic test VPN","identifier":"11111111-1111-1111-1111-111111111111","appDescriptor":{"BundleIdentifier":"com.example.test","Name":"Test","TeamIdentifier":"TEST"}}
source={"WFWorkflowClientVersion":"4402.0.1","WFWorkflowImportQuestions":[],"WFWorkflowActions":[
 {"WFWorkflowActionIdentifier":"is.workflow.actions.vpn.set","WFWorkflowActionParameters":{"UUID":"one","WFVPN":copy.deepcopy(vpn),"WFVPNOperation":"Set On Demand"}},
 {"WFWorkflowActionIdentifier":"is.workflow.actions.vpn.set","WFWorkflowActionParameters":{"UUID":"two","WFVPN":copy.deepcopy(vpn)}}]}
assert builder.make_shortcut(source,True)==source
off=builder.make_shortcut(source,False)
assert off["WFWorkflowActions"][0]["WFWorkflowActionParameters"].pop("WFOnDemandValue") is False
assert off["WFWorkflowActions"][1]["WFWorkflowActionParameters"].pop("WFVPNOperation")=="Disconnect"
assert off==source
for invalid in ["Text instead of VPN object",{"title":"Missing identifier"}]:
 bad=copy.deepcopy(source)
 for a in bad["WFWorkflowActions"]: a["WFWorkflowActionParameters"]["WFVPN"]=invalid
 try: builder.make_shortcut(bad,True)
 except ValueError: pass
 else: raise AssertionError("Invalid VPN binding accepted")
print("PASS: native binding preserved; exact OFF delta; malformed bindings rejected")

for on in (True,False):
    extended=builder.make_shortcut(source,on,return_home=True)
    home=extended["WFWorkflowActions"].pop()
    assert home=={"WFWorkflowActionIdentifier":"is.workflow.actions.returntohomescreen","WFWorkflowActionParameters":{}}
    assert extended==builder.make_shortcut(source,on)
print("PASS: return-home appends one final action, preserving all VPN operations")
