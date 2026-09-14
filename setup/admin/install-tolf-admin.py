#!/usr/bin/env python3
"""Install the read-only TOLF admin inventory on London; grant roles only as root."""
import argparse
import ast
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tempfile
import time
import urllib.request
import fcntl

PAYLOAD = 'IiIiQWRtaW4gaW52ZW50b3J5LiBWUE4gbm9kZSBzdGF0ZSBpcyBuZXZlciBpbmZlcnJlZCBmcm9tIHRoZSBhY2NvdW50IGRhdGFiYXNlLiIiIgppbXBvcnQganNvbgppbXBvcnQgc3FsaXRlMwppbXBvcnQgdXVpZApmcm9tIGNvbnRleHRsaWIgaW1wb3J0IGNvbnRleHRtYW5hZ2VyCmZyb20gZGF0ZXRpbWUgaW1wb3J0IGRhdGV0aW1lLCB0aW1lem9uZQoKVkVSU0lPTiA9ICcxLjAuMCcKSEVBREVSUyA9IHsnQ2FjaGUtQ29udHJvbCc6ICdwcml2YXRlLCBuby1zdG9yZSwgbWF4LWFnZT0wJywgJ1gtQ29udGVudC1UeXBlLU9wdGlvbnMnOiAnbm9zbmlmZid9CkNUWCA9IHt9CgpAY29udGV4dG1hbmFnZXIKZGVmIGRiKCk6CiAgICBjb24gPSBzcWxpdGUzLmNvbm5lY3QoQ1RYWydEQiddLCB0aW1lb3V0PTE1KQogICAgY29uLnJvd19mYWN0b3J5ID0gc3FsaXRlMy5Sb3cKICAgIHRyeToKICAgICAgICB3aXRoIGNvbjoKICAgICAgICAgICAgeWllbGQgY29uCiAgICBmaW5hbGx5OgogICAgICAgIGNvbi5jbG9zZSgpCgoKZGVmIGluaXRpYWxpemUocGF0aCk6CiAgICB3aXRoIHNxbGl0ZTMuY29ubmVjdChwYXRoLCB0aW1lb3V0PTE1KSBhcyBjb246CiAgICAgICAgY29uLmV4ZWN1dGUoJ0NSRUFURSBUQUJMRSBJRiBOT1QgRVhJU1RTIGFkbWluX3JvbGVzICh1c2VyX2lkIFRFWFQgUFJJTUFSWSBLRVksIGdyYW50ZWRfYXQgVEVYVCBOT1QgTlVMTCwgZ3JhbnRlZF9ieSBURVhUIE5PVCBOVUxMKScpCiAgICAgICAgY29uLmV4ZWN1dGUoJ0NSRUFURSBUQUJMRSBJRiBOT1QgRVhJU1RTIGFkbWluX2F1ZGl0IChpZCBJTlRFR0VSIFBSSU1BUlkgS0VZIEFVVE9JTkNSRU1FTlQsIGFjdG9yIFRFWFQgTk9UIE5VTEwsIGFjdGlvbiBURVhUIE5PVCBOVUxMLCB0YXJnZXQgVEVYVCBOT1QgTlVMTCwgY3JlYXRlZF9hdCBURVhUIE5PVCBOVUxMKScpCgoKZGVmIHJvb3RfZ3JhbnQocGF0aCwgbnVtYmVyKToKICAgICMgQ2FsbGVkIG9ubHkgYnkgdGhlIHJvb3Qtb25seSBpbnN0YWxsYXRpb24gdXRpbGl0eSwgbmV2ZXIgYnkgYW4gSFRUUCByb3V0ZS4KICAgIGluaXRpYWxpemUocGF0aCkKICAgIHdpdGggc3FsaXRlMy5jb25uZWN0KHBhdGgsIHRpbWVvdXQ9MTUpIGFzIGNvbjoKICAgICAgICBjb24uZXhlY3V0ZSgnQkVHSU4gSU1NRURJQVRFJykKICAgICAgICByb3dzID0gY29uLmV4ZWN1dGUoJ1NFTEVDVCBESVNUSU5DVCB1LmlkIEZST00gbWFuYWdlZF91c2VycyBtIEpPSU4gdXNlcnMgdSBPTiB1LmlkPW0uYWNjb3VudF9pZCBXSEVSRSBtLm51bWJlcj0/IEFORCBtLmRlbGV0ZWRfYXQgSVMgTlVMTCcsIChudW1iZXIsKSkuZmV0Y2hhbGwoKQogICAgICAgIGlmIGxlbihyb3dzKSAhPSAxOgogICAgICAgICAgICByYWlzZSBWYWx1ZUVycm9yKCdOdW1iZXIgbXVzdCBpZGVudGlmeSBleGFjdGx5IG9uZSBleGlzdGluZyBhY2NvdW50JykKICAgICAgICB1c2VyX2lkID0gcm93c1swXVswXQogICAgICAgIHN0YW1wID0gZGF0ZXRpbWUubm93KHRpbWV6b25lLnV0YykuaXNvZm9ybWF0KCkKICAgICAgICBpZiBub3QgY29uLmV4ZWN1dGUoJ1NFTEVDVCAxIEZST00gYWRtaW5fcm9sZXMgV0hFUkUgdXNlcl9pZD0/JywgKHVzZXJfaWQsKSkuZmV0Y2hvbmUoKToKICAgICAgICAgICAgY29uLmV4ZWN1dGUoJ0lOU0VSVCBJTlRPIGFkbWluX3JvbGVzIFZBTFVFUyAoPyw/LD8pJywgKHVzZXJfaWQsc3RhbXAsJ3Jvb3QnKSkKICAgICAgICAgICAgY29uLmV4ZWN1dGUoJ0lOU0VSVCBJTlRPIGFkbWluX2F1ZGl0KGFjdG9yLGFjdGlvbix0YXJnZXQsY3JlYXRlZF9hdCkgVkFMVUVTICg/LD8sPyw/KScsICgncm9vdCcsJ2FkbWluLmdyYW50Jyx1c2VyX2lkLHN0YW1wKSkKICAgICAgICByZXR1cm4gdXNlcl9pZAoKCmRlZiByb290X3Jldm9rZShwYXRoLCBudW1iZXIpOgogICAgaW5pdGlhbGl6ZShwYXRoKQogICAgd2l0aCBzcWxpdGUzLmNvbm5lY3QocGF0aCwgdGltZW91dD0xNSkgYXMgY29uOgogICAgICAgIGNvbi5leGVjdXRlKCdCRUdJTiBJTU1FRElBVEUnKQogICAgICAgIHJvd3MgPSBjb24uZXhlY3V0ZSgnU0VMRUNUIERJU1RJTkNUIGFjY291bnRfaWQgRlJPTSBtYW5hZ2VkX3VzZXJzIFdIRVJFIG51bWJlcj0/JywgKG51bWJlciwpKS5mZXRjaGFsbCgpCiAgICAgICAgaWYgbGVuKHJvd3MpICE9IDEgb3Igbm90IHJvd3NbMF1bMF06CiAgICAgICAgICAgIHJhaXNlIFZhbHVlRXJyb3IoJ051bWJlciBtdXN0IGlkZW50aWZ5IGV4YWN0bHkgb25lIGFjY291bnQnKQogICAgICAgIHVzZXJfaWQgPSByb3dzWzBdWzBdCiAgICAgICAgaWYgY29uLmV4ZWN1dGUoJ0RFTEVURSBGUk9NIGFkbWluX3JvbGVzIFdIRVJFIHVzZXJfaWQ9PycsICh1c2VyX2lkLCkpLnJvd2NvdW50OgogICAgICAgICAgICBjb24uZXhlY3V0ZSgnSU5TRVJUIElOVE8gYWRtaW5fYXVkaXQoYWN0b3IsYWN0aW9uLHRhcmdldCxjcmVhdGVkX2F0KSBWQUxVRVMgKD8sPyw/LD8pJywgKCdyb290JywnYWRtaW4ucmV2b2tlJyx1c2VyX2lkLGRhdGV0aW1lLm5vdyh0aW1lem9uZS51dGMpLmlzb2Zvcm1hdCgpKSkKICAgICAgICByZXR1cm4gdXNlcl9pZAoKCmRlZiBpZGVudGl0eShyZXF1ZXN0KToKICAgIHVzZXJfaWQgPSBDVFhbJ2F1dGhlbnRpY2F0ZWRfdXNlcl9pZCddKHJlcXVlc3QpCiAgICB3aXRoIGRiKCkgYXMgY29uOgogICAgICAgIGlmIG5vdCBjb24uZXhlY3V0ZSgnU0VMRUNUIDEgRlJPTSB1c2VycyBXSEVSRSBpZD0/JywgKHVzZXJfaWQsKSkuZmV0Y2hvbmUoKToKICAgICAgICAgICAgcmFpc2UgSFRUUEV4Y2VwdGlvbig0MDEsICdhdXRoZW50aWNhdGlvbl9yZXF1aXJlZCcpCiAgICByZXR1cm4gdXNlcl9pZAoKCmRlZiByZXF1aXJlX2FkbWluKHJlcXVlc3QpOgogICAgdXNlcl9pZCA9IGlkZW50aXR5KHJlcXVlc3QpCiAgICB3aXRoIGRiKCkgYXMgY29uOgogICAgICAgIGlmIG5vdCBjb24uZXhlY3V0ZSgnU0VMRUNUIDEgRlJPTSBhZG1pbl9yb2xlcyBXSEVSRSB1c2VyX2lkPT8nLCAodXNlcl9pZCwpKS5mZXRjaG9uZSgpOgogICAgICAgICAgICByYWlzZSBIVFRQRXhjZXB0aW9uKDQwMywgJ2FkbWluaXN0cmF0b3JfcmVxdWlyZWQnKQogICAgcmV0dXJuIHVzZXJfaWQKCgpkZWYgcmVzcG9uc2UoZGF0YSk6CiAgICByZXR1cm4gSlNPTlJlc3BvbnNlKGRhdGEsIGhlYWRlcnM9SEVBREVSUykKCgpkZWYgdXNlcl9yZWNvcmQoY29uLCByb3cpOgogICAgdXNlcl9pZCA9IHJvd1snaWQnXQogICAgbnVtYmVyID0gY29uLmV4ZWN1dGUoJ1NFTEVDVCBNSU4obnVtYmVyKSBGUk9NIG1hbmFnZWRfdXNlcnMgV0hFUkUgYWNjb3VudF9pZD0/IEFORCBkZWxldGVkX2F0IElTIE5VTEwnLCAodXNlcl9pZCwpKS5mZXRjaG9uZSgpWzBdCiAgICBhY2Nlc3MgPSBbZGljdChyKSBmb3IgciBpbiBjb24uZXhlY3V0ZSgnU0VMRUNUIHZwbl91c2VybmFtZSBBUyB1c2VybmFtZSwgc2VydmVyLCBjcmVhdGVkX2F0IEFTIGNyZWF0ZWRBdCBGUk9NIHZwbl9hY2Nlc3MgV0hFUkUgdXNlcl9pZD0/JywgKHVzZXJfaWQsKSldCiAgICByZXR1cm4geydpZCc6IHVzZXJfaWQsICdudW1iZXInOiBudW1iZXIsICdjcmVhdGVkQXQnOiByb3dbJ2NyZWF0ZWRfYXQnXSwgJ2FjY2Vzcyc6IGFjY2VzcywKICAgICAgICAgICAgJ3Bhc3NrZXlzJzogY29uLmV4ZWN1dGUoJ1NFTEVDVCBjb3VudCgqKSBGUk9NIHBhc3NrZXlzIFdIRVJFIHVzZXJfaWQ9PycsICh1c2VyX2lkLCkpLmZldGNob25lKClbMF0sCiAgICAgICAgICAgICd3aW5kb3dzRGV2aWNlcyc6IGNvbi5leGVjdXRlKCJTRUxFQ1QgY291bnQoKikgRlJPTSB3aW5kb3dzX2RldmljZXMgV0hFUkUgdXNlcl9pZD0/IEFORCBzdGF0ZSE9J2RlbGV0ZWQnIiwgKHVzZXJfaWQsKSkuZmV0Y2hvbmUoKVswXSwKICAgICAgICAgICAgJ2lzQWRtaW4nOiBib29sKGNvbi5leGVjdXRlKCdTRUxFQ1QgMSBGUk9NIGFkbWluX3JvbGVzIFdIRVJFIHVzZXJfaWQ9PycsICh1c2VyX2lkLCkpLmZldGNob25lKCkpLAogICAgICAgICAgICAncHJvdGVjdGVkJzogYm9vbChjb24uZXhlY3V0ZSgnU0VMRUNUIDEgRlJPTSB2cG5faW1wb3J0cyBXSEVSRSB1c2VyX2lkPT8gQU5EIHByb3RlY3RlZD0xJywgKHVzZXJfaWQsKSkuZmV0Y2hvbmUoKSl9CgoKZGVmIGluc3RhbGwoYXBwLCBjb250ZXh0KToKICAgIGdsb2JhbCBDVFgsIEhUVFBFeGNlcHRpb24sIEpTT05SZXNwb25zZQogICAgZnJvbSBmYXN0YXBpIGltcG9ydCBIVFRQRXhjZXB0aW9uLCBSZXF1ZXN0CiAgICBmcm9tIGZhc3RhcGkucmVzcG9uc2VzIGltcG9ydCBKU09OUmVzcG9uc2UKICAgIENUWCA9IGNvbnRleHQKICAgIGluaXRpYWxpemUoQ1RYWydEQiddKQoKICAgIEBhcHAuZ2V0KCcvYWRtaW4vY2FwYWJpbGl0aWVzJykKICAgIGRlZiBjYXBhYmlsaXRpZXMoKToKICAgICAgICByZXR1cm4gcmVzcG9uc2Uoeyd2ZXJzaW9uJzogVkVSU0lPTiwgJ2ludmVudG9yeSc6IFRydWUsICdzZXNzaW9ucyc6IEZhbHNlLCAnZGlzY29ubmVjdCc6IEZhbHNlLCAnc3VzcGVuZCc6IEZhbHNlfSkKCiAgICBAYXBwLmdldCgnL2FkbWluL21lJykKICAgIGRlZiBtZShyZXF1ZXN0OiBSZXF1ZXN0KToKICAgICAgICB1c2VyX2lkID0gaWRlbnRpdHkocmVxdWVzdCkKICAgICAgICB3aXRoIGRiKCkgYXMgY29uOgogICAgICAgICAgICBudW1iZXIgPSBjb24uZXhlY3V0ZSgnU0VMRUNUIE1JTihudW1iZXIpIEZST00gbWFuYWdlZF91c2VycyBXSEVSRSBhY2NvdW50X2lkPT8gQU5EIGRlbGV0ZWRfYXQgSVMgTlVMTCcsICh1c2VyX2lkLCkpLmZldGNob25lKClbMF0KICAgICAgICAgICAgYWxsb3dlZCA9IGJvb2woY29uLmV4ZWN1dGUoJ1NFTEVDVCAxIEZST00gYWRtaW5fcm9sZXMgV0hFUkUgdXNlcl9pZD0/JywgKHVzZXJfaWQsKSkuZmV0Y2hvbmUoKSkKICAgICAgICByZXR1cm4gcmVzcG9uc2Uoeydpc0FkbWluJzogYWxsb3dlZCwgJ251bWJlcic6IG51bWJlcn0pCgogICAgQGFwcC5nZXQoJy9hZG1pbi91c2VycycpCiAgICBkZWYgdXNlcnMocmVxdWVzdDogUmVxdWVzdCwgcTogc3RyID0gJycsIG9mZnNldDogaW50ID0gMCwgbGltaXQ6IGludCA9IDUwKToKICAgICAgICByZXF1aXJlX2FkbWluKHJlcXVlc3QpCiAgICAgICAgaWYgb2Zmc2V0IDwgMCBvciBub3QgMSA8PSBsaW1pdCA8PSAxMDAgb3IgbGVuKHEpID4gMTI4OgogICAgICAgICAgICByYWlzZSBIVFRQRXhjZXB0aW9uKDQwMCwgJ2ludmFsaWRfcXVlcnknKQogICAgICAgIHEgPSBxLnN0cmlwKCkKICAgICAgICAjIGluc3RyIHNlYXJjaGVzIGxpdGVyYWxseTogJSwgXyBhbmQgU1FMLWxvb2tpbmcgaW5wdXQgaGF2ZSBubyBzcGVjaWFsIG1lYW5pbmcuCiAgICAgICAgd2hlcmUgPSAnJydXSEVSRSAoPz0nJyBPUiBpbnN0cihsb3dlcih1LmlkKSxsb3dlcig/KSk+MAogICAgICAgICAgICBPUiBFWElTVFMoU0VMRUNUIDEgRlJPTSBtYW5hZ2VkX3VzZXJzIG0gV0hFUkUgbS5hY2NvdW50X2lkPXUuaWQgQU5EIChDQVNUKG0ubnVtYmVyIEFTIFRFWFQpPT8gT1IgaW5zdHIobG93ZXIoQ09BTEVTQ0UobS52cG5fdXNlcm5hbWUsJycpKSxsb3dlcig/KSk+MCkpCiAgICAgICAgICAgIE9SIEVYSVNUUyhTRUxFQ1QgMSBGUk9NIHdpbmRvd3NfZGV2aWNlcyB3IFdIRVJFIHcudXNlcl9pZD11LmlkIEFORCB3LnN0YXRlIT0nZGVsZXRlZCcgQU5EIGluc3RyKGxvd2VyKHcubmFtZSksbG93ZXIoPykpPjApKScnJwogICAgICAgIGFyZ3MgPSAocSxxLHEscSxxKQogICAgICAgIHdpdGggZGIoKSBhcyBjb246CiAgICAgICAgICAgIHRvdGFsID0gY29uLmV4ZWN1dGUoJ1NFTEVDVCBjb3VudCgqKSBGUk9NIHVzZXJzIHUgJyt3aGVyZSxhcmdzKS5mZXRjaG9uZSgpWzBdCiAgICAgICAgICAgIHJvd3MgPSBjb24uZXhlY3V0ZSgnU0VMRUNUIHUuaWQsdS5jcmVhdGVkX2F0IEZST00gdXNlcnMgdSAnK3doZXJlKycgT1JERVIgQlkgdS5jcmVhdGVkX2F0IERFU0MsdS5pZCBMSU1JVCA/IE9GRlNFVCA/JywgYXJncysobGltaXQsb2Zmc2V0KSkuZmV0Y2hhbGwoKQogICAgICAgICAgICB2YWx1ZXMgPSBbdXNlcl9yZWNvcmQoY29uLHIpIGZvciByIGluIHJvd3NdCiAgICAgICAgcmV0dXJuIHJlc3BvbnNlKHsndXNlcnMnOnZhbHVlcywndG90YWwnOnRvdGFsLCdvZmZzZXQnOm9mZnNldCwnbGltaXQnOmxpbWl0LCdvYnNlcnZlZEF0JzpkYXRldGltZS5ub3codGltZXpvbmUudXRjKS5pc29mb3JtYXQoKSwnc291cmNlJzonYWNjb3VudF9kYXRhYmFzZSd9KQoKICAgIEBhcHAuZ2V0KCcvYWRtaW4vdXNlcnMve3VzZXJfaWR9JykKICAgIGRlZiBkZXRhaWxzKHVzZXJfaWQ6IHN0ciwgcmVxdWVzdDogUmVxdWVzdCk6CiAgICAgICAgcmVxdWlyZV9hZG1pbihyZXF1ZXN0KQogICAgICAgIHRyeToKICAgICAgICAgICAgdXNlcl9pZCA9IHN0cih1dWlkLlVVSUQodXNlcl9pZCkpCiAgICAgICAgZXhjZXB0IFZhbHVlRXJyb3I6CiAgICAgICAgICAgIHJhaXNlIEhUVFBFeGNlcHRpb24oNDAwLCAnaW52YWxpZF91c2VyX2lkJykKICAgICAgICB3aXRoIGRiKCkgYXMgY29uOgogICAgICAgICAgICByb3cgPSBjb24uZXhlY3V0ZSgnU0VMRUNUIGlkLGNyZWF0ZWRfYXQgRlJPTSB1c2VycyBXSEVSRSBpZD0/JywgKHVzZXJfaWQsKSkuZmV0Y2hvbmUoKQogICAgICAgICAgICBpZiBub3Qgcm93OgogICAgICAgICAgICAgICAgcmFpc2UgSFRUUEV4Y2VwdGlvbig0MDQsICd1c2VyX25vdF9mb3VuZCcpCiAgICAgICAgICAgIHJlc3VsdCA9IHVzZXJfcmVjb3JkKGNvbixyb3cpCiAgICAgICAgICAgIHJlc3VsdFsnZGV2aWNlcyddID0gW2RpY3QocikgZm9yIHIgaW4gY29uLmV4ZWN1dGUoIlNFTEVDVCB3LmlkLHcubmFtZSx3LnVzZXJuYW1lLHcuc3RhdGUsdy5jcmVhdGVkX2F0IEFTIGNyZWF0ZWRBdCxDT0FMRVNDRShuLnNlcnZlciwncmlnYScpIEFTIHNlcnZlciBGUk9NIHdpbmRvd3NfZGV2aWNlcyB3IExFRlQgSk9JTiB3aW5kb3dzX2RldmljZV9ub2RlcyBuIE9OIG4uZGV2aWNlX2lkPXcuaWQgV0hFUkUgdy51c2VyX2lkPT8gQU5EIHcuc3RhdGUhPSdkZWxldGVkJyBPUkRFUiBCWSB3LmNyZWF0ZWRfYXQsdy5pZCIsKHVzZXJfaWQsKSldCiAgICAgICAgICAgIHJlc3VsdFsncGFzc2tleU5hbWVzJ10gPSBbclswXSBvciAnJyBmb3IgciBpbiBjb24uZXhlY3V0ZSgnU0VMRUNUIG5hbWUgRlJPTSBwYXNza2V5cyBXSEVSRSB1c2VyX2lkPT8gT1JERVIgQlkgY3JlYXRlZF9hdCcsKHVzZXJfaWQsKSldCiAgICAgICAgcmV0dXJuIHJlc3BvbnNlKHJlc3VsdCkKCiAgICBAYXBwLmdldCgnL2FkbWluL3JlZ2lzdHJ5JykKICAgIGRlZiByZWdpc3RyeShyZXF1ZXN0OiBSZXF1ZXN0LCBvZmZzZXQ6IGludCA9IDAsIGxpbWl0OiBpbnQgPSA1MCk6CiAgICAgICAgcmVxdWlyZV9hZG1pbihyZXF1ZXN0KQogICAgICAgIGlmIG9mZnNldCA8IDAgb3Igbm90IDEgPD0gbGltaXQgPD0gMTAwOgogICAgICAgICAgICByYWlzZSBIVFRQRXhjZXB0aW9uKDQwMCwgJ2ludmFsaWRfcXVlcnknKQogICAgICAgIHdpdGggZGIoKSBhcyBjb246CiAgICAgICAgICAgIHRvdGFsID0gY29uLmV4ZWN1dGUoJ1NFTEVDVCBjb3VudCgqKSBGUk9NIG1hbmFnZWRfdXNlcnMgV0hFUkUgZGVsZXRlZF9hdCBJUyBOVUxMJykuZmV0Y2hvbmUoKVswXQogICAgICAgICAgICByb3dzID0gY29uLmV4ZWN1dGUoJ1NFTEVDVCBudW1iZXIsYWNjb3VudF9pZCBBUyBhY2NvdW50SWQsdnBuX3VzZXJuYW1lIEFTIHVzZXJuYW1lLGNyZWF0ZWRfYXQgQVMgY3JlYXRlZEF0LHNvdXJjZSx2cG5fYWN0aXZlIEFTIHByb3Zpc2lvbmVkIEZST00gbWFuYWdlZF91c2VycyBXSEVSRSBkZWxldGVkX2F0IElTIE5VTEwgT1JERVIgQlkgbnVtYmVyIExJTUlUID8gT0ZGU0VUID8nLCAobGltaXQsb2Zmc2V0KSkuZmV0Y2hhbGwoKQogICAgICAgIHJldHVybiByZXNwb25zZSh7J3JlY29yZHMnOltkaWN0KHIpIGZvciByIGluIHJvd3NdLCd0b3RhbCc6dG90YWwsJ29mZnNldCc6b2Zmc2V0LCdsaW1pdCc6bGltaXQsJ3NvdXJjZSc6J2FjY291bnRfZGF0YWJhc2UnfSkKCiAgICBAYXBwLmdldCgnL2FkbWluL2F1ZGl0JykKICAgIGRlZiBhdWRpdChyZXF1ZXN0OiBSZXF1ZXN0KToKICAgICAgICByZXF1aXJlX2FkbWluKHJlcXVlc3QpCiAgICAgICAgd2l0aCBkYigpIGFzIGNvbjoKICAgICAgICAgICAgcm93cyA9IGNvbi5leGVjdXRlKCdTRUxFQ1QgYWN0b3IsYWN0aW9uLHRhcmdldCxjcmVhdGVkX2F0IEFTIGNyZWF0ZWRBdCBGUk9NIGFkbWluX2F1ZGl0IE9SREVSIEJZIGlkIERFU0MgTElNSVQgMTAwJykuZmV0Y2hhbGwoKQogICAgICAgIHJldHVybiByZXNwb25zZSh7J2V2ZW50cyc6W2RpY3QocikgZm9yIHIgaW4gcm93c119KQo='
PAYLOAD_SHA256 = '900c797135ae49bf34058740bbaf2b8462442c007e913f8230f86222cfddb99c'
ROOT = Path('/opt/tolf-api')
DB = '/var/lib/tolf-api/tolf.db'
MARKER = '# TOLF admin inventory v1'


def patch(source):
    tree = ast.parse(source)
    names = {n.name for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
    if 'authenticated_user_id' not in names:
        raise RuntimeError('Expected authentication function is missing; nothing changed')
    if MARKER in source:
        if 'tolf_admin.install(app, globals())' not in source:
            raise RuntimeError('Admin integration differs; nothing changed')
        return source
    addition = '\n'+MARKER+'\nimport tolf_admin\ntolf_admin.install(app, globals())\n'
    lines = source.splitlines(keepends=True)
    for node in tree.body:
        if isinstance(node,ast.If) and '__name__' in ast.unparse(node.test) and '__main__' in ast.unparse(node.test):
            index = node.lineno-1
            return ''.join(lines[:index])+addition+'\n'+''.join(lines[index:])
    return source.rstrip()+'\n'+addition


def module():
    spec = importlib.util.spec_from_file_location('tolf_admin_installer',ROOT/'tolf_admin.py')
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def inventory():
    with sqlite3.connect('file:'+DB+'?mode=ro',uri=True) as con:
        rows = con.execute('SELECT m.number,m.vpn_username,u.id FROM managed_users m JOIN users u ON u.id=m.account_id WHERE m.deleted_at IS NULL ORDER BY m.number').fetchall()
        for number,username,user_id in rows:
            names = [r[0] for r in con.execute('SELECT name FROM passkeys WHERE user_id=? ORDER BY created_at',(user_id,)) if r[0]]
            # JSON escaping prevents control characters in user labels affecting the terminal.
            print(json.dumps({'number':number,'vpn':username,'passkeys':names},ensure_ascii=True))
        return rows


def atomic(path,data,info):
    fd,temp = tempfile.mkstemp(prefix='.'+path.name+'-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as f:
            f.write(data);f.flush();os.fsync(f.fileno())
        os.chown(temp,info.st_uid,info.st_gid);os.chmod(temp,info.st_mode & 0o777)
        os.replace(temp,path)
    finally:
        Path(temp).unlink(missing_ok=True)


def install():
    path=ROOT/'main.py';target=ROOT/'tolf_admin.py'
    source=path.read_text();original=path.read_bytes();updated=patch(source)
    data=base64.b64decode(PAYLOAD)
    if hashlib.sha256(data).hexdigest()!=PAYLOAD_SHA256:
        raise RuntimeError('Admin payload checksum mismatch')
    compile(data,str(target),'exec');compile(updated,str(path),'exec')
    with sqlite3.connect('file:'+DB+'?mode=ro',uri=True) as con:
        required={'users':{'id','created_at'},'managed_users':{'number','account_id','vpn_username','created_at','source','vpn_active','deleted_at'},'vpn_access':{'user_id','vpn_username','created_at','server'},'passkeys':{'user_id','name','created_at'},'vpn_imports':{'user_id','protected'},'windows_devices':{'id','user_id','name','username','state','created_at'},'windows_device_nodes':{'device_id','server'}}
        for table,columns in required.items():
            actual={r[1] for r in con.execute('PRAGMA table_info('+table+')')}
            if not columns.issubset(actual):raise RuntimeError('Unsupported database schema: '+table)
    backup=Path('/root/tolf-admin-backup-'+time.strftime('%Y%m%d-%H%M%S')+'-'+str(os.getpid()));backup.mkdir(mode=0o700)
    shutil.copy2(path,backup/'main.py')
    if target.exists():shutil.copy2(target,backup/'tolf_admin.py')
    info=path.stat()
    print('Backup:',backup,flush=True)
    if path.read_bytes()!=original:raise RuntimeError('API source changed during preparation; nothing changed')
    try:
        atomic(target,data,info);atomic(path,updated.encode(),info)
        subprocess.run(['systemctl','restart','tolf-api.service'],check=True)
        for _ in range(12):
            try:
                with urllib.request.urlopen('https://api.tolf.is/admin/capabilities',timeout=5) as r:status=json.load(r)
                if status.get('version')=='1.0.0' and status.get('inventory') is True:
                    print('OK: TOLF admin inventory API enabled. VPN sessions and credentials were not changed.',flush=True)
                    return
            except Exception:pass
            time.sleep(1)
        raise RuntimeError('Admin API did not pass its availability check')
    except Exception:
        atomic(path,(backup/'main.py').read_bytes(),info)
        if (backup/'tolf_admin.py').exists():atomic(target,(backup/'tolf_admin.py').read_bytes(),info)
        else:target.unlink(missing_ok=True)
        subprocess.run(['systemctl','restart','tolf-api.service'],check=False)
        print('Previous API files restored; backup:',backup)
        raise


def main():
    parser=argparse.ArgumentParser()
    group=parser.add_mutually_exclusive_group()
    group.add_argument('--grant-number',type=int)
    group.add_argument('--revoke-number',type=int)
    group.add_argument('--list-accounts',action='store_true')
    args=parser.parse_args()
    if os.geteuid()!=0 or not (ROOT/'main.py').is_file():raise SystemExit('Run as root on London EDISUK')
    import sys
    with open('/run/lock/tolf-admin-install.lock','w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        if args.list_accounts:inventory();return
        if args.grant_number is not None:
            value=module().root_grant(DB,args.grant_number);print('Administrator granted to account:',args.grant_number,value);return
        if args.revoke_number is not None:
            value=module().root_revoke(DB,args.revoke_number);print('Administrator revoked:',args.revoke_number,value);return
        install()
        with sqlite3.connect(DB) as con:
            has_admin=con.execute('SELECT 1 FROM admin_roles a JOIN users u ON u.id=a.user_id LIMIT 1').fetchone()
        if not has_admin and sys.stdin.isatty():
            print('\nSelect YOUR account using its number and Passkey names:')
            inventory()
            chosen=input('Administrator account number (Enter to skip): ').strip()
            if chosen:
                if not chosen.isdecimal():raise SystemExit('Not a number. API installed; no administrator assigned.')
                module().root_grant(DB,int(chosen));print('Administrator granted to account:',chosen)
        print('Open https://vpn.tolf.is/admin/ after signing in with your Passkey.')
        if not has_admin:print('You can also assign access later: python3 '+str(Path(__file__).resolve())+' --grant-number NUMBER')

if __name__=='__main__':main()
