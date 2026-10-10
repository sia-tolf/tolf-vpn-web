"""Portable shortcuts must never ship the author's device-local VPN binding."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('public_builder', Path(__file__).with_name('build-public.py'))
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class PortableShortcuts(unittest.TestCase):
    def test_portable_setup_clears_both_bindings_and_keeps_safe_operations(self):
        binding = {'title':'PRIVATE VPN NAME', 'identifier':'PRIVATE DEVICE ID',
                   'appDescriptor':{'BundleIdentifier':'com.cisco.anyconnect', 'Name':'AnyConnect'}}
        source = {'WFWorkflowIcon':{'WFWorkflowIconStartColor':3031607807, 'WFWorkflowIconGlyphNumber':59760},
                  'WFWorkflowImportQuestions':[], 'WFWorkflowActions':[
            {'WFWorkflowActionIdentifier':'is.workflow.actions.vpn.set', 'WFWorkflowActionParameters':{'WFVPN':binding, 'WFVPNOperation':'Set On Demand', 'UUID':'PRIVATE ACTION ID'}},
            {'WFWorkflowActionIdentifier':'is.workflow.actions.vpn.set', 'WFWorkflowActionParameters':{'WFVPN':binding, 'UUID':'PRIVATE ACTION ID'}}]}
        for on in (True, False):
            workflow = builder.make_public(source, on)
            self.assertNotIn('PRIVATE', repr(workflow))
            self.assertEqual(workflow['WFWorkflowName'], 'TOLF ON' if on else 'TOLF OFF')
            actions = workflow['WFWorkflowActions']
            self.assertEqual(actions[0]['WFWorkflowActionParameters']['WFVPNOperation'], 'Set On Demand')
            self.assertEqual(actions[0]['WFWorkflowActionParameters'].get('WFOnDemandValue', True), on)
            self.assertEqual(actions[1]['WFWorkflowActionParameters'].get('WFVPNOperation', 'Connect'), 'Connect' if on else 'Disconnect')
            self.assertEqual(actions[2]['WFWorkflowActionIdentifier'], 'is.workflow.actions.returntohomescreen')
            self.assertEqual([q['ActionIndex'] for q in workflow['WFWorkflowImportQuestions']], [0, 1])
            for q in workflow['WFWorkflowImportQuestions']:
                self.assertEqual(q['ParameterKey'], 'WFVPN')
                self.assertNotIn('DefaultValue', q)


if __name__ == '__main__':
    unittest.main()
