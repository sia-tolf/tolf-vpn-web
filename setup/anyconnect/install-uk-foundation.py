#!/usr/bin/env python3
"""Install UK AnyConnect foundation. Built with embedded, hash-checked modules."""
import ast
import base64
import hashlib
import json
import os
from pathlib import Path
import pwd
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

PAYLOAD = {'tolf_oc_certificates.py': {'sha256': '69e9d1129cd03e39bcf39cb4914da949543daf5791d657ed0846a635e0ab362e', 'data': 'IiIiQ2VydGlmaWNhdGUgYXV0aG9yaXR5IGZvciBwZXJzb25hbCBUT0xGIEFueUNvbm5lY3QgZGV2aWNlcyAoVUsgb25seSkuIiIiCmltcG9ydCBkYXRldGltZSBhcyBkdAppbXBvcnQgb3MKZnJvbSBwYXRobGliIGltcG9ydCBQYXRoCmltcG9ydCBzZWNyZXRzCmltcG9ydCBzaHV0aWwKaW1wb3J0IHRlbXBmaWxlCmltcG9ydCB1dWlkCgpmcm9tIGNyeXB0b2dyYXBoeSBpbXBvcnQgeDUwOQpmcm9tIGNyeXB0b2dyYXBoeS5oYXptYXQucHJpbWl0aXZlcyBpbXBvcnQgaGFzaGVzLCBzZXJpYWxpemF0aW9uCmZyb20gY3J5cHRvZ3JhcGh5Lmhhem1hdC5wcmltaXRpdmVzLmFzeW1tZXRyaWMgaW1wb3J0IHJzYQpmcm9tIGNyeXB0b2dyYXBoeS5oYXptYXQucHJpbWl0aXZlcy5zZXJpYWxpemF0aW9uIGltcG9ydCBwa2NzMTIKZnJvbSBjcnlwdG9ncmFwaHkueDUwOS5vaWQgaW1wb3J0IE5hbWVPSUQsIEV4dGVuZGVkS2V5VXNhZ2VPSUQKCgpkZWYgbm93KCk6CiAgICByZXR1cm4gZHQuZGF0ZXRpbWUubm93KGR0LnRpbWV6b25lLnV0YykKCgpkZWYgcHJpdmF0ZV93cml0ZShwYXRoLCBkYXRhKToKICAgIGZkID0gb3Mub3BlbihwYXRoLCBvcy5PX1dST05MWSB8IG9zLk9fQ1JFQVQgfCBvcy5PX0VYQ0wsIDBvNjAwKQogICAgd2l0aCBvcy5mZG9wZW4oZmQsICJ3YiIpIGFzIGhhbmRsZToKICAgICAgICBoYW5kbGUud3JpdGUoZGF0YSkKICAgICAgICBoYW5kbGUuZmx1c2goKQogICAgICAgIG9zLmZzeW5jKGhhbmRsZS5maWxlbm8oKSkKCgpkZWYgaW5pdGlhbGl6ZShkaXJlY3RvcnkpOgogICAgIiIiQ3JlYXRlIG9uY2U7IGFuIGluY29tcGxldGUgb3IgbWlzbWF0Y2hlZCBhdXRob3JpdHkgaXMgbmV2ZXIgcmVwbGFjZWQuIiIiCiAgICBkaXJlY3RvcnkgPSBQYXRoKGRpcmVjdG9yeSkKICAgIGlmIGRpcmVjdG9yeS5leGlzdHMoKToKICAgICAgICBhdXRob3JpdHkgPSBBdXRob3JpdHkoZGlyZWN0b3J5KQogICAgICAgIHJldHVybiBhdXRob3JpdHkuZmluZ2VycHJpbnQKICAgIGRpcmVjdG9yeS5wYXJlbnQubWtkaXIocGFyZW50cz1UcnVlLCBleGlzdF9vaz1UcnVlKQogICAgc3RhZ2luZyA9IFBhdGgodGVtcGZpbGUubWtkdGVtcChwcmVmaXg9Ii5vYy1jYS0iLCBkaXI9ZGlyZWN0b3J5LnBhcmVudCkpCiAgICB0cnk6CiAgICAgICAgcGFzc3dvcmQgPSBzZWNyZXRzLnRva2VuX2J5dGVzKDQ4KQogICAgICAgIGtleSA9IHJzYS5nZW5lcmF0ZV9wcml2YXRlX2tleShwdWJsaWNfZXhwb25lbnQ9NjU1MzcsIGtleV9zaXplPTMwNzIpCiAgICAgICAgc3ViamVjdCA9IHg1MDkuTmFtZShbCiAgICAgICAgICAgIHg1MDkuTmFtZUF0dHJpYnV0ZShOYW1lT0lELk9SR0FOSVpBVElPTl9OQU1FLCAiVE9MRiIpLAogICAgICAgICAgICB4NTA5Lk5hbWVBdHRyaWJ1dGUoTmFtZU9JRC5DT01NT05fTkFNRSwgIlRPTEYgQW55Q29ubmVjdCBEZXZpY2UgQ0EiKSwKICAgICAgICBdKQogICAgICAgIGNyZWF0ZWQgPSBub3coKQogICAgICAgIGNlcnQgPSAoeDUwOS5DZXJ0aWZpY2F0ZUJ1aWxkZXIoKS5zdWJqZWN0X25hbWUoc3ViamVjdCkuaXNzdWVyX25hbWUoc3ViamVjdCkKICAgICAgICAgICAgICAgIC5wdWJsaWNfa2V5KGtleS5wdWJsaWNfa2V5KCkpLnNlcmlhbF9udW1iZXIoeDUwOS5yYW5kb21fc2VyaWFsX251bWJlcigpKQogICAgICAgICAgICAgICAgLm5vdF92YWxpZF9iZWZvcmUoY3JlYXRlZCAtIGR0LnRpbWVkZWx0YShtaW51dGVzPTUpKQogICAgICAgICAgICAgICAgLm5vdF92YWxpZF9hZnRlcihjcmVhdGVkICsgZHQudGltZWRlbHRhKGRheXM9MzY1MCkpCiAgICAgICAgICAgICAgICAuYWRkX2V4dGVuc2lvbih4NTA5LkJhc2ljQ29uc3RyYWludHMoY2E9VHJ1ZSwgcGF0aF9sZW5ndGg9MCksIGNyaXRpY2FsPVRydWUpCiAgICAgICAgICAgICAgICAuYWRkX2V4dGVuc2lvbih4NTA5LktleVVzYWdlKAogICAgICAgICAgICAgICAgICAgIGRpZ2l0YWxfc2lnbmF0dXJlPVRydWUsIGNvbnRlbnRfY29tbWl0bWVudD1GYWxzZSwga2V5X2VuY2lwaGVybWVudD1GYWxzZSwKICAgICAgICAgICAgICAgICAgICBkYXRhX2VuY2lwaGVybWVudD1GYWxzZSwga2V5X2FncmVlbWVudD1GYWxzZSwga2V5X2NlcnRfc2lnbj1UcnVlLAogICAgICAgICAgICAgICAgICAgIGNybF9zaWduPVRydWUsIGVuY2lwaGVyX29ubHk9RmFsc2UsIGRlY2lwaGVyX29ubHk9RmFsc2UpLCBjcml0aWNhbD1UcnVlKQogICAgICAgICAgICAgICAgLmFkZF9leHRlbnNpb24oeDUwOS5TdWJqZWN0S2V5SWRlbnRpZmllci5mcm9tX3B1YmxpY19rZXkoa2V5LnB1YmxpY19rZXkoKSksIEZhbHNlKQogICAgICAgICAgICAgICAgLnNpZ24oa2V5LCBoYXNoZXMuU0hBMjU2KCkpKQogICAgICAgIHByaXZhdGVfd3JpdGUoc3RhZ2luZyAvICJrZXktcGFzc3dvcmQuYmluIiwgcGFzc3dvcmQpCiAgICAgICAgcHJpdmF0ZV93cml0ZShzdGFnaW5nIC8gImNhLWtleS5wZW0iLCBrZXkucHJpdmF0ZV9ieXRlcygKICAgICAgICAgICAgc2VyaWFsaXphdGlvbi5FbmNvZGluZy5QRU0sIHNlcmlhbGl6YXRpb24uUHJpdmF0ZUZvcm1hdC5QS0NTOCwKICAgICAgICAgICAgc2VyaWFsaXphdGlvbi5CZXN0QXZhaWxhYmxlRW5jcnlwdGlvbihwYXNzd29yZCkpKQogICAgICAgIHByaXZhdGVfd3JpdGUoc3RhZ2luZyAvICJjYS5wZW0iLCBjZXJ0LnB1YmxpY19ieXRlcyhzZXJpYWxpemF0aW9uLkVuY29kaW5nLlBFTSkpCiAgICAgICAgYXV0aG9yaXR5ID0gQXV0aG9yaXR5KHN0YWdpbmcpCiAgICAgICAgcHJpdmF0ZV93cml0ZShzdGFnaW5nIC8gImNhLmNybC5wZW0iLCBhdXRob3JpdHkuY3JsKFtdKSkKICAgICAgICAjIEEgY29uY3VycmVudCBpbml0aWFsaXplciBtdXN0IG5vdCByZXBsYWNlIGFuIGV4aXN0aW5nIENBLgogICAgICAgIG9zLnJlbmFtZShzdGFnaW5nLCBkaXJlY3RvcnkpCiAgICBleGNlcHQgRXhjZXB0aW9uOgogICAgICAgIGlmIHN0YWdpbmcuZXhpc3RzKCk6CiAgICAgICAgICAgIHNodXRpbC5ybXRyZWUoc3RhZ2luZykKICAgICAgICByYWlzZQogICAgcmV0dXJuIEF1dGhvcml0eShkaXJlY3RvcnkpLmZpbmdlcnByaW50CgoKY2xhc3MgQXV0aG9yaXR5OgogICAgZGVmIF9faW5pdF9fKHNlbGYsIGRpcmVjdG9yeSk6CiAgICAgICAgc2VsZi5kaXJlY3RvcnkgPSBQYXRoKGRpcmVjdG9yeSkKICAgICAgICBzZWxmLnBhc3N3b3JkID0gKHNlbGYuZGlyZWN0b3J5IC8gImtleS1wYXNzd29yZC5iaW4iKS5yZWFkX2J5dGVzKCkKICAgICAgICBzZWxmLmtleSA9IHNlcmlhbGl6YXRpb24ubG9hZF9wZW1fcHJpdmF0ZV9rZXkoCiAgICAgICAgICAgIChzZWxmLmRpcmVjdG9yeSAvICJjYS1rZXkucGVtIikucmVhZF9ieXRlcygpLCBzZWxmLnBhc3N3b3JkKQogICAgICAgIHNlbGYuY2VydCA9IHg1MDkubG9hZF9wZW1feDUwOV9jZXJ0aWZpY2F0ZSgoc2VsZi5kaXJlY3RvcnkgLyAiY2EucGVtIikucmVhZF9ieXRlcygpKQogICAgICAgIGlmIHNlbGYuY2VydC5wdWJsaWNfa2V5KCkucHVibGljX251bWJlcnMoKSAhPSBzZWxmLmtleS5wdWJsaWNfa2V5KCkucHVibGljX251bWJlcnMoKToKICAgICAgICAgICAgcmFpc2UgUnVudGltZUVycm9yKCJBbnlDb25uZWN0IENBIGtleSBkb2VzIG5vdCBtYXRjaCBpdHMgY2VydGlmaWNhdGUiKQogICAgICAgIGlmIG5vdCBzZWxmLmNlcnQuZXh0ZW5zaW9ucy5nZXRfZXh0ZW5zaW9uX2Zvcl9jbGFzcyh4NTA5LkJhc2ljQ29uc3RyYWludHMpLnZhbHVlLmNhOgogICAgICAgICAgICByYWlzZSBSdW50aW1lRXJyb3IoIkFueUNvbm5lY3QgYXV0aG9yaXR5IGlzIG5vdCBhIENBIikKICAgICAgICBpZiBzZWxmLmNlcnQubm90X3ZhbGlkX2FmdGVyX3V0YyA8PSBub3coKToKICAgICAgICAgICAgcmFpc2UgUnVudGltZUVycm9yKCJBbnlDb25uZWN0IENBIGV4cGlyZWQiKQoKICAgIEBwcm9wZXJ0eQogICAgZGVmIGZpbmdlcnByaW50KHNlbGYpOgogICAgICAgIHJldHVybiBzZWxmLmNlcnQuZmluZ2VycHJpbnQoaGFzaGVzLlNIQTI1NigpKS5oZXgoKQoKICAgIGRlZiBpc3N1ZShzZWxmLCBkZXZpY2VfaWQsIGRheXM9MzY1KToKICAgICAgICBkZXZpY2VfaWQgPSB1dWlkLlVVSUQoZGV2aWNlX2lkKS5oZXgKICAgICAgICBpZiBub3QgaXNpbnN0YW5jZShkYXlzLCBpbnQpIG9yIG5vdCAxIDw9IGRheXMgPD0gMzY1OgogICAgICAgICAgICByYWlzZSBWYWx1ZUVycm9yKCJJbnZhbGlkIGNlcnRpZmljYXRlIGxpZmV0aW1lIikKICAgICAgICBrZXkgPSByc2EuZ2VuZXJhdGVfcHJpdmF0ZV9rZXkocHVibGljX2V4cG9uZW50PTY1NTM3LCBrZXlfc2l6ZT0yMDQ4KQogICAgICAgIGNyZWF0ZWQgPSBub3coKQogICAgICAgIGV4cGlyZXMgPSBtaW4oY3JlYXRlZCArIGR0LnRpbWVkZWx0YShkYXlzPWRheXMpLCBzZWxmLmNlcnQubm90X3ZhbGlkX2FmdGVyX3V0YykKICAgICAgICBpZiBleHBpcmVzIDw9IGNyZWF0ZWQgKyBkdC50aW1lZGVsdGEoZGF5cz0xKToKICAgICAgICAgICAgcmFpc2UgUnVudGltZUVycm9yKCJBbnlDb25uZWN0IENBIG5lZWRzIHJlbmV3YWwiKQogICAgICAgIGNuID0gInRvbGYtb2MtIiArIGRldmljZV9pZAogICAgICAgIGNlcnQgPSAoeDUwOS5DZXJ0aWZpY2F0ZUJ1aWxkZXIoKQogICAgICAgICAgICAgICAgLnN1YmplY3RfbmFtZSh4NTA5Lk5hbWUoW3g1MDkuTmFtZUF0dHJpYnV0ZShOYW1lT0lELkNPTU1PTl9OQU1FLCBjbildKSkKICAgICAgICAgICAgICAgIC5pc3N1ZXJfbmFtZShzZWxmLmNlcnQuc3ViamVjdCkucHVibGljX2tleShrZXkucHVibGljX2tleSgpKQogICAgICAgICAgICAgICAgLnNlcmlhbF9udW1iZXIoeDUwOS5yYW5kb21fc2VyaWFsX251bWJlcigpKQogICAgICAgICAgICAgICAgLm5vdF92YWxpZF9iZWZvcmUoY3JlYXRlZCAtIGR0LnRpbWVkZWx0YShtaW51dGVzPTUpKS5ub3RfdmFsaWRfYWZ0ZXIoZXhwaXJlcykKICAgICAgICAgICAgICAgIC5hZGRfZXh0ZW5zaW9uKHg1MDkuQmFzaWNDb25zdHJhaW50cyhjYT1GYWxzZSwgcGF0aF9sZW5ndGg9Tm9uZSksIGNyaXRpY2FsPVRydWUpCiAgICAgICAgICAgICAgICAuYWRkX2V4dGVuc2lvbih4NTA5LktleVVzYWdlKAogICAgICAgICAgICAgICAgICAgIGRpZ2l0YWxfc2lnbmF0dXJlPVRydWUsIGNvbnRlbnRfY29tbWl0bWVudD1GYWxzZSwga2V5X2VuY2lwaGVybWVudD1UcnVlLAogICAgICAgICAgICAgICAgICAgIGRhdGFfZW5jaXBoZXJtZW50PUZhbHNlLCBrZXlfYWdyZWVtZW50PUZhbHNlLCBrZXlfY2VydF9zaWduPUZhbHNlLAogICAgICAgICAgICAgICAgICAgIGNybF9zaWduPUZhbHNlLCBlbmNpcGhlcl9vbmx5PUZhbHNlLCBkZWNpcGhlcl9vbmx5PUZhbHNlKSwgY3JpdGljYWw9VHJ1ZSkKICAgICAgICAgICAgICAgIC5hZGRfZXh0ZW5zaW9uKHg1MDkuRXh0ZW5kZWRLZXlVc2FnZShbRXh0ZW5kZWRLZXlVc2FnZU9JRC5DTElFTlRfQVVUSF0pLCBGYWxzZSkKICAgICAgICAgICAgICAgIC5hZGRfZXh0ZW5zaW9uKHg1MDkuU3ViamVjdEtleUlkZW50aWZpZXIuZnJvbV9wdWJsaWNfa2V5KGtleS5wdWJsaWNfa2V5KCkpLCBGYWxzZSkKICAgICAgICAgICAgICAgIC5hZGRfZXh0ZW5zaW9uKHg1MDkuQXV0aG9yaXR5S2V5SWRlbnRpZmllci5mcm9tX2lzc3Vlcl9wdWJsaWNfa2V5KHNlbGYua2V5LnB1YmxpY19rZXkoKSksIEZhbHNlKQogICAgICAgICAgICAgICAgLnNpZ24oc2VsZi5rZXksIGhhc2hlcy5TSEEyNTYoKSkpCiAgICAgICAgcmV0dXJuIHsKICAgICAgICAgICAgInVzZXJuYW1lIjogY24sICJzZXJpYWwiOiBmb3JtYXQoY2VydC5zZXJpYWxfbnVtYmVyLCAieCIpLAogICAgICAgICAgICAiY3JlYXRlZF9hdCI6IGNyZWF0ZWQuaXNvZm9ybWF0KCksICJleHBpcmVzX2F0IjogZXhwaXJlcy5pc29mb3JtYXQoKSwKICAgICAgICAgICAgImNlcnRpZmljYXRlIjogY2VydC5wdWJsaWNfYnl0ZXMoc2VyaWFsaXphdGlvbi5FbmNvZGluZy5QRU0pLAogICAgICAgICAgICAiZW5jcnlwdGVkX2tleSI6IGtleS5wcml2YXRlX2J5dGVzKAogICAgICAgICAgICAgICAgc2VyaWFsaXphdGlvbi5FbmNvZGluZy5QRU0sIHNlcmlhbGl6YXRpb24uUHJpdmF0ZUZvcm1hdC5QS0NTOCwKICAgICAgICAgICAgICAgIHNlcmlhbGl6YXRpb24uQmVzdEF2YWlsYWJsZUVuY3J5cHRpb24oc2VsZi5wYXNzd29yZCkpLAogICAgICAgIH0KCiAgICBkZWYgYnVuZGxlKHNlbGYsIHJlY29yZCk6CiAgICAgICAga2V5ID0gc2VyaWFsaXphdGlvbi5sb2FkX3BlbV9wcml2YXRlX2tleShyZWNvcmRbImVuY3J5cHRlZF9rZXkiXSwgc2VsZi5wYXNzd29yZCkKICAgICAgICBjZXJ0ID0geDUwOS5sb2FkX3BlbV94NTA5X2NlcnRpZmljYXRlKHJlY29yZFsiY2VydGlmaWNhdGUiXSkKICAgICAgICBpZiBrZXkucHVibGljX2tleSgpLnB1YmxpY19udW1iZXJzKCkgIT0gY2VydC5wdWJsaWNfa2V5KCkucHVibGljX251bWJlcnMoKToKICAgICAgICAgICAgcmFpc2UgUnVudGltZUVycm9yKCJEZXZpY2UgY2VydGlmaWNhdGUgZG9lcyBub3QgbWF0Y2ggaXRzIGtleSIpCiAgICAgICAgcGFzc3dvcmQgPSBzZWNyZXRzLnRva2VuX3VybHNhZmUoMTgpCiAgICAgICAgZGF0YSA9IHBrY3MxMi5zZXJpYWxpemVfa2V5X2FuZF9jZXJ0aWZpY2F0ZXMoCiAgICAgICAgICAgIHJlY29yZFsidXNlcm5hbWUiXS5lbmNvZGUoImFzY2lpIiksIGtleSwgY2VydCwgW3NlbGYuY2VydF0sCiAgICAgICAgICAgIHNlcmlhbGl6YXRpb24uQmVzdEF2YWlsYWJsZUVuY3J5cHRpb24ocGFzc3dvcmQuZW5jb2RlKCJhc2NpaSIpKSkKICAgICAgICByZXR1cm4gZGF0YSwgcGFzc3dvcmQKCiAgICBkZWYgY3JsKHNlbGYsIHJldm9rZWQsIG51bWJlcj0xKToKICAgICAgICBjcmVhdGVkID0gbm93KCkKICAgICAgICBidWlsZGVyID0gKHg1MDkuQ2VydGlmaWNhdGVSZXZvY2F0aW9uTGlzdEJ1aWxkZXIoKS5pc3N1ZXJfbmFtZShzZWxmLmNlcnQuc3ViamVjdCkKICAgICAgICAgICAgICAgICAgIC5sYXN0X3VwZGF0ZShjcmVhdGVkIC0gZHQudGltZWRlbHRhKG1pbnV0ZXM9MSkpCiAgICAgICAgICAgICAgICAgICAubmV4dF91cGRhdGUoY3JlYXRlZCArIGR0LnRpbWVkZWx0YShkYXlzPTcpKQogICAgICAgICAgICAgICAgICAgLmFkZF9leHRlbnNpb24oeDUwOS5DUkxOdW1iZXIobnVtYmVyKSwgRmFsc2UpCiAgICAgICAgICAgICAgICAgICAuYWRkX2V4dGVuc2lvbih4NTA5LkF1dGhvcml0eUtleUlkZW50aWZpZXIuZnJvbV9pc3N1ZXJfcHVibGljX2tleSgKICAgICAgICAgICAgICAgICAgICAgICBzZWxmLmtleS5wdWJsaWNfa2V5KCkpLCBGYWxzZSkpCiAgICAgICAgZm9yIHNlcmlhbCwgcmV2b2tlZF9hdCBpbiByZXZva2VkOgogICAgICAgICAgICBlbnRyeSA9ICh4NTA5LlJldm9rZWRDZXJ0aWZpY2F0ZUJ1aWxkZXIoKS5zZXJpYWxfbnVtYmVyKGludChzZXJpYWwsIDE2KSkKICAgICAgICAgICAgICAgICAgICAgLnJldm9jYXRpb25fZGF0ZShyZXZva2VkX2F0KS5idWlsZCgpKQogICAgICAgICAgICBidWlsZGVyID0gYnVpbGRlci5hZGRfcmV2b2tlZF9jZXJ0aWZpY2F0ZShlbnRyeSkKICAgICAgICByZXR1cm4gYnVpbGRlci5zaWduKHNlbGYua2V5LCBoYXNoZXMuU0hBMjU2KCkpLnB1YmxpY19ieXRlcyhzZXJpYWxpemF0aW9uLkVuY29kaW5nLlBFTSkK'}, 'tolf_anyconnect.py': {'sha256': '38c070e470de639880cde662209dfdb690be6fab7aba390e1c60a739be2221d4', 'data': 'IiIiVUsgZm91bmRhdGlvbiBmb3IgcGVyc29uYWwgQW55Q29ubmVjdDsgaXNzdWFuY2Ugc3RheXMgZGlzYWJsZWQgdW50aWwgbm9kZSBhY3RpdmF0aW9uLiIiIgpmcm9tIGNvbnRleHRsaWIgaW1wb3J0IGNsb3NpbmcKZnJvbSBwYXRobGliIGltcG9ydCBQYXRoCmltcG9ydCBzcWxpdGUzCmZyb20gZmFzdGFwaSBpbXBvcnQgSFRUUEV4Y2VwdGlvbiwgUmVxdWVzdApmcm9tIGZhc3RhcGkucmVzcG9uc2VzIGltcG9ydCBKU09OUmVzcG9uc2UsIFJlc3BvbnNlCmZyb20gdG9sZl9vY19jZXJ0aWZpY2F0ZXMgaW1wb3J0IEF1dGhvcml0eQoKVkVSU0lPTiA9IDEKSEVBREVSUyA9IHsiQ2FjaGUtQ29udHJvbCI6ICJuby1zdG9yZSIsICJSZWZlcnJlci1Qb2xpY3kiOiAibm8tcmVmZXJyZXIifQpTQ0hFTUEgPSAiIiIKQ1JFQVRFIFRBQkxFIElGIE5PVCBFWElTVFMgb2NfZGV2aWNlcyAoCiAgICBpZCBURVhUIFBSSU1BUlkgS0VZLAogICAgLS0gS2VlcCB0aGUgY2VydGlmaWNhdGUgdG9tYnN0b25lIGFmdGVyIGFjY291bnQgZGVsZXRpb24gZm9yIENSTCBlbmZvcmNlbWVudC4KICAgIHVzZXJfaWQgVEVYVCBOT1QgTlVMTCwKICAgIHJlcXVlc3RfaWQgVEVYVCBOT1QgTlVMTCwKICAgIGxhYmVsIFRFWFQgTk9UIE5VTEwsCiAgICB1c2VybmFtZSBURVhUIFVOSVFVRSBOT1QgTlVMTCwKICAgIHNlcmlhbCBURVhUIFVOSVFVRSBOT1QgTlVMTCwKICAgIGNlcnRpZmljYXRlIEJMT0IgTk9UIE5VTEwsCiAgICBlbmNyeXB0ZWRfa2V5IEJMT0IgTk9UIE5VTEwsCiAgICBjcmVhdGVkX2F0IFRFWFQgTk9UIE5VTEwsCiAgICBleHBpcmVzX2F0IFRFWFQgTk9UIE5VTEwsCiAgICBzdGF0ZSBURVhUIE5PVCBOVUxMIENIRUNLKHN0YXRlIElOICgncGVuZGluZycsJ2FjdGl2ZScsJ3Jldm9raW5nJywncmV2b2tlZCcpKSwKICAgIHJldm9rZWRfYXQgVEVYVCwKICAgIG1vZGUgVEVYVCBOT1QgTlVMTCBERUZBVUxUICdhdXRvJyBDSEVDSyhtb2RlIElOICgnYXV0bycsJ3J1JywnbHYnLCd5dCcpKSwKICAgIFVOSVFVRSh1c2VyX2lkLCByZXF1ZXN0X2lkKQopOwpDUkVBVEUgVEFCTEUgSUYgTk9UIEVYSVNUUyBvY19pbXBvcnRfZ3JhbnRzICgKICAgIHRva2VuX2hhc2ggQkxPQiBQUklNQVJZIEtFWSwKICAgIGRldmljZV9pZCBURVhUIE5PVCBOVUxMIFJFRkVSRU5DRVMgb2NfZGV2aWNlcyhpZCksCiAgICB1c2VyX2lkIFRFWFQgTk9UIE5VTEwsCiAgICBleHBpcmVzX2F0IFRFWFQgTk9UIE5VTEwsCiAgICBwYWNrYWdlIEJMT0IgTk9UIE5VTEwKKTsKQ1JFQVRFIFRSSUdHRVIgSUYgTk9UIEVYSVNUUyBvY19hZnRlcl9hY2NvdW50X2RlbGV0ZSBBRlRFUiBERUxFVEUgT04gdXNlcnMKQkVHSU4KICAgIFVQREFURSBvY19kZXZpY2VzIFNFVCBzdGF0ZT0ncmV2b2tpbmcnLAogICAgICAgIHJldm9rZWRfYXQ9Q09BTEVTQ0UocmV2b2tlZF9hdCxzdHJmdGltZSgnJVktJW0tJWRUJUg6JU06JWZaJywnbm93JykpCiAgICAgICAgV0hFUkUgdXNlcl9pZD1PTEQuaWQgQU5EIHN0YXRlIElOICgncGVuZGluZycsJ2FjdGl2ZScpOwogICAgREVMRVRFIEZST00gb2NfaW1wb3J0X2dyYW50cyBXSEVSRSB1c2VyX2lkPU9MRC5pZDsKRU5EOwoiIiIKCgpkZWYgaW5zdGFsbChhcHAsIGNvbnRleHQpOgogICAgZm9yIG5hbWUgaW4gKCJEQiIsICJhdXRoZW50aWNhdGVkX3VzZXJfaWQiLCAidG9sZl9wcm9tb3MiKToKICAgICAgICBpZiBuYW1lIG5vdCBpbiBjb250ZXh0OgogICAgICAgICAgICByYWlzZSBSdW50aW1lRXJyb3IoIk1pc3NpbmcgVE9MRiBpbnRlZ3JhdGlvbjogIiArIG5hbWUpCiAgICBkaXJlY3RvcnkgPSBQYXRoKGNvbnRleHRbIkRCIl0pLnBhcmVudCAvICJhbnljb25uZWN0IgogICAgYXV0aG9yaXR5ID0gQXV0aG9yaXR5KGRpcmVjdG9yeSkKICAgIHdpdGggY2xvc2luZyhzcWxpdGUzLmNvbm5lY3QoY29udGV4dFsiREIiXSwgdGltZW91dD0zMCkpIGFzIGNvbiwgY29uOgogICAgICAgIGlmIG5vdCBjb24uZXhlY3V0ZSgiU0VMRUNUIDEgRlJPTSBzcWxpdGVfbWFzdGVyIFdIRVJFIHR5cGU9J3RhYmxlJyBBTkQgbmFtZT0ndXNlcnMnIikuZmV0Y2hvbmUoKToKICAgICAgICAgICAgcmFpc2UgUnVudGltZUVycm9yKCJUT0xGIGFjY291bnQgZGF0YWJhc2Ugbm90IGZvdW5kIikKICAgICAgICBjb24uZXhlY3V0ZXNjcmlwdChTQ0hFTUEpCgogICAgQGFwcC5nZXQoIi9vYy9hY2Nlc3MvY2FwYWJpbGl0aWVzIikKICAgIGRlZiBjYXBhYmlsaXRpZXMoKToKICAgICAgICByZXR1cm4gSlNPTlJlc3BvbnNlKHsKICAgICAgICAgICAgInZlcnNpb24iOiBWRVJTSU9OLCAiY2VydGlmaWNhdGVBdXRob3JpdHkiOiBUcnVlLAogICAgICAgICAgICAiY2FTaGEyNTYiOiBhdXRob3JpdHkuZmluZ2VycHJpbnQsCiAgICAgICAgICAgICJpc3N1YW5jZSI6IEZhbHNlLCAibm9kZVJlYWR5IjogRmFsc2UsCiAgICAgICAgICAgICJyZWFzb24iOiAibm9kZV9hY3RpdmF0aW9uX3JlcXVpcmVkIiwKICAgICAgICB9LCBoZWFkZXJzPUhFQURFUlMpCgogICAgQGFwcC5nZXQoIi9vYy9hY2Nlc3MvY2EucGVtIikKICAgIGRlZiBwdWJsaWNfY2EoKToKICAgICAgICAjIFRoaXMgaXMgYSBwdWJsaWMgQ0EgY2VydGlmaWNhdGUsIG5ldmVyIGEga2V5IG9yIGEgY2xpZW50IGlkZW50aXR5LgogICAgICAgIHJldHVybiBSZXNwb25zZSgoZGlyZWN0b3J5IC8gImNhLnBlbSIpLnJlYWRfYnl0ZXMoKSwKICAgICAgICAgICAgICAgICAgICAgICAgbWVkaWFfdHlwZT0iYXBwbGljYXRpb24veC1wZW0tZmlsZSIsIGhlYWRlcnM9SEVBREVSUykKCiAgICBAYXBwLmdldCgiL29jL2FjY2Vzcy9kZXZpY2VzIikKICAgIGRlZiBkZXZpY2VzKHJlcXVlc3Q6IFJlcXVlc3QpOgogICAgICAgIHVzZXIgPSBjb250ZXh0WyJhdXRoZW50aWNhdGVkX3VzZXJfaWQiXShyZXF1ZXN0KQogICAgICAgIHdpdGggY2xvc2luZyhzcWxpdGUzLmNvbm5lY3QoY29udGV4dFsiREIiXSwgdGltZW91dD0zMCkpIGFzIGNvbjoKICAgICAgICAgICAgY29uLnJvd19mYWN0b3J5ID0gc3FsaXRlMy5Sb3cKICAgICAgICAgICAgcm93cyA9IGNvbi5leGVjdXRlKCIiIgogICAgICAgICAgICAgICAgU0VMRUNUIGlkLGxhYmVsLHVzZXJuYW1lLGNyZWF0ZWRfYXQsZXhwaXJlc19hdCxzdGF0ZSxtb2RlCiAgICAgICAgICAgICAgICBGUk9NIG9jX2RldmljZXMgV0hFUkUgdXNlcl9pZD0/IE9SREVSIEJZIGNyZWF0ZWRfYXQKICAgICAgICAgICAgIiIiLCAodXNlciwpKS5mZXRjaGFsbCgpCiAgICAgICAgcmV0dXJuIEpTT05SZXNwb25zZSh7ImRldmljZXMiOiBbZGljdChyb3cpIGZvciByb3cgaW4gcm93c119LCBoZWFkZXJzPUhFQURFUlMpCgogICAgQGFwcC5wb3N0KCIvb2MvYWNjZXNzL2RldmljZXMiKQogICAgZGVmIGNyZWF0ZV9kZXZpY2UocmVxdWVzdDogUmVxdWVzdCk6CiAgICAgICAgY29udGV4dFsiYXV0aGVudGljYXRlZF91c2VyX2lkIl0ocmVxdWVzdCkKICAgICAgICBpZiByZXF1ZXN0LmhlYWRlcnMuZ2V0KCJvcmlnaW4iKSAhPSBjb250ZXh0LmdldCgiT1JJR0lOIik6CiAgICAgICAgICAgIHJhaXNlIEhUVFBFeGNlcHRpb24oNDAzLCAiSW52YWxpZCBvcmlnaW4iKQogICAgICAgIHJhaXNlIEhUVFBFeGNlcHRpb24oNTAzLCAiQW55Q29ubmVjdCBub2RlIGFjdGl2YXRpb24gaXMgbm90IGNvbXBsZXRlZCIpCg=='}}
API = Path("/opt/tolf-api")
PYTHON = API / "venv/bin/python"
MARKER = "# TOLF AnyConnect UK foundation v1"


def run(*args):
    return subprocess.check_output(args, text=True).strip()


def atomic_write(path, data, mode=0o644):
    fd, temporary = tempfile.mkstemp(prefix=".oc-install-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main():
    if os.geteuid() != 0:
        raise RuntimeError("Run this installer as root on EDISUK")
    source = (API / "main.py").read_text()
    tree = ast.parse(source)
    db = None
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "DB" for t in node.targets):
            db = Path(ast.literal_eval(node.value))
    if db is None or not db.is_file():
        raise RuntimeError("Existing TOLF database was not found")
    if not PYTHON.is_file():
        raise RuntimeError("TOLF API Python environment was not found")
    run(str(PYTHON), "-c", "import cryptography, fastapi")
    user = run("systemctl", "show", "tolf-api", "-p", "User", "--value") or "root"
    owner = pwd.getpwnam(user)
    modules = {}
    for name, entry in PAYLOAD.items():
        if name not in {"tolf_oc_certificates.py", "tolf_anyconnect.py"}:
            raise RuntimeError("Unexpected installer payload")
        data = base64.b64decode(entry["data"], validate=True)
        if hashlib.sha256(data).hexdigest() != entry["sha256"]:
            raise RuntimeError("Installer payload hash mismatch")
        compile(data, name, "exec")
        modules[name] = data
    if len(modules) != 2:
        raise RuntimeError("Installer payload is incomplete")
    if MARKER not in source and "tolf_anyconnect.install" in source:
        raise RuntimeError("An unrecognized AnyConnect module is already installed")
    updated = source if MARKER in source else source.rstrip() + (
        "\n\n" + MARKER + "\nimport tolf_anyconnect\ntolf_anyconnect.install(app, globals())\n"
    )
    compile(updated, str(API / "main.py"), "exec")
    backup = Path(tempfile.mkdtemp(prefix="anyconnect-backup-", dir=API))
    shutil.copy2(API / "main.py", backup / "main.py")
    for name in modules:
        if (API / name).exists():
            shutil.copy2(API / name, backup / name)
    directory = db.parent / "anyconnect"
    if directory.is_symlink():
        raise RuntimeError("AnyConnect authority directory cannot be a symlink")
    restarted = False
    try:
        for name, data in modules.items():
            atomic_write(API / name, data)
        env = dict(os.environ, PYTHONPATH=str(API))
        fingerprint = subprocess.check_output(
            [str(PYTHON), "-c", "import sys; from tolf_oc_certificates import initialize; print(initialize(sys.argv[1]))",
             str(directory)], env=env, text=True).strip()
        os.chown(directory, owner.pw_uid, owner.pw_gid)
        os.chmod(directory, 0o700)
        for path in directory.iterdir():
            if path.is_symlink() or not path.is_file():
                raise RuntimeError("Unexpected file in AnyConnect authority directory")
            os.chown(path, owner.pw_uid, owner.pw_gid)
            os.chmod(path, 0o600)
        # Confirm that the actual service user can read and decrypt the CA.
        run("runuser", "-u", user, "--", str(PYTHON), "-c",
            "import sys; sys.path.insert(0,sys.argv[1]); from tolf_oc_certificates import Authority; Authority(sys.argv[2])",
            str(API), str(directory))
        atomic_write(API / "main.py", updated.encode())
        restarted = True
        subprocess.run(["systemctl", "restart", "tolf-api"], check=True)
        result = None
        for _ in range(20):
            try:
                with urllib.request.urlopen("http://127.0.0.1:8000/oc/access/capabilities", timeout=2) as response:
                    result = json.load(response)
                if result.get("version") == 1 and result.get("caSha256") == fingerprint:
                    break
            except (OSError, ValueError):
                pass
            time.sleep(1)
        if (not result or result.get("version") != 1 or result.get("caSha256") != fingerprint
                or result.get("issuance") is not False or result.get("nodeReady") is not False):
            raise RuntimeError("AnyConnect API health check failed")
    except Exception:
        atomic_write(API / "main.py", (backup / "main.py").read_bytes())
        for name in modules:
            if (backup / name).exists():
                atomic_write(API / name, (backup / name).read_bytes())
        if restarted:
            subprocess.run(["systemctl", "restart", "tolf-api"], check=False)
        print("Existing API restored. Backup:", backup, file=sys.stderr)
        print("The new CA, if created, is preserved for a retry.", file=sys.stderr)
        raise
    print("OK: UK AnyConnect certificate foundation installed.")
    print("CA SHA256:", fingerprint)
    print("Backup:", backup)
    print("Device issuance: disabled until Moscow node activation.")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
