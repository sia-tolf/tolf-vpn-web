"""Narrow installation edits for the existing API, preserving unrelated modules."""
from billing_wallet_patch import patch as billing_patch


def accounts_patch(source):
    if source.count("'trialPackageIssuance':False")!=3:raise ValueError('Unsupported accounts source')
    source=source.replace("'trialPackageIssuance':False", "'trialPackageIssuance':bool(self.ctx.get('trial_wallet'))",1)
    source=source.replace("'trialPackageIssuance':False", "'trialPackageIssuance':bool(context.get('trial_wallet'))")
    compile(source,'tolf_account_admin.py','exec')
    return source


def main_patch(source):
    anchor='tolf_account_admin.install(app, globals())\n'
    if source.count(anchor)!=1 or 'import tolf_trial_packages' in source:raise ValueError('Unsupported API source')
    source=source.replace(anchor,anchor+'\n# One-time explicit 1 GB trial and trial-first wallet.\nimport tolf_trial_packages\ntolf_trial_packages.install(app, globals())\n')
    compile(source,'main.py','exec')
    return source
