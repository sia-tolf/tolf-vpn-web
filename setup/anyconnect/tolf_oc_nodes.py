"""Multi-ingress operations; activated nodes share one UK device identity.

Activation is owned by the UK installer; nodes share the UK certificate identity.
"""
from fastapi import HTTPException


class Nodes:
    def __init__(self, nodes):
        if not nodes:
            raise ValueError('At least one activated ingress is required')
        self.nodes = dict(nodes)

    def health(self, fresh=False):
        results = {name: node.health(fresh=fresh)
                   for name, node in self.nodes.items()}
        return all(results.values())

    def set(self, username, mode, previous_mode=None):
        """Require all ACKs; compensate even a command with a lost reply.

        Creation callers retain pending state on errors; policy callers retain
        the previous stored mode. Reconciliation must reapply that stored state
        to every activated node if compensation also fails.
        """
        attempted = []
        try:
            for node in self.nodes.values():
                attempted.append(node)
                node.set(username, mode)
        except HTTPException:
            failures = False
            for node in reversed(attempted):
                try:
                    if previous_mode is None:
                        node.remove(username)
                    else:
                        node.set(username, previous_mode)
                except HTTPException:
                    failures = True
            raise HTTPException(503, 'Ingress synchronization pending' if failures
                                else 'Ingress update not completed') from None

    def revoke(self, username):
        """Attempt both CRL refresh and disconnect at every ingress.

        An unavailable node must not prevent revocation on reachable nodes.
        The UK tombstone remains pending until every action is acknowledged.
        """
        failures = []
        for name, node in self.nodes.items():
            for action in (node.sync_crl, lambda node=node: node.remove(username)):
                try:
                    action()
                except HTTPException:
                    failures.append(name)
        if failures:
            raise HTTPException(503, 'Ingress revocation pending')

    def sessions(self, username):
        states = {}
        for name, node in self.nodes.items():
            try:
                states[name] = {'connected': node.session(username), 'available': True}
            except HTTPException:
                states[name] = {'connected': None, 'available': False}
        return {'connected': any(state['connected'] is True for state in states.values()),
                'complete': all(state['available'] for state in states.values()),
                'nodes': states}
