"""Build one controller; do not modify the production two-shortcut generator."""
import plistlib
import sys
import uuid
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "setup/anyconnect"))
from tolf_oc_shortcuts import workflow, sign

def controller(name):
    doc = workflow(name, "on")
    doc["WFWorkflowName"] = "TOLF"
    doc["WFWorkflowHasShortcutInputVariables"] = True
    doc["WFWorkflowInputContentItemClasses"] = ["WFStringContentItem"]
    text_id = "4B5FF2D1-1B38-4D57-AD77-2C1B195ED02A"
    # Materialize a Text action so If resolves a string operand during import.
    # Raw Shortcut Input has no concrete content type when the editor validates it.
    actions = [{"WFWorkflowActionIdentifier":"is.workflow.actions.gettext",
                "WFWorkflowActionParameters":{
                    "UUID":text_id,
                    "WFTextActionText":{
                        "Value":{"string":"\uFFFC", "attachmentsByRange":{
                            "{0, 1}":{"Type":"ExtensionInput"}}},
                        "WFSerializationType":"WFTextTokenString"}}}]

    for mode in ("on", "off"):
        group = str(uuid.uuid5(uuid.NAMESPACE_URL, "https://vpn.tolf.is/controller/" + mode)).upper()
        actions.extend([
            {"WFWorkflowActionIdentifier":"is.workflow.actions.conditional",
             "WFWorkflowActionParameters":{
                 "GroupingIdentifier":group, "WFControlFlowMode":0,
                 "WFInput":{"Type":"Variable", "Variable":{
                     "Value":{"Type":"ActionOutput", "OutputUUID":text_id, "OutputName":"Text",
                              "Aggrandizements":[{"Type":"WFCoercionVariableAggrandizement",
                                                 "CoercionItemClass":"WFStringContentItem"}]},
                     "WFSerializationType":"WFTextTokenAttachment"}},
                 "WFCondition":4, "WFConditionalActionString":mode}},
            workflow(name, mode)["WFWorkflowActions"][0],
            {"WFWorkflowActionIdentifier":"is.workflow.actions.conditional",
             "WFWorkflowActionParameters":{"GroupingIdentifier":group, "WFControlFlowMode":2}}
        ])
    # Nest both recognized values; all other input reaches the menu.
    text_action, on_if, on_action, on_end, off_if, off_action, off_end = actions
    def otherwise(begin):
        return {"WFWorkflowActionIdentifier":"is.workflow.actions.conditional",
                "WFWorkflowActionParameters":{
                    "GroupingIdentifier":begin["WFWorkflowActionParameters"]["GroupingIdentifier"],
                    "WFControlFlowMode":1}}
    actions = [text_action, on_if, on_action, otherwise(on_if),
               off_if, off_action, otherwise(off_if)]
    menu_group = "30F28665-D168-4D0E-9E7A-349B067D39C9"
    actions.append({
        "WFWorkflowActionIdentifier":"is.workflow.actions.choosefrommenu",
        "WFWorkflowActionParameters":{
            "GroupingIdentifier":menu_group, "WFControlFlowMode":0,
            "WFMenuPrompt":"Управление VPN",
            "WFMenuItems":[
                {"WFItemType":0, "WFValue":"Включить VPN"},
                {"WFItemType":0, "WFValue":"Выключить VPN"}]}})
    for mode, title in (("on", "Включить VPN"), ("off", "Выключить VPN")):
        actions.append({
            "WFWorkflowActionIdentifier":"is.workflow.actions.choosefrommenu",
            "WFWorkflowActionParameters":{
                "GroupingIdentifier":menu_group, "WFControlFlowMode":1,
                "WFMenuItemTitle":title, "WFMenuItemAttributedTitle":title}})
        actions.append(workflow(name, mode)["WFWorkflowActions"][0])
    actions.extend([
        {"WFWorkflowActionIdentifier":"is.workflow.actions.choosefrommenu",
         "WFWorkflowActionParameters":{"GroupingIdentifier":menu_group, "WFControlFlowMode":2}},
        off_end, on_end
    ])
    # Diagnostic build: remain in Shortcuts to distinguish a crash from Home Screen navigation.
    doc["WFWorkflowActions"] = actions
    return doc

if __name__ == "__main__":
    doc = controller("TOLF Москва iPhone")
    raw = plistlib.dumps(doc, fmt=plistlib.FMT_XML, sort_keys=False)
    target = Path(__file__).parent / "auto-install"
    (target / "TOLF.plist").write_bytes(raw)
    (target / "TOLF.shortcut").write_bytes(sign(raw, "TOLF"))
    print("Signed controller TOLF")
