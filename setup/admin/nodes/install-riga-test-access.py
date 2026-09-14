#!/usr/bin/python3
"""Install reversible Test #26 access control and provisioning guards."""
import base64
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import time

PAYLOAD = 'IyEvdXNyL2Jpbi9weXRob24zCiIiIlJldmVyc2libGUgY3JlZGVudGlhbHMgcXVhcmFudGluZSBmb3IgVGVzdCAjMjYgb25seS4gUm9vdCBvbiBSaWdhLiIiIgppbXBvcnQgY29udGV4dGxpYgppbXBvcnQgZmNudGwKaW1wb3J0IGhhc2hsaWIKaW1wb3J0IGpzb24KaW1wb3J0IG9zCmZyb20gcGF0aGxpYiBpbXBvcnQgUGF0aAppbXBvcnQgcmUKaW1wb3J0IHJ1bnB5CmltcG9ydCBzdWJwcm9jZXNzCmltcG9ydCBzeXMKaW1wb3J0IHRlbXBmaWxlCmltcG9ydCB0aW1lCmltcG9ydCB1dWlkCgpVU0VSID0gJ3VzZXJfMDg4ODA0OGNhYzZlNDRkMjhhZWQ5ODU3YWEzMWU5ZWQnCkNPTkYgPSBQYXRoKCcvZXRjL3N3YW5jdGwvY29uZi5kL3VzZXItJyArIFVTRVIgKyAnLmNvbmYnKQpCQVNFID0gUGF0aCgnL3Zhci9saWIvdG9sZi1hZG1pbi90ZXN0MjYtYWNjZXNzJykKU1RBVEUgPSBCQVNFIC8gJ3N0YXRlLmpzb24nClZBVUxUID0gQkFTRSAvICdjcmVkZW50aWFsLnNhdmVkJwpBTExPVyA9IFBhdGgoJy92YXIvbGliL2lrZS11c2Vycy9tb3Njb3ctYWNjZXNzLzA4ODgwNDhjYWM2ZTQ0ZDI4YWVkOTg1N2FhMzFlOWVkLmFsbG93JykKWkVSTyA9ICcwJyAqIDMyClNTSCA9IFsnL3Vzci9iaW4vc3NoJywgJy1UJywgJy1pJywgJy9yb290Ly5zc2gvaWRfZWQyNTUxOV9pa2VfdXNlcnNfc3luYycsCiAgICAgICAnLW8nLCAnSWRlbnRpdGllc09ubHk9eWVzJywgJy1vJywgJ0JhdGNoTW9kZT15ZXMnLCAnLW8nLCAnU3RyaWN0SG9zdEtleUNoZWNraW5nPXllcycsCiAgICAgICAnLW8nLCAnQ29ubmVjdFRpbWVvdXQ9MTAnLCAncm9vdEAxMC4zMS4wLjEnXQoKCmNsYXNzIEFjY2Vzc0Vycm9yKEV4Y2VwdGlvbik6CiAgICBwYXNzCgoKZGVmIGF0b21pYyhwYXRoLCBkYXRhKToKICAgIGZkLCBuYW1lID0gdGVtcGZpbGUubWtzdGVtcChwcmVmaXg9Jy5uZXctJywgZGlyPXBhdGgucGFyZW50KQogICAgdHJ5OgogICAgICAgIHdpdGggb3MuZmRvcGVuKGZkLCAnd2InKSBhcyBvdXQ6CiAgICAgICAgICAgIG91dC53cml0ZShkYXRhKQogICAgICAgICAgICBvdXQuZmx1c2goKQogICAgICAgICAgICBvcy5mc3luYyhvdXQuZmlsZW5vKCkpCiAgICAgICAgb3MuY2htb2QobmFtZSwgMG82MDApCiAgICAgICAgb3MucmVwbGFjZShuYW1lLCBwYXRoKQogICAgICAgIGZkID0gb3Mub3BlbihwYXRoLnBhcmVudCwgb3MuT19SRE9OTFkgfCBvcy5PX0RJUkVDVE9SWSkKICAgICAgICB0cnk6IG9zLmZzeW5jKGZkKQogICAgICAgIGZpbmFsbHk6IG9zLmNsb3NlKGZkKQogICAgZmluYWxseToKICAgICAgICBQYXRoKG5hbWUpLnVubGluayhtaXNzaW5nX29rPVRydWUpCgoKZGVmIGNvbW1hbmQoYXJncywgZGF0YT1Ob25lKToKICAgIHJlc3VsdCA9IHN1YnByb2Nlc3MucnVuKGFyZ3MsIGlucHV0PWRhdGEsIHN0ZG91dD1zdWJwcm9jZXNzLlBJUEUsCiAgICAgICAgICAgICAgICAgICAgICAgICAgICBzdGRlcnI9c3VicHJvY2Vzcy5ERVZOVUxMLCB0aW1lb3V0PTMwLCBjaGVjaz1GYWxzZSkKICAgIGlmIHJlc3VsdC5yZXR1cm5jb2RlOgogICAgICAgIHJhaXNlIEFjY2Vzc0Vycm9yKCdub2RlX29wZXJhdGlvbl9mYWlsZWQnKQogICAgcmV0dXJuIHJlc3VsdC5zdGRvdXQKCgpkZWYgcmVtb3RlKHRleHQsIGRhdGE9Tm9uZSk6CiAgICByZXR1cm4gY29tbWFuZChTU0ggKyBbdGV4dF0sIGRhdGEpCgoKZGVmIGRpZ2VzdChkYXRhKToKICAgIHJldHVybiBoYXNobGliLnNoYTI1NihkYXRhKS5oZXhkaWdlc3QoKQoKCmRlZiByZW1vdGVfZGlnZXN0KCk6CiAgICBvdXRwdXQgPSByZW1vdGUoImlmIFsgLWYgJyIgKyBzdHIoQ09ORikgKyAiJyBdOyB0aGVuIHNoYTI1NnN1bSAnIiArIHN0cihDT05GKSArICInOyBlbHNlIGVjaG8gYWJzZW50OyBmaSIpLmRlY29kZSgnYXNjaWknKS5zcGxpdCgpCiAgICBpZiBvdXRwdXQgPT0gWydhYnNlbnQnXToKICAgICAgICByZXR1cm4gTm9uZQogICAgaWYgbGVuKG91dHB1dCkgIT0gMiBvciBub3QgcmUuZnVsbG1hdGNoKCdbMC05YS1mXXs2NH0nLCBvdXRwdXRbMF0pOgogICAgICAgIHJhaXNlIEFjY2Vzc0Vycm9yKCdpbnZhbGlkX25vZGVfcmVzcG9uc2UnKQogICAgcmV0dXJuIG91dHB1dFswXQoKCmRlZiByZWFkX3N0YXRlKCk6CiAgICBpZiBub3QgU1RBVEUuZXhpc3RzKCk6CiAgICAgICAgcmV0dXJuIHsnc3RhdGUnOiAnYWN0aXZlJywgJ3JldmlzaW9uJzogWkVST30KICAgIHZhbHVlID0ganNvbi5sb2FkcyhTVEFURS5yZWFkX3RleHQoKSkKICAgIGlmIHZhbHVlLmdldCgnc3RhdGUnKSBub3QgaW4gKCdhY3RpdmUnLCAnc3VzcGVuZGluZycsICdzdXNwZW5kZWQnLCAncmVzdW1pbmcnKSBvciBub3QgcmUuZnVsbG1hdGNoKCdbMC05YS1mXXszMn0nLCB2YWx1ZS5nZXQoJ3JldmlzaW9uJywgJycpKToKICAgICAgICByYWlzZSBBY2Nlc3NFcnJvcignaW52YWxpZF9zYXZlZF9zdGF0ZScpCiAgICByZXR1cm4gdmFsdWUKCgpkZWYgd3JpdGVfc3RhdGUodmFsdWUpOgogICAgYXRvbWljKFNUQVRFLCBqc29uLmR1bXBzKHZhbHVlKS5lbmNvZGUoKSkKCgpkZWYgcmVwb3J0KHZhbHVlKToKICAgIHJldHVybiB7J3N0YXR1cyc6ICdvaycsICdhY2NvdW50TnVtYmVyJzogMjYsICdzdGF0ZSc6IHZhbHVlWydzdGF0ZSddLCAncmV2aXNpb24nOiB2YWx1ZVsncmV2aXNpb24nXX0KCgpkZWYgcmVsb2FkX2xvY2FsKCk6CiAgICBjb21tYW5kKFsnL3Vzci9zYmluL3N3YW5jdGwnLCAnLS1sb2FkLWNyZWRzJywgJy0tY2xlYXInLCAnLS1ub3Byb21wdCddKQoKCmRlZiBoaWRlX2NyZWRlbnRpYWxzKCk6CiAgICBDT05GLnVubGluayhtaXNzaW5nX29rPVRydWUpCiAgICByZWxvYWRfbG9jYWwoKQogICAgcmVtb3RlKCJybSAtZiAnIiArIHN0cihDT05GKSArICInICYmIHN3YW5jdGwgLS1sb2FkLWNyZWRzIC0tY2xlYXIgLS1ub3Byb21wdCA+L2Rldi9udWxsIDI+JjEiKQoKCmRlZiByZXN0b3JlX2NyZWRlbnRpYWxzKGRhdGEpOgogICAgaWYgbm90IEFMTE9XLmlzX2ZpbGUoKToKICAgICAgICByYWlzZSBBY2Nlc3NFcnJvcignbW9zY293X3Blcm1pc3Npb25fbWlzc2luZycpCiAgICBpZiBDT05GLmV4aXN0cygpIGFuZCBkaWdlc3QoQ09ORi5yZWFkX2J5dGVzKCkpICE9IGRpZ2VzdChkYXRhKToKICAgICAgICByYWlzZSBBY2Nlc3NFcnJvcignbG9jYWxfY3JlZGVudGlhbF9jb25mbGljdCcpCiAgICByZW1vdGVfaGFzaCA9IHJlbW90ZV9kaWdlc3QoKQogICAgaWYgcmVtb3RlX2hhc2ggbm90IGluIChOb25lLCBkaWdlc3QoZGF0YSkpOgogICAgICAgIHJhaXNlIEFjY2Vzc0Vycm9yKCdyZW1vdGVfY3JlZGVudGlhbF9jb25mbGljdCcpCiAgICAjIFNlY3JldCBieXRlcyB0cmF2ZWwgb25seSB0aHJvdWdoIFNTSCBzdGRpbiwgbmV2ZXIgYXJndiwgbG9ncyBvciBKU09OLgogICAgcmVtb3RlKCJzZXQgLWV1OyB1bWFzayAwNzc7IHRtcD0kKG1rdGVtcCAvZXRjL3N3YW5jdGwvY29uZi5kLy50ZXN0MjYuWFhYWFhYKTsgIgogICAgICAgICAgICJ0cmFwICdybSAtZiBcIiR0bXBcIicgRVhJVDsgY2F0ID5cIiR0bXBcIjsgY2htb2QgNjAwIFwiJHRtcFwiOyAiCiAgICAgICAgICAgIm12IC1mIFwiJHRtcFwiICciICsgc3RyKENPTkYpICsgIic7IHN3YW5jdGwgLS1sb2FkLWNyZWRzIC0tY2xlYXIgLS1ub3Byb21wdCA+L2Rldi9udWxsIDI+JjEiLCBkYXRhKQogICAgYXRvbWljKENPTkYsIGRhdGEpCiAgICByZWxvYWRfbG9jYWwoKQogICAgaWYgcmVtb3RlX2RpZ2VzdCgpICE9IGRpZ2VzdChkYXRhKToKICAgICAgICByYWlzZSBBY2Nlc3NFcnJvcigncmVzdG9yYXRpb25fbm90X2NvbmZpcm1lZCcpCgoKZGVmIHRlcm1pbmF0ZV90ZXN0X3Nlc3Npb25zKCk6CiAgICBicmlkZ2UgPSBydW5weS5ydW5fcGF0aCgnL3Vzci9sb2NhbC9zYmluL3RvbGYtYWRtaW4tdGVzdC1jb250cm9sJykKICAgIGRlYWRsaW5lID0gdGltZS5tb25vdG9uaWMoKSArIDYwCiAgICBmb3Igbm9kZSBpbiAoJ3JpZ2EnLCAnbW9zY293Jyk6CiAgICAgICAgIyBSZS1saXN0IG9uY2UgcGVyIHNlbGVjdGVkIFNBIHNvIGVhY2ggb3BlcmF0aW9uIGhhcyBhIGZyZXNoIGJvdW5kZWQgdHJhbnNwb3J0LgogICAgICAgIGZvciBhdHRlbXB0IGluIHJhbmdlKDE2KToKICAgICAgICAgICAgaWYgdGltZS5tb25vdG9uaWMoKSA+PSBkZWFkbGluZToKICAgICAgICAgICAgICAgIHJhaXNlIEFjY2Vzc0Vycm9yKCd0ZXN0X2Rpc2Nvbm5lY3RfdGltZW91dCcpCiAgICAgICAgICAgIHdpdGggYnJpZGdlWydjb25uZWN0J10obm9kZSkgYXMgY2xpZW50OgogICAgICAgICAgICAgICAgY2xpZW50LmRlYWRsaW5lID0gbWluKGNsaWVudC5kZWFkbGluZSwgZGVhZGxpbmUpCiAgICAgICAgICAgICAgICBpbnZlbnRvcnkgPSBjbGllbnQuaW52ZW50b3J5KCkKICAgICAgICAgICAgICAgIGlmIGFueShyb3cuZ2V0KCdyZW1vdGUtaWQnKSA9PSBVU0VSLmVuY29kZSgpIGFuZCByb3cuZ2V0KCdyZW1vdGUtZWFwLWlkJykgIT0gVVNFUi5lbmNvZGUoKSBmb3Igcm93IGluIGludmVudG9yeSk6CiAgICAgICAgICAgICAgICAgICAgcmFpc2UgQWNjZXNzRXJyb3IoJ3Rlc3Rfc2Vzc2lvbl9pZGVudGl0eV9ub3RfdmVyaWZpYWJsZScpCiAgICAgICAgICAgICAgICBzZWxlY3RlZCA9IFticmlkZ2VbJ3NlbGVjdG9yJ10ocm93KSBmb3Igcm93IGluIGludmVudG9yeQogICAgICAgICAgICAgICAgICAgICAgICAgICAgaWYgcm93LmdldCgncmVtb3RlLWVhcC1pZCcpID09IFVTRVIuZW5jb2RlKCldCiAgICAgICAgICAgICAgICBpZiBhbnkoaXRlbSBpcyBOb25lIGZvciBpdGVtIGluIHNlbGVjdGVkKToKICAgICAgICAgICAgICAgICAgICByYWlzZSBBY2Nlc3NFcnJvcigndGVzdF9hdXRoZW50aWNhdGlvbl9pbl9wcm9ncmVzcycpCiAgICAgICAgICAgICAgICBpZiBub3Qgc2VsZWN0ZWQ6CiAgICAgICAgICAgICAgICAgICAgYnJlYWsKICAgICAgICAgICAgICAgIHJlc3VsdCA9IGJyaWRnZVsnb3BlcmF0ZSddKGNsaWVudCwgc2VsZWN0ZWRbMF0pCiAgICAgICAgICAgICAgICBpZiByZXN1bHQuZ2V0KCdzdGF0dXMnKSAhPSAnb2snOgogICAgICAgICAgICAgICAgICAgIHJhaXNlIEFjY2Vzc0Vycm9yKCd0ZXN0X2Rpc2Nvbm5lY3Rfbm90X2NvbmZpcm1lZCcpCiAgICAgICAgZWxzZToKICAgICAgICAgICAgcmFpc2UgQWNjZXNzRXJyb3IoJ3Rlc3Rfc2Vzc2lvbnNfcmVtYWluJykKCgpkZWYgY2hhbmdlKGFjdGlvbiwgZXhwZWN0ZWQpOgogICAgdmFsdWUgPSByZWFkX3N0YXRlKCkKICAgIGlmIHZhbHVlWydyZXZpc2lvbiddICE9IGV4cGVjdGVkOgogICAgICAgIHJhaXNlIEFjY2Vzc0Vycm9yKCdzdGFsZV9yZXZpc2lvbicpCiAgICBpZiBhY3Rpb24gPT0gJ3N1c3BlbmQnOgogICAgICAgIGlmIHZhbHVlWydzdGF0ZSddID09ICdhY3RpdmUnOgogICAgICAgICAgICBpZiBub3QgQ09ORi5pc19maWxlKCkgb3Igbm90IEFMTE9XLmlzX2ZpbGUoKToKICAgICAgICAgICAgICAgIHJhaXNlIEFjY2Vzc0Vycm9yKCd0ZXN0X2NyZWRlbnRpYWxzX29yX3Blcm1pc3Npb25fbWlzc2luZycpCiAgICAgICAgICAgIGRhdGEgPSBDT05GLnJlYWRfYnl0ZXMoKQogICAgICAgICAgICAjIE5ldmVyIG92ZXJ3cml0ZSBhIGRpZmZlcmVudCBNb3Njb3cgY3JlZGVudGlhbCBvbiBsYXRlciByZXN1bWUuCiAgICAgICAgICAgIGlmIHJlbW90ZV9kaWdlc3QoKSAhPSBkaWdlc3QoZGF0YSk6CiAgICAgICAgICAgICAgICByYWlzZSBBY2Nlc3NFcnJvcignbm9kZV9jcmVkZW50aWFsc19kaWZmZXInKQogICAgICAgICAgICBhdG9taWMoVkFVTFQsIGRhdGEpCiAgICAgICAgICAgIHZhbHVlWydkaWdlc3QnXSA9IGRpZ2VzdChkYXRhKQogICAgICAgIGVsaWYgbm90IFZBVUxULmlzX2ZpbGUoKSBvciBkaWdlc3QoVkFVTFQucmVhZF9ieXRlcygpKSAhPSB2YWx1ZS5nZXQoJ2RpZ2VzdCcpOgogICAgICAgICAgICByYWlzZSBBY2Nlc3NFcnJvcignc2F2ZWRfY3JlZGVudGlhbF9pbnZhbGlkJykKICAgICAgICB2YWx1ZS51cGRhdGUoc3RhdGU9J3N1c3BlbmRpbmcnLCByZXZpc2lvbj11dWlkLnV1aWQ0KCkuaGV4KQogICAgICAgIHdyaXRlX3N0YXRlKHZhbHVlKSAgIyBkdXJhYmxlIGRlbnkgZ2F0ZSBCRUZPUkUgcmVtb3ZpbmcgZWl0aGVyIGNyZWRlbnRpYWwKICAgICAgICBoaWRlX2NyZWRlbnRpYWxzKCkKICAgICAgICB0ZXJtaW5hdGVfdGVzdF9zZXNzaW9ucygpCiAgICAgICAgaWYgQ09ORi5leGlzdHMoKSBvciByZW1vdGVfZGlnZXN0KCkgaXMgbm90IE5vbmU6CiAgICAgICAgICAgIHJhaXNlIEFjY2Vzc0Vycm9yKCdzdXNwZW5zaW9uX25vdF9jb25maXJtZWQnKQogICAgICAgIHZhbHVlWydzdGF0ZSddID0gJ3N1c3BlbmRlZCcKICAgICAgICB3cml0ZV9zdGF0ZSh2YWx1ZSkKICAgIGVsaWYgYWN0aW9uID09ICdyZXN1bWUnOgogICAgICAgIGlmIHZhbHVlWydzdGF0ZSddID09ICdhY3RpdmUnOgogICAgICAgICAgICByZXR1cm4gcmVwb3J0KHZhbHVlKQogICAgICAgIGlmIG5vdCBWQVVMVC5pc19maWxlKCkgb3IgZGlnZXN0KFZBVUxULnJlYWRfYnl0ZXMoKSkgIT0gdmFsdWUuZ2V0KCdkaWdlc3QnKToKICAgICAgICAgICAgcmFpc2UgQWNjZXNzRXJyb3IoJ3NhdmVkX2NyZWRlbnRpYWxfaW52YWxpZCcpCiAgICAgICAgdmFsdWUudXBkYXRlKHN0YXRlPSdyZXN1bWluZycsIHJldmlzaW9uPXV1aWQudXVpZDQoKS5oZXgpCiAgICAgICAgd3JpdGVfc3RhdGUodmFsdWUpCiAgICAgICAgcmVzdG9yZV9jcmVkZW50aWFscyhWQVVMVC5yZWFkX2J5dGVzKCkpCiAgICAgICAgdmFsdWVbJ3N0YXRlJ10gPSAnYWN0aXZlJwogICAgICAgIHdyaXRlX3N0YXRlKHZhbHVlKSAgIyBhbGxvdyBzeW5jaHJvbmlzYXRpb24gb25seSBBRlRFUiBib3RoIHJlbG9hZHMgc3VjY2VlZAogICAgICAgIFZBVUxULnVubGluayhtaXNzaW5nX29rPVRydWUpCiAgICBlbHNlOgogICAgICAgIHJhaXNlIEFjY2Vzc0Vycm9yKCdpbnZhbGlkX2FjdGlvbicpCiAgICByZXR1cm4gcmVwb3J0KHZhbHVlKQoKCmRlZiBndWFyZCh1c2VybmFtZSk6CiAgICBpZiB1c2VybmFtZSA9PSBVU0VSIGFuZCByZWFkX3N0YXRlKClbJ3N0YXRlJ10gIT0gJ2FjdGl2ZSc6CiAgICAgICAgcmFpc2UgQWNjZXNzRXJyb3IoJ3Rlc3RfYWNjZXNzX3N1c3BlbmRlZCcpCgoKZGVmIG1haW4oKToKICAgIGlmIG9zLmdldGV1aWQoKSAhPSAwOgogICAgICAgIHJhaXNlIEFjY2Vzc0Vycm9yKCdyb290X3JlcXVpcmVkJykKICAgIGFyZ3MgPSBzeXMuYXJndlsxOl0KICAgIGlmIGxlbihhcmdzKSA9PSAyIGFuZCBhcmdzWzBdID09ICdndWFyZCc6CiAgICAgICAgZ3VhcmQoYXJnc1sxXSkKICAgICAgICByZXR1cm4KICAgIGlmIGFyZ3MgIT0gWydzdGF0dXMnXSBhbmQgKGxlbihhcmdzKSAhPSAyIG9yIGFyZ3NbMF0gbm90IGluICgnc3VzcGVuZCcsICdyZXN1bWUnKSBvciBub3QgcmUuZnVsbG1hdGNoKCdbMC05YS1mXXszMn0nLCBhcmdzWzFdKSk6CiAgICAgICAgcmFpc2UgQWNjZXNzRXJyb3IoJ2ludmFsaWRfYXJndW1lbnRzJykKICAgIEJBU0UubWtkaXIocGFyZW50cz1UcnVlLCBleGlzdF9vaz1UcnVlLCBtb2RlPTBvNzAwKQogICAgb3MuY2htb2QoQkFTRSwgMG83MDApCiAgICB3aXRoIGNvbnRleHRsaWIuRXhpdFN0YWNrKCkgYXMgc3RhY2s6CiAgICAgICAgIyBTYW1lIG9yZGVyIGFzIHByb3Zpc2lvbi1yb290IC0+IHN5bmMuIEd1YXJkIG1vZGUgbmV2ZXIgcmVhY3F1aXJlcyBsb2Nrcy4KICAgICAgICBmb3IgZmlsZW5hbWUgaW4gKCcvdmFyL2xvY2svdG9sZi1wcm92aXNpb24ubG9jaycsICcvdmFyL2xvY2svdG9sZi1hZG1pbi10ZXN0LXN5bmMubG9jaycpOgogICAgICAgICAgICBsb2NrID0gc3RhY2suZW50ZXJfY29udGV4dChvcGVuKGZpbGVuYW1lLCAnYScpKQogICAgICAgICAgICBmY250bC5mbG9jayhsb2NrLCBmY250bC5MT0NLX0VYKQogICAgICAgIHJlc3VsdCA9IHJlcG9ydChyZWFkX3N0YXRlKCkpIGlmIGFyZ3MgPT0gWydzdGF0dXMnXSBlbHNlIGNoYW5nZSgqYXJncykKICAgIHByaW50KGpzb24uZHVtcHMocmVzdWx0KSkKCgppZiBfX25hbWVfXyA9PSAnX19tYWluX18nOgogICAgdHJ5OgogICAgICAgIG1haW4oKQogICAgZXhjZXB0IEV4Y2VwdGlvbiBhcyBleGM6CiAgICAgICAgIyBBIHBhcnRpYWwgb3BlcmF0aW9uIHJlbWFpbnMgZHVyYWJseSBzdXNwZW5kaW5nL3Jlc3VtaW5nOyBuZXZlciBjbGFpbSBzdWNjZXNzLgogICAgICAgIHByaW50KGpzb24uZHVtcHMoeydzdGF0dXMnOiAnZXJyb3InLCAnZXJyb3InOiBzdHIoZXhjKSBpZiBpc2luc3RhbmNlKGV4YywgQWNjZXNzRXJyb3IpIGVsc2UgJ2FjY2Vzc19vcGVyYXRpb25fZmFpbGVkJ30pKQogICAgICAgIHN5cy5leGl0KDEpCg=='
HASH = '68410ae7c2f32d7a23b803f1f46cb2a4eef326eefa4ec9f3fd7f8d05a0824cd9'
BASE = Path('/usr/local/sbin')
READER = BASE / 'tolf-admin-test-access'
MARKER = '# TOLF test account access control v1'
ROOT_BLOCK = """
# TOLF test account access control v1
if [ "${1:-}" = admin-test-access ]; then
    case "${2:-}" in
        status) [ "$#" -eq 2 ] || exit 1; exec /usr/local/sbin/tolf-admin-test-access status ;;
        suspend|resume) [ "$#" -eq 3 ] || exit 1; exec /usr/local/sbin/tolf-admin-test-access "$2" "$3" ;;
        *) exit 1 ;;
    esac
fi
"""
SSH_BLOCK = """
# TOLF test account access control v1
if [ "${SSH_ORIGINAL_COMMAND:-}" = 'admin-test-access status' ]; then
    exec sudo -n /usr/local/sbin/tolf-provision-root admin-test-access status
fi
if [[ "${SSH_ORIGINAL_COMMAND:-}" =~ ^admin-test-access[[:space:]]+(suspend|resume)[[:space:]]+([0-9a-f]{32})$ ]]; then
    exec sudo -n /usr/local/sbin/tolf-provision-root admin-test-access "${BASH_REMATCH[1]}" "${BASH_REMATCH[2]}"
fi
"""
PROVISION_GUARD = """
# TOLF Test26 provisioning guard v1
/usr/local/sbin/tolf-admin-test-access guard "$NEW_USER" || exit 1
case "$ACTION" in
    create-username|delete-username) /usr/local/sbin/tolf-admin-test-access guard "$ACCOUNT_ID" || exit 1 ;;
esac
"""
SYNC_GUARD = """
# TOLF Test26 sync guard v1
case "${1:-}:${2:-}" in
    push:user_0888048cac6e44d28aed9857aa31e9ed|delete:user_0888048cac6e44d28aed9857aa31e9ed)
        exec 8>/var/lock/tolf-admin-test-sync.lock
        flock -x 8
        /usr/local/sbin/tolf-admin-test-access guard "$2" || exit 1
        ;;
esac
"""


def insert_guard(source, anchor, block):
    marker = next(line for line in block.splitlines() if line.startswith('# TOLF'))
    if marker in source:
        if block.strip() not in source:
            raise RuntimeError('Existing access guard differs')
        return source
    if source.count(anchor) != 1:
        raise RuntimeError('Unsupported provisioning or synchronization script')
    return source.replace(anchor, block + '\n' + anchor, 1)


def patch(source, block):
    if MARKER in source:
        if block.strip() not in source:
            raise RuntimeError('Existing admin integration differs')
        return source
    anchor = 'set -euo pipefail\n'
    if source.count(anchor) != 1 or '/usr/local/sbin/tolf-' not in source:
        raise RuntimeError('Unsupported provisioning script')
    return source.replace(anchor, anchor + block + '\n', 1)


def atomic(path, data, info=None):
    fd, name = tempfile.mkstemp(prefix='.'+path.name+'-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(name, (info.st_mode & 0o777) if info else 0o755)
        os.chown(name, info.st_uid if info else 0, info.st_gid if info else 0)
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def main():
    if os.geteuid() != 0 or socket.gethostname() != 'EDISLV':
        raise SystemExit('Run as root on Riga EDISLV')
    with open('/var/lock/tolf-provision.lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        reader = base64.b64decode(PAYLOAD)
        if hashlib.sha256(reader).hexdigest() != HASH:
            raise RuntimeError('Payload checksum mismatch')
        compile(reader, str(READER), 'exec')
        planned = {READER: reader}
        for name, block in [('tolf-provision-root', ROOT_BLOCK), ('tolf-provision-ssh', SSH_BLOCK)]:
            path = BASE/name
            text = patch(path.read_text(), block)
            if name == 'tolf-provision-root':
                text = insert_guard(text, 'find_user() {', PROVISION_GUARD)
            planned[path] = text.encode()
            subprocess.run(['/bin/bash', '-n'], input=planned[path], check=True)
        sync = BASE/'ike-users-sync.sh'
        planned[sync] = insert_guard(sync.read_text(), "DIR='/etc/swanctl/conf.d'", SYNC_GUARD).encode()
        subprocess.run(['/bin/sh', '-n'], input=planned[sync], check=True)
        backup = Path('/root/tolf-admin-test-access-backup-'+time.strftime('%Y%m%d-%H%M%S')+'-'+str(os.getpid()))
        backup.mkdir(mode=0o700)
        original = {}
        for path in planned:
            original[path] = (path.read_bytes(), path.stat()) if path.exists() else None
            if path.exists():
                shutil.copy2(path, backup/path.name)
        print('Backup:', backup, flush=True)
        try:
            for path, data in planned.items():
                atomic(path, data, original[path][1] if original[path] else None)
            reports = []
            for node in ('riga', 'moscow'):
                run = subprocess.run([str(BASE/'tolf-admin-test-control'), 'list', node], capture_output=True,
                                     text=True, timeout=35)
                if run.returncode:
                    raise RuntimeError(node + ' VICI read probe failed: ' + run.stdout[-500:])
                report = json.loads(run.stdout)
                if report.get('status') != 'ok' or report.get('node') != node:
                    raise RuntimeError(node + ' VICI validation failed')
                reports.append(report)
        except Exception:
            for path, old in original.items():
                if old is None:
                    path.unlink(missing_ok=True)
                else:
                    atomic(path, old[0], old[1])
            print('Previous files restored.', flush=True)
            raise
        print('OK: reversible access control installed; restricted to Test #26.')
        print('Installation did not suspend access or change VPN credentials.')
        for report in reports:
            print(report['node'] + ' VICI: OK; Test sessions: ' + str(len(report['sessions'])))


if __name__ == '__main__':
    main()
