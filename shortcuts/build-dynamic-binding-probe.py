"""Isolated iOS probe: variable inside the native VPN entity title.
This serialization is experimental; do not use in the production installer
until an iOS test confirms the named On Demand setting actually changes.
"""
import copy, plistlib, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"setup/anyconnect"))
from tolf_oc_shortcuts import controller, sign

def build():
    doc=controller("TOLF Москва iPad")
    doc["WFWorkflowName"]="TOLF-Binding-Check"
    uid="EC3AD564-3619-4C11-AD7F-13972B328CEE"
    token={"WFSerializationType":"WFTextTokenString","Value":{
        "string":"\uFFFC","attachmentsByRange":{"{0, 1}":{
            "Type":"ActionOutput","OutputUUID":uid,"OutputName":"Text"}}}}
    action=copy.deepcopy(next(a for a in doc["WFWorkflowActions"]
        if a["WFWorkflowActionIdentifier"]=="is.workflow.actions.vpn.set"
        and a["WFWorkflowActionParameters"].get("WFOnDemandValue")==0))
    action["WFWorkflowActionParameters"]["WFVPN"]["title"]=token
    doc["WFWorkflowActions"]=[
        {"WFWorkflowActionIdentifier":"is.workflow.actions.gettext",
         "WFWorkflowActionParameters":{"UUID":uid,"WFTextActionText":"TOLF Москва iPad"}},
        action,
        {"WFWorkflowActionIdentifier":"is.workflow.actions.nothing","WFWorkflowActionParameters":{}}]
    return doc

if __name__=="__main__":
    doc=build()
    raw=plistlib.dumps(doc,fmt=plistlib.FMT_XML,sort_keys=False)
    dest=Path(__file__).parent/"probe"
    (dest/"TOLF-Binding-Check.plist").write_bytes(raw)
    (dest/"TOLF-Binding-Check.shortcut").write_bytes(sign(raw,doc["WFWorkflowName"]))
    print("Signed isolated On Demand OFF binding probe")
