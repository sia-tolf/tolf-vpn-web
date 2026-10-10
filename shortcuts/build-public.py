#!/usr/bin/env python3
"""Build a portable candidate; validate VPN picker import on iOS before release.

No device-local VPN identifiers or account data are distributed. Both native
VPN parameters are configured during Shortcuts setup. A name is not a VPN ID.
"""
import argparse
import importlib.util
import plistlib
from pathlib import Path
import urllib.request

spec = importlib.util.spec_from_file_location('native_builder', Path(__file__).with_name('build.py'))
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)


def make_public(source, on):
    workflow = native.make_shortcut(source, on, return_home=True)
    workflow['WFWorkflowName'] = 'TOLF ' + ('ON' if on else 'OFF')
    workflow['WFWorkflowImportQuestions'] = []
    for index, action in enumerate(workflow['WFWorkflowActions'][:2]):
        params = action['WFWorkflowActionParameters']
        action['WFWorkflowActionParameters'] = {
            k: v for k, v in params.items() if k in ('WFVPNOperation', 'WFOnDemandValue')
        }
        workflow['WFWorkflowImportQuestions'].append({
            'Category': 'Parameter', 'ParameterKey': 'WFVPN', 'ActionIndex': index,
            'Text': 'Выберите установленный VPN TOLF. В обоих вопросах выберите одно и то же подключение. / Select the installed TOLF VPN. Use the same connection for both questions.',
        })
    workflow['WFWorkflowIcon'] = {
        'WFWorkflowIconStartColor': 431817727 if on else 4282601983,
        'WFWorkflowIconGlyphNumber': source['WFWorkflowIcon']['WFWorkflowIconGlyphNumber'],
    }
    return workflow


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--sign', action='store_true', help='Send only the generic, unbound workflow to RoutineHub HubSign')
    args = parser.parse_args()
    source = plistlib.loads(args.source.read_bytes())
    args.output.mkdir(parents=True, exist_ok=True)
    for on in (True, False):
        workflow = make_public(source, on)
        data = plistlib.dumps(workflow, fmt=plistlib.FMT_XML, sort_keys=False)
        stem = 'TOLF-' + ('ON' if on else 'OFF')
        (args.output / (stem + '.plist')).write_bytes(data)
        if args.sign:
            import json
            request = urllib.request.Request('https://hubsign.routinehub.services/sign',
                data=json.dumps({'shortcutName': workflow['WFWorkflowName'], 'shortcut':data.decode()}).encode(),
                headers={'Content-Type':'application/json', 'User-Agent':'cherri/2.3.0'}, method='POST')
            with urllib.request.urlopen(request, timeout=40) as response:
                signed = response.read()
            if not signed.startswith(b'AEA1') or len(signed) < 2000:
                raise RuntimeError('Invalid signed shortcut response')
            (args.output / (stem + '.shortcut')).write_bytes(signed)
        print('Built generic candidate', stem)


if __name__ == '__main__':
    main()
