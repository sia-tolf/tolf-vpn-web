"""Build shared controller with fixed native VPN bindings for all devices."""
import copy, plistlib, sys, uuid
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"setup/anyconnect"))
from tolf_oc_shortcuts import controller, sign

def action(kind, **params):
    return {"WFWorkflowActionIdentifier":"is.workflow.actions."+kind,"WFWorkflowActionParameters":params}

def build():
    doc=controller("TOLF Москва")
    doc["WFWorkflowName"]="TOLF"
    doc["WFWorkflowHasShortcutInputVariables"]=True
    doc["WFWorkflowInputContentItemClasses"]=["WFStringContentItem"]
    uid="4412CB76-318A-4B94-AF3D-9277B57914C5"
    text=action("gettext",UUID=uid,WFTextActionText={
        "WFSerializationType":"WFTextTokenString","Value":{
            "string":"\uFFFC","attachmentsByRange":{"{0, 1}":{"Type":"ExtensionInput"}}}})
    variable={"Type":"Variable","Variable":{"WFSerializationType":"WFTextTokenAttachment","Value":{
        "Type":"ActionOutput","OutputUUID":uid,"OutputName":"Text",
        "Aggrandizements":[{"Type":"WFCoercionVariableAggrandizement","CoercionItemClass":"WFStringContentItem"}]}}}
    def flow(group,mode,**extra):
        return action("conditional",GroupingIdentifier=group,WFControlFlowMode=mode,**extra)
    serial=0
    def city_menu(city):
        nonlocal serial
        serial+=1
        actions=copy.deepcopy(controller("TOLF "+city)["WFWorkflowActions"][:-3])
        group=str(uuid.uuid5(uuid.NAMESPACE_URL,"tolf/shared/menu/"+str(serial))).upper()
        for a in actions:
            if a["WFWorkflowActionIdentifier"]=="is.workflow.actions.choosefrommenu":
                a["WFWorkflowActionParameters"]["GroupingIdentifier"]=group
        return actions
    g1="62A55CA8-57C7-4C48-AF0A-B6E9BEA01686"
    g2="37D9C862-0634-4C79-B523-39585F132412"
    gm="1868AA94-0050-457C-986E-11F058C3E0E2"
    acts=[text,flow(g1,0,WFInput=variable,WFCondition=4,WFConditionalActionString="moscow")]
    acts+=city_menu("Москва")+[flow(g1,1),flow(g2,0,WFInput=variable,WFCondition=4,WFConditionalActionString="riga")]
    acts+=city_menu("Рига")+[flow(g2,1)]
    acts+=[action("choosefrommenu",GroupingIdentifier=gm,WFControlFlowMode=0,WFMenuPrompt="TOLF — подключение",WFMenuItems=[
        {"WFItemType":0,"WFValue":"Москва"},{"WFItemType":0,"WFValue":"Рига"}])]
    for city in ("Москва","Рига"):
        acts+=[action("choosefrommenu",GroupingIdentifier=gm,WFControlFlowMode=1,
            WFMenuItemTitle=city,WFMenuItemAttributedTitle=city)]
        acts+=city_menu(city)
    acts+=[action("choosefrommenu",GroupingIdentifier=gm,WFControlFlowMode=2),flow(g2,2),flow(g1,2)]
    acts+=doc["WFWorkflowActions"][-3:]
    doc["WFWorkflowActions"]=acts
    return doc

if __name__=="__main__":
    doc=build()
    raw=plistlib.dumps(doc,fmt=plistlib.FMT_XML,sort_keys=False)
    dest=Path(__file__).parent/"universal"
    dest.mkdir(exist_ok=True)
    (dest/"TOLF.plist").write_bytes(raw)
    (dest/"TOLF.shortcut").write_bytes(sign(raw,"TOLF"))
    print("Signed shared TOLF controller: fixed Moscow/Riga bindings")
