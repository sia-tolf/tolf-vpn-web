#!/usr/bin/python3
"""Install structured session control restricted to Test account 26."""
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

PAYLOAD = 'IyEvdXNyL2Jpbi9weXRob24zCiIiIlZJQ0kgc2Vzc2lvbiBjb250cm9sLiBEZWxpYmVyYXRlbHkgcmVzdHJpY3RlZCB0byB0ZXN0IGFjY291bnQgMjYuCgpQcm90b2NvbDogc3Ryb25nc3dhbi9zdHJvbmdzd2FuIHNyYy9saWJjaGFyb24vcGx1Z2lucy92aWNpL1JFQURNRS5tZC4KTmV2ZXIgdXNlcyBzd2FuY3RsJ3MgaHVtYW4tcmVhZGFibGUgb3V0cHV0IGZvciBhdXRob3JpemF0aW9uLgoiIiIKaW1wb3J0IGNvbnRleHRsaWIKaW1wb3J0IGpzb24KaW1wb3J0IG9zCmltcG9ydCByZQppbXBvcnQgc2VsZWN0CmltcG9ydCBzb2NrZXQKaW1wb3J0IHN0cnVjdAppbXBvcnQgc3VicHJvY2VzcwppbXBvcnQgc3lzCmltcG9ydCB0aW1lCgpURVNUX1VTRVIgPSAndXNlcl8wODg4MDQ4Y2FjNmU0NGQyOGFlZDk4NTdhYTMxZTllZCcKU09DS0VUID0gJy92YXIvcnVuL2NoYXJvbi52aWNpJwpTU0ggPSBbJy91c3IvYmluL3NzaCcsICctVCcsICctaScsICcvcm9vdC8uc3NoL2lkX2VkMjU1MTlfaWtlX3VzZXJzX3N5bmMnLAogICAgICAgJy1vJywgJ0lkZW50aXRpZXNPbmx5PXllcycsICctbycsICdCYXRjaE1vZGU9eWVzJywKICAgICAgICctbycsICdTdHJpY3RIb3N0S2V5Q2hlY2tpbmc9eWVzJywgJy1vJywgJ0Nvbm5lY3RUaW1lb3V0PTEwJywKICAgICAgICdyb290QDEwLjMxLjAuMScsICcvdXNyL2Jpbi9zb2NhdCBTVERJTyBVTklYLUNPTk5FQ1Q6L3Zhci9ydW4vY2hhcm9uLnZpY2knXQoKCmNsYXNzIENvbnRyb2xFcnJvcihFeGNlcHRpb24pOgogICAgcGFzcwoKCmRlZiBkZWNvZGUoZGF0YSk6CiAgICAiIiJEZWNvZGUgbGVuZ3RoLWRlbGltaXRlZCBWSUNJLCByZWplY3RpbmcgZHVwbGljYXRlIG9yIG1hbGZvcm1lZCBmaWVsZHMuIiIiCiAgICBwb3MgPSAwCiAgICByb290ID0ge30KICAgIHN0YWNrID0gW3Jvb3RdCiAgICBjdXJyZW50X2xpc3QgPSBOb25lCgogICAgZGVmIHRha2Uobik6CiAgICAgICAgbm9ubG9jYWwgcG9zCiAgICAgICAgaWYgcG9zICsgbiA+IGxlbihkYXRhKToKICAgICAgICAgICAgcmFpc2UgQ29udHJvbEVycm9yKCd0cnVuY2F0ZWRfbWVzc2FnZScpCiAgICAgICAgdmFsdWUgPSBkYXRhW3Bvczpwb3Mrbl0KICAgICAgICBwb3MgKz0gbgogICAgICAgIHJldHVybiB2YWx1ZQoKICAgIGRlZiBuYW1lKCk6CiAgICAgICAgcmV0dXJuIHRha2UodGFrZSgxKVswXSkuZGVjb2RlKCdhc2NpaScpCgogICAgZGVmIHZhbHVlKCk6CiAgICAgICAgcmV0dXJuIHRha2Uoc3RydWN0LnVucGFjaygnIUgnLCB0YWtlKDIpKVswXSkKCiAgICB3aGlsZSBwb3MgPCBsZW4oZGF0YSk6CiAgICAgICAga2luZCA9IHRha2UoMSlbMF0KICAgICAgICBpZiBjdXJyZW50X2xpc3QgaXMgbm90IE5vbmU6CiAgICAgICAgICAgIGlmIGtpbmQgPT0gNToKICAgICAgICAgICAgICAgIGN1cnJlbnRfbGlzdC5hcHBlbmQodmFsdWUoKSkKICAgICAgICAgICAgZWxpZiBraW5kID09IDY6CiAgICAgICAgICAgICAgICBjdXJyZW50X2xpc3QgPSBOb25lCiAgICAgICAgICAgIGVsc2U6CiAgICAgICAgICAgICAgICByYWlzZSBDb250cm9sRXJyb3IoJ2ludmFsaWRfbGlzdCcpCiAgICAgICAgICAgIGNvbnRpbnVlCiAgICAgICAgaWYga2luZCA9PSAyOgogICAgICAgICAgICBpZiBsZW4oc3RhY2spID09IDE6CiAgICAgICAgICAgICAgICByYWlzZSBDb250cm9sRXJyb3IoJ3VuZXhwZWN0ZWRfc2VjdGlvbl9lbmQnKQogICAgICAgICAgICBzdGFjay5wb3AoKQogICAgICAgIGVsaWYga2luZCBpbiAoMSwgMywgNCk6CiAgICAgICAgICAgIGtleSA9IG5hbWUoKQogICAgICAgICAgICBpZiBrZXkgaW4gc3RhY2tbLTFdOgogICAgICAgICAgICAgICAgcmFpc2UgQ29udHJvbEVycm9yKCdkdXBsaWNhdGVfZmllbGQnKQogICAgICAgICAgICBpZiBraW5kID09IDM6CiAgICAgICAgICAgICAgICBzdGFja1stMV1ba2V5XSA9IHZhbHVlKCkKICAgICAgICAgICAgZWxpZiBraW5kID09IDE6CiAgICAgICAgICAgICAgICBjaGlsZCA9IHt9CiAgICAgICAgICAgICAgICBzdGFja1stMV1ba2V5XSA9IGNoaWxkCiAgICAgICAgICAgICAgICBzdGFjay5hcHBlbmQoY2hpbGQpCiAgICAgICAgICAgICAgICBpZiBsZW4oc3RhY2spID4gMTY6CiAgICAgICAgICAgICAgICAgICAgcmFpc2UgQ29udHJvbEVycm9yKCdleGNlc3NpdmVfZGVwdGgnKQogICAgICAgICAgICBlbHNlOgogICAgICAgICAgICAgICAgY3VycmVudF9saXN0ID0gW10KICAgICAgICAgICAgICAgIHN0YWNrWy0xXVtrZXldID0gY3VycmVudF9saXN0CiAgICAgICAgZWxzZToKICAgICAgICAgICAgcmFpc2UgQ29udHJvbEVycm9yKCdpbnZhbGlkX2VsZW1lbnQnKQogICAgaWYgbGVuKHN0YWNrKSAhPSAxIG9yIGN1cnJlbnRfbGlzdCBpcyBub3QgTm9uZToKICAgICAgICByYWlzZSBDb250cm9sRXJyb3IoJ3VuY2xvc2VkX21lc3NhZ2UnKQogICAgcmV0dXJuIHJvb3QKCgpkZWYgbmFtZWQobmFtZSk6CiAgICBkYXRhID0gbmFtZS5lbmNvZGUoJ2FzY2lpJykKICAgIHJldHVybiBieXRlcyhbbGVuKGRhdGEpXSkgKyBkYXRhCgoKZGVmIGVuY29kZShmaWVsZHMpOgogICAgcmV0dXJuIGInJy5qb2luKGInXHgwMycgKyBuYW1lZChrKSArIHN0cnVjdC5wYWNrKCchSCcsIGxlbih2KSkgKyB2CiAgICAgICAgICAgICAgICAgICAgZm9yIGssIHYgaW4gZmllbGRzLml0ZW1zKCkpCgoKY2xhc3MgVmljaToKICAgIGRlZiBfX2luaXRfXyhzZWxmLCByZWFkX2ZkLCB3cml0ZV9mZCk6CiAgICAgICAgc2VsZi5yZWFkX2ZkLCBzZWxmLndyaXRlX2ZkID0gcmVhZF9mZCwgd3JpdGVfZmQKICAgICAgICBzZWxmLmRlYWRsaW5lID0gdGltZS5tb25vdG9uaWMoKSArIDI1CiAgICAgICAgc2VsZi50b3RhbCA9IDAKCiAgICBkZWYgd2FpdChzZWxmLCB3cml0aW5nPUZhbHNlKToKICAgICAgICByZW1haW5pbmcgPSBzZWxmLmRlYWRsaW5lIC0gdGltZS5tb25vdG9uaWMoKQogICAgICAgIGlmIHJlbWFpbmluZyA8PSAwOgogICAgICAgICAgICByYWlzZSBDb250cm9sRXJyb3IoJ3RyYW5zcG9ydF90aW1lb3V0JykKICAgICAgICByZWFkeSA9IHNlbGVjdC5zZWxlY3QoW10gaWYgd3JpdGluZyBlbHNlIFtzZWxmLnJlYWRfZmRdLAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICBbc2VsZi53cml0ZV9mZF0gaWYgd3JpdGluZyBlbHNlIFtdLCBbXSwgcmVtYWluaW5nKQogICAgICAgIGlmIG5vdCByZWFkeVsxIGlmIHdyaXRpbmcgZWxzZSAwXToKICAgICAgICAgICAgcmFpc2UgQ29udHJvbEVycm9yKCd0cmFuc3BvcnRfdGltZW91dCcpCgogICAgZGVmIHJlYWQoc2VsZiwgc2l6ZSk6CiAgICAgICAgb3V0cHV0ID0gYnl0ZWFycmF5KCkKICAgICAgICB3aGlsZSBsZW4ob3V0cHV0KSA8IHNpemU6CiAgICAgICAgICAgIHNlbGYud2FpdCgpCiAgICAgICAgICAgIHBhcnQgPSBvcy5yZWFkKHNlbGYucmVhZF9mZCwgc2l6ZSAtIGxlbihvdXRwdXQpKQogICAgICAgICAgICBpZiBub3QgcGFydDoKICAgICAgICAgICAgICAgIHJhaXNlIENvbnRyb2xFcnJvcigndHJhbnNwb3J0X2Nsb3NlZCcpCiAgICAgICAgICAgIG91dHB1dC5leHRlbmQocGFydCkKICAgICAgICByZXR1cm4gYnl0ZXMob3V0cHV0KQoKICAgIGRlZiBzZW5kKHNlbGYsIHBhY2tldCk6CiAgICAgICAgZGF0YSA9IHN0cnVjdC5wYWNrKCchSScsIGxlbihwYWNrZXQpKSArIHBhY2tldAogICAgICAgIHdoaWxlIGRhdGE6CiAgICAgICAgICAgIHNlbGYud2FpdChUcnVlKQogICAgICAgICAgICB3cml0dGVuID0gb3Mud3JpdGUoc2VsZi53cml0ZV9mZCwgZGF0YSkKICAgICAgICAgICAgaWYgbm90IHdyaXR0ZW46CiAgICAgICAgICAgICAgICByYWlzZSBDb250cm9sRXJyb3IoJ3RyYW5zcG9ydF9jbG9zZWQnKQogICAgICAgICAgICBkYXRhID0gZGF0YVt3cml0dGVuOl0KCiAgICBkZWYgcmVjZWl2ZShzZWxmKToKICAgICAgICBzaXplID0gc3RydWN0LnVucGFjaygnIUknLCBzZWxmLnJlYWQoNCkpWzBdCiAgICAgICAgc2VsZi50b3RhbCArPSBzaXplCiAgICAgICAgaWYgbm90IDEgPD0gc2l6ZSA8PSA1MTIgKiAxMDI0IG9yIHNlbGYudG90YWwgPiA4ICogMTAyNCAqIDEwMjQ6CiAgICAgICAgICAgIHJhaXNlIENvbnRyb2xFcnJvcigncmVzcG9uc2VfdG9vX2xhcmdlJykKICAgICAgICByZXR1cm4gc2VsZi5yZWFkKHNpemUpCgogICAgZGVmIHJlcXVlc3Qoc2VsZiwgY29tbWFuZCwgZmllbGRzPU5vbmUpOgogICAgICAgIHNlbGYuc2VuZChiJ1x4MDAnICsgbmFtZWQoY29tbWFuZCkgKyBlbmNvZGUoZmllbGRzIG9yIHt9KSkKICAgICAgICBwYWNrZXQgPSBzZWxmLnJlY2VpdmUoKQogICAgICAgIGlmIHBhY2tldFswXSAhPSAxOgogICAgICAgICAgICByYWlzZSBDb250cm9sRXJyb3IoJ3VuZXhwZWN0ZWRfcmVzcG9uc2UnKQogICAgICAgIHJldHVybiBkZWNvZGUocGFja2V0WzE6XSkKCiAgICBkZWYgaW52ZW50b3J5KHNlbGYpOgogICAgICAgIHNlbGYuc2VuZChiJ1x4MDMnICsgbmFtZWQoJ2xpc3Qtc2EnKSkKICAgICAgICBpZiBzZWxmLnJlY2VpdmUoKSAhPSBiJ1x4MDUnOgogICAgICAgICAgICByYWlzZSBDb250cm9sRXJyb3IoJ2V2ZW50X3JlZ2lzdHJhdGlvbl9mYWlsZWQnKQogICAgICAgIHNlbGYuc2VuZChiJ1x4MDAnICsgbmFtZWQoJ2xpc3Qtc2FzJykpCiAgICAgICAgcm93cyA9IFtdCiAgICAgICAgd2hpbGUgVHJ1ZToKICAgICAgICAgICAgcGFja2V0ID0gc2VsZi5yZWNlaXZlKCkKICAgICAgICAgICAgaWYgcGFja2V0WzBdID09IDE6CiAgICAgICAgICAgICAgICBpZiBkZWNvZGUocGFja2V0WzE6XSkgIT0ge306CiAgICAgICAgICAgICAgICAgICAgcmFpc2UgQ29udHJvbEVycm9yKCdpbnZhbGlkX2ludmVudG9yeV9yZXNwb25zZScpCiAgICAgICAgICAgICAgICBicmVhawogICAgICAgICAgICBwcmVmaXggPSBiJ1x4MDcnICsgbmFtZWQoJ2xpc3Qtc2EnKQogICAgICAgICAgICBpZiBub3QgcGFja2V0LnN0YXJ0c3dpdGgocHJlZml4KToKICAgICAgICAgICAgICAgIHJhaXNlIENvbnRyb2xFcnJvcigndW5leHBlY3RlZF9pbnZlbnRvcnlfZXZlbnQnKQogICAgICAgICAgICBldmVudCA9IGRlY29kZShwYWNrZXRbbGVuKHByZWZpeCk6XSkKICAgICAgICAgICAgaWYgbGVuKGV2ZW50KSAhPSAxIG9yIG5vdCBpc2luc3RhbmNlKG5leHQoaXRlcihldmVudC52YWx1ZXMoKSkpLCBkaWN0KToKICAgICAgICAgICAgICAgIHJhaXNlIENvbnRyb2xFcnJvcignaW52YWxpZF9pbnZlbnRvcnlfZXZlbnQnKQogICAgICAgICAgICByb3dzLmFwcGVuZChuZXh0KGl0ZXIoZXZlbnQudmFsdWVzKCkpKSkKICAgICAgICAgICAgaWYgbGVuKHJvd3MpID4gMTAwMDA6CiAgICAgICAgICAgICAgICByYWlzZSBDb250cm9sRXJyb3IoJ3Rvb19tYW55X3Nlc3Npb25zJykKICAgICAgICBzZWxmLnNlbmQoYidceDA0JyArIG5hbWVkKCdsaXN0LXNhJykpCiAgICAgICAgaWYgc2VsZi5yZWNlaXZlKCkgIT0gYidceDA1JzoKICAgICAgICAgICAgcmFpc2UgQ29udHJvbEVycm9yKCdldmVudF91bnJlZ2lzdHJhdGlvbl9mYWlsZWQnKQogICAgICAgIHJldHVybiByb3dzCgoKQGNvbnRleHRsaWIuY29udGV4dG1hbmFnZXIKZGVmIGNvbm5lY3Qobm9kZSk6CiAgICBpZiBub2RlID09ICdyaWdhJzoKICAgICAgICB3aXRoIHNvY2tldC5zb2NrZXQoc29ja2V0LkFGX1VOSVgsIHNvY2tldC5TT0NLX1NUUkVBTSkgYXMgc29jazoKICAgICAgICAgICAgc29jay5zZXR0aW1lb3V0KDEwKQogICAgICAgICAgICBzb2NrLmNvbm5lY3QoU09DS0VUKQogICAgICAgICAgICBzb2NrLnNldGJsb2NraW5nKFRydWUpCiAgICAgICAgICAgIHlpZWxkIFZpY2koc29jay5maWxlbm8oKSwgc29jay5maWxlbm8oKSkKICAgIGVsaWYgbm9kZSA9PSAnbW9zY293JzoKICAgICAgICBwcm9jZXNzID0gc3VicHJvY2Vzcy5Qb3BlbihTU0gsIHN0ZGluPXN1YnByb2Nlc3MuUElQRSwgc3Rkb3V0PXN1YnByb2Nlc3MuUElQRSwKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBzdGRlcnI9c3VicHJvY2Vzcy5ERVZOVUxMLCBidWZzaXplPTApCiAgICAgICAgdHJ5OgogICAgICAgICAgICB5aWVsZCBWaWNpKHByb2Nlc3Muc3Rkb3V0LmZpbGVubygpLCBwcm9jZXNzLnN0ZGluLmZpbGVubygpKQogICAgICAgIGZpbmFsbHk6CiAgICAgICAgICAgIHByb2Nlc3Muc3RkaW4uY2xvc2UoKQogICAgICAgICAgICBwcm9jZXNzLnN0ZG91dC5jbG9zZSgpCiAgICAgICAgICAgIGlmIHByb2Nlc3MucG9sbCgpIGlzIE5vbmU6CiAgICAgICAgICAgICAgICBwcm9jZXNzLnRlcm1pbmF0ZSgpCiAgICAgICAgICAgIHRyeToKICAgICAgICAgICAgICAgIHByb2Nlc3Mud2FpdCh0aW1lb3V0PTIpCiAgICAgICAgICAgIGV4Y2VwdCBzdWJwcm9jZXNzLlRpbWVvdXRFeHBpcmVkOgogICAgICAgICAgICAgICAgcHJvY2Vzcy5raWxsKCkKICAgICAgICAgICAgICAgIHByb2Nlc3Mud2FpdCh0aW1lb3V0PTIpCiAgICBlbHNlOgogICAgICAgIHJhaXNlIENvbnRyb2xFcnJvcignaW52YWxpZF9ub2RlJykKCgpkZWYgc2VsZWN0b3Iocm93KToKICAgICMgRUFQIGF1dGhlbnRpY2F0aW9uIGlkZW50aXR5IGlzIHJlcXVpcmVkOyBuZXZlciBmYWxsIGJhY2sgdG8gYW4gSUtFIElELgogICAgaWYgcm93LmdldCgnc3RhdGUnKSAhPSBiJ0VTVEFCTElTSEVEJyBvciByb3cuZ2V0KCdyZW1vdGUtZWFwLWlkJykgIT0gVEVTVF9VU0VSLmVuY29kZSgpOgogICAgICAgIHJldHVybiBOb25lCiAgICB0cnk6CiAgICAgICAgcmVzdWx0ID0ge2tleTogcm93W2tleV0uZGVjb2RlKCdhc2NpaScpIGZvciBrZXkgaW4KICAgICAgICAgICAgICAgICAgKCd1bmlxdWVpZCcsICdpbml0aWF0b3Itc3BpJywgJ3Jlc3BvbmRlci1zcGknKX0KICAgIGV4Y2VwdCAoS2V5RXJyb3IsIEF0dHJpYnV0ZUVycm9yLCBVbmljb2RlRXJyb3IpOgogICAgICAgIHJhaXNlIENvbnRyb2xFcnJvcignaW52YWxpZF90ZXN0X3Nlc3Npb24nKQogICAgdmFsaWRhdGVfc2VsZWN0b3IocmVzdWx0KQogICAgcmV0dXJuIHJlc3VsdAoKCmRlZiB2YWxpZGF0ZV9zZWxlY3RvcihpdGVtKToKICAgIGlmIG5vdCByZS5mdWxsbWF0Y2gocidbMS05XVswLTldezAsOX0nLCBpdGVtWyd1bmlxdWVpZCddKSBvciBpbnQoaXRlbVsndW5pcXVlaWQnXSkgPiA0Mjk0OTY3Mjk1OgogICAgICAgIHJhaXNlIENvbnRyb2xFcnJvcignaW52YWxpZF9zZXNzaW9uX2lkJykKICAgIGZvciBmaWVsZCBpbiAoJ2luaXRpYXRvci1zcGknLCAncmVzcG9uZGVyLXNwaScpOgogICAgICAgIGlmIG5vdCByZS5mdWxsbWF0Y2gocidbMC05YS1mXXsxNn0nLCBpdGVtW2ZpZWxkXSk6CiAgICAgICAgICAgIHJhaXNlIENvbnRyb2xFcnJvcignaW52YWxpZF9zZXNzaW9uX3NwaScpCgoKZGVmIG9wZXJhdGUoY2xpZW50LCBleHBlY3RlZD1Ob25lKToKICAgIHJvd3MgPSBjbGllbnQuaW52ZW50b3J5KCkKICAgIHRlc3RzID0gW2l0ZW0gZm9yIHJvdyBpbiByb3dzIGlmIChpdGVtIDo9IHNlbGVjdG9yKHJvdykpIGlzIG5vdCBOb25lXQogICAgaWYgZXhwZWN0ZWQgaXMgTm9uZToKICAgICAgICByZXR1cm4geydzdGF0dXMnOiAnb2snLCAnYWNjb3VudE51bWJlcic6IDI2LCAnc2Vzc2lvbnMnOiB0ZXN0c30KICAgIHZhbGlkYXRlX3NlbGVjdG9yKGV4cGVjdGVkKQogICAgbWF0Y2hlcyA9IFtyb3cgZm9yIHJvdyBpbiByb3dzIGlmIHJvdy5nZXQoJ3VuaXF1ZWlkJykgPT0gZXhwZWN0ZWRbJ3VuaXF1ZWlkJ10uZW5jb2RlKCldCiAgICBpZiBsZW4obWF0Y2hlcykgIT0gMSBvciBzZWxlY3RvcihtYXRjaGVzWzBdKSAhPSBleHBlY3RlZDoKICAgICAgICByYWlzZSBDb250cm9sRXJyb3IoJ3N0YWxlX29yX2ZvcmJpZGRlbl9zZXNzaW9uJykKICAgICMgTGlzdCBhbmQgdGVybWluYXRlIG9uIHRoZSBTQU1FIHNvY2tldDogZGFlbW9uIHJlc3RhcnQgY2xvc2VzIGl0OyBubyByZWNvbm5lY3QvcmV0cnkuCiAgICAjIFVuaXF1ZSBJS0UgSURzIGRvIG5vdCBnZXQgcmV1c2VkIGR1cmluZyB0aGlzIGRhZW1vbiBsaWZldGltZSAoZXhjZXB0IHVpbnQzMiB3cmFwKS4KICAgIHJlcGx5ID0gY2xpZW50LnJlcXVlc3QoJ3Rlcm1pbmF0ZScsIHsnaWtlLWlkJzogZXhwZWN0ZWRbJ3VuaXF1ZWlkJ10uZW5jb2RlKCksCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICd0aW1lb3V0JzogYic1MDAwJywgJ2ZvcmNlJzogYidubyd9KQogICAgaWYgcmVwbHkuZ2V0KCdzdWNjZXNzJykgIT0gYid5ZXMnIG9yIHJlcGx5LmdldCgnbWF0Y2hlcycpICE9IGInMScgb3IgcmVwbHkuZ2V0KCd0ZXJtaW5hdGVkJykgIT0gYicxJzoKICAgICAgICByZXR1cm4geydzdGF0dXMnOiAndW5rbm93bicsICdlcnJvcic6ICdkaXNjb25uZWN0X25vdF9jb25maXJtZWQnLCAnYWNjb3VudE51bWJlcic6IDI2fQogICAgcmVtYWluaW5nID0gY2xpZW50LmludmVudG9yeSgpCiAgICBpZiBhbnkocm93LmdldCgndW5pcXVlaWQnKSA9PSBleHBlY3RlZFsndW5pcXVlaWQnXS5lbmNvZGUoKSBmb3Igcm93IGluIHJlbWFpbmluZyk6CiAgICAgICAgcmV0dXJuIHsnc3RhdHVzJzogJ3Vua25vd24nLCAnZXJyb3InOiAnZGlzY29ubmVjdF9ub3RfY29uZmlybWVkJywgJ2FjY291bnROdW1iZXInOiAyNn0KICAgIHJldHVybiB7J3N0YXR1cyc6ICdvaycsICdhY2NvdW50TnVtYmVyJzogMjYsICdkaXNjb25uZWN0ZWQnOiBleHBlY3RlZFsndW5pcXVlaWQnXSwKICAgICAgICAgICAgJ3JlY29ubmVjdGVkJzogYW55KHNlbGVjdG9yKHJvdykgaXMgbm90IE5vbmUgZm9yIHJvdyBpbiByZW1haW5pbmcpfQoKCmRlZiBtYWluKCk6CiAgICBpZiBvcy5nZXRldWlkKCkgIT0gMDoKICAgICAgICByYWlzZSBDb250cm9sRXJyb3IoJ3Jvb3RfcmVxdWlyZWQnKQogICAgYXJncyA9IHN5cy5hcmd2WzE6XQogICAgaWYgbGVuKGFyZ3MpID09IDIgYW5kIGFyZ3NbMF0gPT0gJ2xpc3QnOgogICAgICAgIGV4cGVjdGVkID0gTm9uZQogICAgZWxpZiBsZW4oYXJncykgPT0gNSBhbmQgYXJnc1swXSA9PSAnZGlzY29ubmVjdCc6CiAgICAgICAgZXhwZWN0ZWQgPSBkaWN0KHppcCgoJ3VuaXF1ZWlkJywgJ2luaXRpYXRvci1zcGknLCAncmVzcG9uZGVyLXNwaScpLCBhcmdzWzI6XSkpCiAgICAgICAgdmFsaWRhdGVfc2VsZWN0b3IoZXhwZWN0ZWQpCiAgICBlbHNlOgogICAgICAgIHJhaXNlIENvbnRyb2xFcnJvcignaW52YWxpZF9hcmd1bWVudHMnKQogICAgd2l0aCBjb25uZWN0KGFyZ3NbMV0pIGFzIGNsaWVudDoKICAgICAgICByZXN1bHQgPSBvcGVyYXRlKGNsaWVudCwgZXhwZWN0ZWQpCiAgICByZXN1bHRbJ25vZGUnXSA9IGFyZ3NbMV0KICAgIHByaW50KGpzb24uZHVtcHMocmVzdWx0LCBzZXBhcmF0b3JzPSgnLCcsICc6JykpKQogICAgcmV0dXJuIDAgaWYgcmVzdWx0WydzdGF0dXMnXSA9PSAnb2snIGVsc2UgMQoKCmlmIF9fbmFtZV9fID09ICdfX21haW5fXyc6CiAgICB0cnk6CiAgICAgICAgc3lzLmV4aXQobWFpbigpKQogICAgZXhjZXB0IChDb250cm9sRXJyb3IsIE9TRXJyb3IsIFVuaWNvZGVFcnJvcikgYXMgZXJyb3I6CiAgICAgICAgIyBUcmFuc3BvcnQgZXJyb3JzIGRvbid0IGVzdGFibGlzaCB3aGV0aGVyIGEgc2VudCB0ZXJtaW5hdGUgY29tcGxldGVkLiBEbyBub3QgcmV0cnkuCiAgICAgICAgcHJpbnQoanNvbi5kdW1wcyh7J3N0YXR1cyc6ICdlcnJvcicsICdlcnJvcic6IHN0cihlcnJvcikgaWYgaXNpbnN0YW5jZShlcnJvciwgQ29udHJvbEVycm9yKQogICAgICAgICAgICAgICAgICAgICAgICAgIGVsc2UgJ3RyYW5zcG9ydF9lcnJvcid9KSkKICAgICAgICBzeXMuZXhpdCgxKQo='
HASH = '6aed9dd3395e171f9bee7cf50ee2f37d0aca0db84b6c059689d7e9e564388894'
BASE = Path('/usr/local/sbin')
READER = BASE / 'tolf-admin-test-control'
MARKER = '# TOLF test account session control v1'
ROOT_BLOCK = '''
# TOLF test account session control v1
if [ "${1:-}" = admin-test-sessions ]; then
    [ "$#" -eq 2 ] || exit 1
    exec /usr/local/sbin/tolf-admin-test-control list "$2"
fi
if [ "${1:-}" = admin-test-disconnect ]; then
    [ "$#" -eq 5 ] || exit 1
    exec /usr/local/sbin/tolf-admin-test-control disconnect "$2" "$3" "$4" "$5"
fi
'''
SSH_BLOCK = '''
# TOLF test account session control v1
if [[ "${SSH_ORIGINAL_COMMAND:-}" =~ ^admin-test-sessions[[:space:]]+(riga|moscow)$ ]]; then
    exec sudo -n /usr/local/sbin/tolf-provision-root admin-test-sessions "${BASH_REMATCH[1]}"
fi
if [[ "${SSH_ORIGINAL_COMMAND:-}" =~ ^admin-test-disconnect[[:space:]]+(riga|moscow)[[:space:]]+([1-9][0-9]{0,9})[[:space:]]+([0-9a-f]{16})[[:space:]]+([0-9a-f]{16})$ ]]; then
    exec sudo -n /usr/local/sbin/tolf-provision-root admin-test-disconnect "${BASH_REMATCH[1]}" "${BASH_REMATCH[2]}" "${BASH_REMATCH[3]}" "${BASH_REMATCH[4]}"
fi
'''


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
            planned[path] = patch(path.read_text(), block).encode()
            subprocess.run(['/bin/bash', '-n'], input=planned[path], check=True)
        backup = Path('/root/tolf-admin-test-control-backup-'+time.strftime('%Y%m%d-%H%M%S')+'-'+str(os.getpid()))
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
                run = subprocess.run([str(READER), 'list', node], capture_output=True,
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
        print('OK: structured session control installed; restricted to Test account #26.')
        print('Installation only read session data. No VPN sessions disconnected.')
        for report in reports:
            print(report['node'] + ' VICI: OK; Test sessions: ' + str(len(report['sessions'])))


if __name__ == '__main__':
    main()
